"""Construit la base JSON d'une législature à partir des fichiers bruts de l'open data.

Usage : python3 pipeline/construire.py 17 [--rafraichir-cr AAAA-MM-JJ]

Les comptes rendus de séance sont gardés en cache dans donnees/brut/<législature>/comptes-rendus/.
Avec --rafraichir-cr, ceux des séances tenues à partir de cette date sont re-téléchargés
(l'Assemblée peut corriger un compte rendu quelques jours après sa publication).

Produit dans donnees/base/<législature>/ :
- groupes.json  : les groupes politiques, dans l'ordre de l'hémicycle ;
- niches.json   : les journées réservées détectées, avec leur programme et le statut de chaque texte ;
- textes.json   : les textes votés (niches et votes solennels), avec auteur, statut et suite donnée ;
- scrutins.json : les votes utilisés, avec les positions des groupes recalculées ;
- rapport.md    : les chiffres clés et tout ce qui doit être vérifié à la main.

Les niches vérifiées se trouvent dans donnees/validation/niches-<législature>.json : « valide » (vérifiée par un humain),
« verifie_ia » (vérifiée par IA dans les comptes rendus), « a_valider », ou « rejete ». Une entrée peut porter des
« corrections » du programme (statut rectifié, ou ligne à exclure).
"""
import collections
import datetime
import html
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

from commun import (BASE, BRUT, ORGANE_ASSEMBLEE, ORGANE_SENAT, SITE_AN, VALIDATION, actes, ecrire_json,
                    en_liste, lire_json, lire_zip, mots, normaliser, proximite, telecharger)

# Ordre de l'hémicycle, de la gauche vers la droite (l'open data ne le fournit pas)
ORDRE_HEMICYCLE = {
    "15": ["FI", "GDR", "SOC", "EDS", "LT", "LAREM", "DEM", "AGIR-E", "UDI-I", "LR", "NI"],
    "16": ["LFI-NUPES", "GDR-NUPES", "ECOLO", "SOC", "LIOT", "RE", "DEM", "HOR", "LR", "RN", "NI"],
    "17": ["LFI-NFP", "GDR", "ECOS", "SOC", "LIOT", "DEM", "EPR", "HOR", "DR", "UDR", "RN", "NI"],
}
# Groupes qui ont changé de sigle en cours de législature : on garde un seul sigle, le plus récent
MEME_GROUPE = {
    "UDDPLR": "UDR",                                   # 17e
    "SOC-A": "SOC",                                    # 16e
    "MODEM": "DEM", "NG": "SOC",                       # 15e : renommages
    "LC": "UDI-I", "UDI-AGIR": "UDI-I", "UDI-A-I": "UDI-I", "UDI_I": "UDI-I",   # 15e : Les Constructifs, devenus UDI et Indépendants
}

NS = "{http://schemas.assemblee-nationale.fr/referentiel}"

# Date à partir de laquelle les comptes rendus en cache sont re-téléchargés (option --rafraichir-cr)
RAFRAICHIR_DEPUIS = None
_rafraichis = set()
CR_ABSENTS = []   # comptes rendus pas encore publiés


# ---------------------------------------------------------------- chargement

def charger_groupes_et_mandats(legislature):
    organes, tous_groupes, mandats = {}, {}, collections.defaultdict(list)
    for doc in lire_zip(BRUT / legislature / "acteurs.zip", "organe"):
        o = doc["organe"]
        if o.get("codeType") == "GP":
            abrev = MEME_GROUPE.get(o["libelleAbrev"], o["libelleAbrev"])
            tous_groupes[o["uid"]] = abrev   # toutes législatures : un texte peut venir d'une législature précédente
            if o.get("legislature") == legislature:
                organes[o["uid"]] = {"abrev": abrev, "nom": o["libelle"], "couleur": o.get("couleurAssociee"),
                                     "position": o.get("positionPolitique"),   # vide pour la 17e
                                     "debut": o["viMoDe"].get("dateDebut") or "", "fin": o["viMoDe"].get("dateFin")}
    for doc in lire_zip(BRUT / legislature / "acteurs.zip", "acteur"):
        a = doc["acteur"]
        uid = a["uid"]["#text"] if isinstance(a["uid"], dict) else a["uid"]
        for m in en_liste((a.get("mandats") or {}).get("mandat")):
            ref = (m.get("organes") or {}).get("organeRef")
            if m.get("typeOrgane") == "GP" and ref in tous_groupes:
                mandats[uid].append((m.get("dateDebut") or "", m.get("dateFin") or "9999", tous_groupes[ref]))
            elif m.get("typeOrgane") == "GOUVERNEMENT":
                mandats[uid].append((m.get("dateDebut") or "", m.get("dateFin") or "9999", "GOUVERNEMENT"))
    return organes, mandats


def groupe_a_la_date(mandats, acteur, jour):
    """Groupe d'un député à une date ; « GOUVERNEMENT » s'il était alors ministre."""
    trouves = [abrev for debut, fin, abrev in mandats.get(acteur, []) if debut <= jour <= fin]
    return "GOUVERNEMENT" if "GOUVERNEMENT" in trouves else (trouves[0] if trouves else None)


def charger_scrutins(legislature, organes):
    scrutins = {}
    for doc in lire_zip(BRUT / legislature / "scrutins.zip", "json"):
        s = doc["scrutin"]
        groupes = []
        for g in en_liste(s["ventilationVotes"]["organe"]["groupes"]["groupe"]):
            v = g["vote"]["decompteVoix"]
            groupes.append({"g": organes.get(g["organeRef"], {}).get("abrev", g["organeRef"]), "m": int(g["nombreMembresGroupe"]),
                            "pour": int(v["pour"]), "contre": int(v["contre"]), "abst": int(v["abstentions"])})
        d = s["syntheseVote"]["decompte"]
        scrutins[s["uid"]] = {"numero": int(s["numero"]), "date": s["dateScrutin"], "type": s["typeVote"]["codeTypeVote"],
                              "titre": s["titre"], "sort": s["sort"]["code"], "pour": int(d["pour"]), "contre": int(d["contre"]),
                              "abst": int(d["abstentions"]), "seance": s.get("seanceRef"), "groupes": groupes}
        # L'open data omet parfois la ligne d'un groupe (le MoDem dans une douzaine de votes de mai-juillet 2020) :
        # on ne l'invente pas, on signale les groupes absents et les voix qui ne sont attribuées à aucun groupe
        presents = {g["organeRef"] for g in en_liste(s["ventilationVotes"]["organe"]["groupes"]["groupe"])}
        manquants = sorted({o["abrev"] for uid, o in organes.items() if uid not in presents and o["debut"][:10] <= s["dateScrutin"]
                            and (not o["fin"] or o["fin"][:10] >= s["dateScrutin"])} - {g["g"] for g in groupes})
        ecart = {k: scrutins[s["uid"]][k] - sum(g[k] for g in groupes) for k in ("pour", "contre", "abst")}
        if manquants:
            scrutins[s["uid"]]["groupesManquants"] = manquants
            scrutins[s["uid"]]["voixNonVentilees"] = ecart
        # Le dossier cité par le vote lui-même (renseigné depuis 2024 seulement)
        ref = ((s.get("objet") or {}).get("dossierLegislatif") or {}).get("dossierRef")
        if ref:
            scrutins[s["uid"]]["dossierRef"] = ref
    return scrutins


def charger_dossiers(legislature):
    """Les dossiers de la législature. Un dossier qui se poursuit sous la législature suivante figure aussi dans ses
    fichiers, dans une version plus à jour (promulgation, lectures suivantes, votes corrigés) : c'est celle qu'on garde."""
    dossiers = {}
    for doc in lire_zip(BRUT / legislature / "dossiers.zip", "dossierParlementaire"):
        d = doc["dossierParlementaire"]
        dossiers[d["uid"]] = d
    for autre in sorted(ORGANE_ASSEMBLEE, key=int):
        if int(autre) <= int(legislature) or not (BRUT / autre / "dossiers.zip").exists():
            continue
        for doc in lire_zip(BRUT / autre / "dossiers.zip", "dossierParlementaire"):
            d = doc["dossierParlementaire"]
            if d["uid"] in dossiers and derniere_date(d) >= derniere_date(dossiers[d["uid"]]):
                dossiers[d["uid"]] = d
    return dossiers


def derniere_date(dossier):
    return max((a["dateActe"] for a in actes(dossier) if a.get("dateActe")), default="")


def charger_seances(legislature):
    """Séances plénières confirmées de l'Assemblée, regroupées par jour."""
    jours = collections.defaultdict(list)
    for doc in lire_zip(BRUT / legislature / "agenda.zip", "reunion"):
        r = doc["reunion"]
        if r.get("@xsi:type") == "seance_type" and r.get("organeReuniRef") == ORGANE_ASSEMBLEE[legislature] and r["cycleDeVie"]["etat"] == "Confirmé":
            jours[r["timeStampDebut"][:10]].append(r)
    for liste in jours.values():
        liste.sort(key=lambda r: r["timeStampDebut"])
    return jours


# ---------------------------------------------------------------- dossiers

def auteur(dossier, mandats, jour):
    """Qui a déposé le texte : le gouvernement, des sénateurs, ou un député (avec son groupe au moment du dépôt)."""
    procedure, titre = dossier["procedureParlementaire"]["libelle"], dossier["titreDossier"]["titre"]
    if procedure.lower().startswith(("projet de loi", "projet de ratification")) or titre.startswith("Projet de loi"):
        return {"type": "gouvernement"}
    depots = sorted(a["dateActe"][:10] for a in actes(dossier) if a["codeActe"].endswith("DEPOT") and a.get("dateActe"))
    jour = depots[0] if depots else jour
    init = dossier.get("initiateur") or {}
    for a in en_liste((init.get("acteurs") or {}).get("acteur")):
        g = groupe_a_la_date(mandats, a["acteurRef"], jour)
        if g == "GOUVERNEMENT":
            return {"type": "gouvernement"}
        if g:
            return {"type": "depute", "groupe": g, "acteur": a["acteurRef"]}
    organes_init = [((o.get("organeRef") or {}).get("uid")) for o in en_liste((init.get("organes") or {}).get("organe"))]
    if ORGANE_SENAT in organes_init:
        return {"type": "senat"}
    return {"type": "inconnu"}


def suite_donnee(dossier):
    """Ce que le texte est devenu après l'Assemblée : promulgation, Conseil constitutionnel, dernière étape."""
    tous = actes(dossier)
    prom = next((a for a in tous if a["codeActe"] == "PROM-PUB"), None)
    cc = next((a for a in tous if a["codeActe"] == "CC-CONCLUSION"), None)
    dates = [a for a in tous if a.get("dateActe")]
    dernier = max(dates, key=lambda a: a["dateActe"]) if dates else None
    return {
        "promulgation": prom["dateActe"][:10] if prom else None,
        "numeroLoi": prom.get("codeLoi") if prom else None,
        "conseilConstitutionnel": (cc.get("statutConclusion") or {}).get("libelle") if cc else None,
        "derniereEtape": dernier["codeActe"] if dernier else None,
        "dateDerniereEtape": dernier["dateActe"][:10] if dernier else None,
    }


def premier_depot(dossier):
    """Date du premier dépôt du texte (« 9999 » si inconnue)."""
    return min((a["dateActe"][:10] for a in actes(dossier) if a["codeActe"].endswith("DEPOT") and a.get("dateActe")), default="9999")


def decisions_assemblee(dossier):
    """Décisions de l'Assemblée sur ce texte : date, résultat, votes associés."""
    res = []
    for a in actes(dossier):
        if a["codeActe"].endswith(("DEBATS-DEC", "DEBATS-AN-DEC")) and a.get("organeRef") in ORGANE_ASSEMBLEE.values() and a.get("dateActe"):
            res.append({"date": a["dateActe"][:10], "statut": (a.get("statutConclusion") or {}).get("libelle", ""),
                        "votes": en_liste((a.get("voteRefs") or {}).get("voteRef"))})
    return res


def variantes_titre(titre):
    """En 2017-2022, les titres commencent souvent par un thème (« Société : … ») absent de l'intitulé des votes."""
    return list(dict.fromkeys([titre, re.sub(r"^[^:]{3,40} : ", "", titre)]))


def correspondance(dossier, scrutin):
    """Proximité entre le titre d'un dossier et l'intitulé d'un vote (0 à 1). Une loi organique et la loi ordinaire qui
    l'accompagne portent souvent le même titre : un vote sur l'une ne correspond pas à l'autre."""
    if ("organique" in dossier["procedureParlementaire"]["libelle"].lower()) != ("loi organique" in scrutin["titre"]):
        return 0.0
    return max(proximite(t, titre_vise(scrutin["titre"])) for t in variantes_titre(dossier["titreDossier"]["titre"].replace("\r", " ")))


def debattus_par_jour(dossiers):
    """Pour chaque jour : les dossiers discutés ou votés en séance à l'Assemblée."""
    jours = collections.defaultdict(set)
    for uid, d in dossiers.items():
        for a in actes(d):
            if a.get("organeRef") in ORGANE_ASSEMBLEE.values() and a.get("dateActe") and "DEBATS" in a["codeActe"]:
                jours[a["dateActe"][:10]].add(uid)
    return jours


def votes_des_dossiers(dossiers, scrutins, debattus, a_verifier):
    """Le dossier de chaque vote cité par une décision de l'Assemblée.

    L'open data se trompe parfois de vote (un amendement d'un autre texte, le vote du texte voisin). Un vote cité n'est
    retenu que s'il porte sur ce texte : le dossier indiqué par le vote lui-même quand il y en a un ; sinon un intitulé
    proche du titre du dossier, ou, pour un texte renommé, un vote du jour de la décision qu'aucun autre texte discuté
    ce jour-là ne revendique. Un vote cité par deux dossiers n'est rattaché à aucun (à vérifier)."""
    liens = collections.defaultdict(set)
    for uid, d in dossiers.items():
        for dec in decisions_assemblee(d):
            for v in dec["votes"]:
                s = scrutins.get(v)
                if not s:
                    continue
                if s.get("dossierRef"):
                    ok = s["dossierRef"] == uid
                elif correspondance(d, s) >= 0.5:
                    ok = True
                else:
                    ok = s["date"] == dec["date"] and not any(correspondance(dossiers[o], s) >= 0.75 for o in debattus[s["date"]] if o != uid)
                if ok:
                    liens[v].add(uid)
                else:
                    a_verifier.append(f"Vote n° {s['numero']} du {s['date']} cité par le dossier {uid} (décision du {dec['date']}) "
                                      f"mais portant sur un autre objet, écarté : « {s['titre'][:90]} »")
    resultat = {}
    for v, uids in liens.items():
        if len(uids) == 1:
            resultat[v] = next(iter(uids))
        else:
            a_verifier.append(f"Vote n° {scrutins[v]['numero']} du {scrutins[v]['date']} cité par plusieurs dossiers ({', '.join(sorted(uids))}) : rattaché à aucun")
            resultat[v] = None
    return resultat


EX_AEQUO = []   # rapprochements par le titre abandonnés faute de pouvoir départager deux candidats


def meilleur(candidats, quoi, seuil=0.75, scrutins=None):
    """Le candidat au meilleur score (≥ seuil). Deux candidats à égalité : aucun, plutôt que de choisir au hasard.
    Exception : deux votes du même jour au même intitulé sont le même vote recommencé ; le dernier compte."""
    candidats = sorted((c for c in candidats if c[0] >= seuil), key=lambda c: c[0], reverse=True)
    if not candidats:
        return None
    ex_aequo = [c[1] for c in candidats if c[0] == candidats[0][0]]
    if scrutins and len({frozenset(mots(scrutins[v]["titre"])) for v in ex_aequo}) == 1:
        return max(ex_aequo, key=lambda v: scrutins[v]["numero"])
    if len(ex_aequo) > 1:
        EX_AEQUO.append(f"{quoi} : candidats à égalité ({', '.join(str(c[1]) for c in candidats if c[0] == candidats[0][0])}), aucun retenu")
        return None
    return candidats[0][1]


# ---------------------------------------------------------------- comptes rendus

def compte_rendu(legislature, ref, jour=None):
    """Plan (sommaire) et texte intégral d'un compte rendu de séance, téléchargé au besoin."""
    chemin = BRUT / legislature / "comptes-rendus" / f"{ref}.xml"
    recent = RAFRAICHIR_DEPUIS and jour and jour >= RAFRAICHIR_DEPUIS and ref not in _rafraichis
    if not chemin.exists() or recent:
        try:
            telecharger(f"{SITE_AN}/{ref}.xml", chemin)
            _rafraichis.add(ref)
        except (OSError, subprocess.CalledProcessError):
            if not chemin.exists():   # séance trop récente : l'Assemblée n'a pas encore publié son compte rendu
                CR_ABSENTS.append(f"{ref} (séance du {jour})")
                return [], ""
    racine = ET.parse(chemin).getroot()
    titres = []
    for s1 in racine.iter(f"{NS}sommaire1"):
        intitule = s1.find(f"{NS}titreStruct/{NS}intitule")
        if intitule is not None:
            t = re.sub(r"\s+", " ", "".join(intitule.itertext())).strip()
            if t and not t.startswith(("Ordre du jour", "Suspension", "Rappel", "Modification de l")):
                titres.append(t)
    brut = open(chemin, encoding="utf-8").read()
    corps = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", brut)))
    return titres, corps


# Formules officielles de la présidence quand un auteur retire son texte (une simple demande de retrait ne compte pas)
RETRAIT = re.compile(r"pris acte du retrait|il n.y a pas lieu de poursuivre la discussion|le texte a été retiré", re.I)


def segments_du_jour(legislature, seances):
    """Pour chaque titre de point discuté dans la journée : son texte intégral (pour repérer un retrait)."""
    segments = []
    for r in seances:
        ref = r.get("compteRenduRef")
        if not ref:
            continue
        titres, corps = compte_rendu(legislature, ref, r["timeStampDebut"][:10])
        # Les débats commencent à l'ouverture de la séance : avant, c'est le sommaire, qui répète les mêmes titres
        fin_sommaire = corps.find("La séance est ouverte")
        positions = []
        for t in titres:
            p = corps.find(t, max(fin_sommaire, 0) + 10)
            if p >= 0:
                positions.append((p, t))
        positions.sort()
        for i, (p, t) in enumerate(positions):
            fin = positions[i + 1][0] if i + 1 < len(positions) else len(corps)
            segments.append({"titre": t, "texte": corps[p:fin]})
        for t in titres:   # un titre présent au sommaire mais introuvable dans le corps compte quand même
            if t not in [x for _, x in positions]:
                segments.append({"titre": t, "texte": ""})
    return segments


# ---------------------------------------------------------------- niches

def points_du_jour(seances):
    """Points de l'ordre du jour d'une journée, dans l'ordre, sans doublon."""
    vus, points = set(), []
    for r in seances:
        for p in en_liste(((r.get("ODJ") or {}).get("pointsODJ") or {}).get("pointODJ")):
            if p["typePointODJ"] not in ("Discussion", "Suite de la discussion"):
                continue
            refs = en_liste((p.get("dossiersLegislatifsRefs") or {}).get("dossierRef"))
            objet = re.sub(r"^(Suite de la )?[Dd]iscussion,?( en [^,]+,)?( de la| d’une| d'une| du)? ", "", p["objet"]).strip(" ;.")
            if objet.startswith("Journée réservée"):
                continue
            cle = refs[0] if refs else normaliser(objet)[:80]
            if cle in vus:
                continue
            vus.add(cle)
            points.append({"dossier": refs[0] if refs else None, "objet": objet})
    return points


def relier_dossier(point, dossiers_ppl, jour, debattus):
    """Retrouve le dossier d'un point de l'ordre du jour qui n'en cite pas (comparaison des titres).

    Seuls comptent les dossiers déjà déposés ce jour-là (un texte redéposé plus tard porte souvent le même titre).
    À score égal, un dossier discuté en séance ce jour-là l'emporte, puis celui dont le titre recouvre le mieux l'intitulé
    (un titre très court ressemble à tout) ; s'il reste une égalité, aucun n'est retenu."""
    if point["dossier"]:
        return point["dossier"]
    objet = mots(point["objet"])
    candidats = [((proximite(point["objet"], titre), uid in debattus[jour], len(objet & mots(titre)) / (len(objet | mots(titre)) or 1)), uid)
                 for uid, titre, depot in dossiers_ppl if depot <= jour]
    return meilleur([c for c in candidats if c[0][0] >= 0.75], f"Niche du {jour} : dossier de « {point['objet'][:60]} »", seuil=(0.75,))


def detecter_niches(jours, dossiers, mandats):
    """Jeudis où la plupart des propositions inscrites viennent d'un même groupe."""
    candidats = []
    for jour, seances in sorted(jours.items()):
        if datetime.date.fromisoformat(jour).weekday() != 3:
            continue
        groupes = collections.Counter()
        for p in points_du_jour(seances):
            d = dossiers.get(p["dossier"]) if p["dossier"] else None
            if d and not d["procedureParlementaire"]["libelle"].lower().startswith("projet"):
                a = auteur(d, mandats, jour)
                if a.get("groupe"):
                    groupes[a["groupe"]] += 1
        if not groupes:
            continue
        g, n = groupes.most_common(1)[0]
        total = sum(groupes.values())
        if n >= 2 and n / total >= 0.6:
            candidats.append({"date": jour, "groupe": g, "textesDuGroupe": n, "textesAvecAuteur": total})
    return candidats


def titre_vise(titre_scrutin):
    """Le titre du texte dans l'intitulé d'un vote : « l'ensemble de la proposition de loi visant à … (première lecture) »."""
    t = re.sub(r"^(l['’]ensemble|l['’]article unique|la proposition de résolution)( du| de la| de l['’])? ", "", titre_scrutin)
    return re.sub(r"\s*\([^)]*\)\.?$", "", t)


def vote_final_du_jour(titre, scrutins, jour):
    """Le vote sur l'ensemble d'un texte ce jour-là, quand la décision ne le cite pas."""
    candidats = [(proximite(titre, titre_vise(s["titre"])), uid) for uid, s in scrutins.items()
                 if s["date"] == jour and s["titre"].startswith(("l'ensemble", "l’ensemble", "l'article unique", "la proposition de résolution"))]
    return meilleur(candidats, f"Vote sur l'ensemble du {jour} pour « {titre[:60]} »", scrutins=scrutins)


def vote_de_suppression(titre, scrutins, jour, articles=("article unique", "article premier")):
    """Le vote qui a supprimé l'article unique, ou le premier article, d'un texte (le texte est alors vidé)."""
    candidats = [(proximite(titre, titre_vise(s["titre"])), uid) for uid, s in scrutins.items()
                 if s["date"] == jour and s["titre"].startswith(("l'amendement de suppression", "l’amendement de suppression"))
                 and any(a in s["titre"] for a in articles) and s["sort"] == "adopté"]
    return meilleur(candidats, f"Vote de suppression du {jour} pour « {titre[:60]} »", scrutins=scrutins)


# Votes qui rejettent un texte sans examiner ses articles. Pour une proposition de résolution (commission d'enquête),
# la commission peut conclure au rejet : adopter ces conclusions revient à rejeter le texte
REJET = ("la motion de rejet préalable", "les conclusions de rejet de la commission")


def vote_premier_article(titre, scrutins, jour):
    """Le vote rejetant l'article premier d'un texte (le texte est alors vidé de son contenu principal)."""
    candidats = [(proximite(titre, s["titre"]), uid) for uid, s in scrutins.items()
                 if s["date"] == jour and s["titre"].startswith(("l'article premier", "l’article premier")) and s["sort"] == "rejeté"]
    return meilleur(candidats, f"Vote sur l'article premier du {jour} pour « {titre[:60]} »", scrutins=scrutins)


def vote_de_motion(titre, scrutins, jour, motion):
    """Une motion de procédure adoptée sur ce texte : « la motion de rejet préalable » ou « la motion de renvoi en commission »."""
    candidats = [(proximite(titre, s["titre"].split(" de la proposition de ", 1)[-1]), uid) for uid, s in scrutins.items()
                 if s["date"] == jour and s["titre"].startswith(motion) and s["sort"] == "adopté"]
    return meilleur(candidats, f"Motion du {jour} pour « {titre[:60]} »", scrutins=scrutins)


def statut_point(point, dossier_uid, dossiers, scrutins, segments, jour, vote_vers_dossier, debattus):
    """Statut d'un texte au programme d'une niche, d'après les décisions, les votes et le compte rendu."""
    d = dossiers.get(dossier_uid) if dossier_uid else None
    titre = d["titreDossier"]["titre"].replace("\r", " ") if d else point["objet"]
    resultat = {"titre": titre, "dossier": dossier_uid, "scrutin": None, "inverse": False}
    # En 2017-2022, les titres commencent souvent par un thème (« Société : … ») absent de l'intitulé des votes :
    # on cherche avec le titre complet, puis sans ce préfixe
    variantes = variantes_titre(titre)

    def chercher(fonction, *args):
        return next((v for t in variantes for v in [fonction(t, scrutins, jour, *args)] if v), None)

    # 1. Une décision de l'Assemblée ce jour-là
    if d:
        for dec in decisions_assemblee(d):
            if dec["date"] == jour:
                # « modifiée » : adoptée en deuxième lecture avec des changements
                resultat["statut"] = "adopte" if dec["statut"].startswith(("adopt", "modifi")) else "rejete" if dec["statut"].startswith("rejet") else dec["statut"]
                # Le vote cité par la décision, s'il porte bien sur ce texte (voir votes_des_dossiers)
                resultat["scrutin"] = next((v for v in dec["votes"] if vote_vers_dossier.get(v) == dossier_uid), None) or chercher(vote_final_du_jour)
                # Rejeté sans vote sur l'ensemble : par une motion de procédure, ou parce que ses articles ont été supprimés
                # un à un (vote inversé : « pour » la suppression = contre le texte)
                if resultat["statut"] == "rejete" and not resultat["scrutin"]:
                    resultat["scrutin"] = chercher(vote_de_motion, REJET) or chercher(vote_de_suppression)
                    resultat["inverse"] = bool(resultat["scrutin"])
                    if not resultat["scrutin"]:   # premier article rejeté : vote dans le même sens que le texte
                        resultat["scrutin"] = chercher(vote_premier_article)
                return resultat
    # Les étapes 2 et 3 cherchent un vote par son intitulé : pas pour un dossier que l'Assemblée n'a pas discuté ce
    # jour-là (le même texte existe souvent sous deux dossiers, celui du Sénat et celui de l'Assemblée)
    hors_seance = d and dossier_uid not in debattus[jour]
    # 2. Une motion de rejet préalable adoptée, ou un article unique supprimé : le texte est rejeté (le vote est inversé)
    vote = not hors_seance and (chercher(vote_de_motion, REJET) or chercher(vote_de_suppression, ("article unique",)))
    if vote:
        resultat.update(statut="rejete", scrutin=vote, inverse=True)
        return resultat
    # 3. Une motion de renvoi en commission adoptée : la discussion s'arrête, le texte retourne en commission
    vote = not hors_seance and chercher(vote_de_motion, "la motion de renvoi en commission")
    if vote:
        resultat.update(statut="renvoye", scrutin=vote, inverse=True)
        return resultat
    # 4. Le compte rendu : retiré en séance, discussion commencée, ou pas examiné. Un texte peut y figurer
    # plusieurs fois (début de la discussion, puis retrait en fin de journée) : on regarde tous ses passages
    passages = [sg for sg in segments if max(proximite(t, sg["titre"]) for t in variantes) >= 0.5]
    if passages:
        resultat["statut"] = "retire" if any(RETRAIT.search(sg["texte"]) for sg in passages) else "commence"
    else:
        resultat["statut"] = "pas_examine"
    return resultat


RANG_STATUT = {"pas_examine": 0, "commence": 1, "retire": 2, "renvoye": 2, "rejete": 3, "adopte": 3}


# ---------------------------------------------------------------- construction

def main():
    global RAFRAICHIR_DEPUIS
    if len(sys.argv) < 2:
        sys.exit("Usage : python3 pipeline/construire.py <législature> [--rafraichir-cr AAAA-MM-JJ]")
    leg = sys.argv[1]
    if "--rafraichir-cr" in sys.argv:
        RAFRAICHIR_DEPUIS = sys.argv[sys.argv.index("--rafraichir-cr") + 1]
    sortie = BASE / leg
    print("Chargement des groupes et des députés…", flush=True)
    organes, mandats = charger_groupes_et_mandats(leg)
    print("Chargement des votes…", flush=True)
    scrutins = charger_scrutins(leg, organes)
    print("Chargement des dossiers…", flush=True)
    dossiers = charger_dossiers(leg)
    print("Chargement de l'ordre du jour…", flush=True)
    jours = charger_seances(leg)
    # Les propositions de loi (y compris organiques et constitutionnelles : « Projet ou proposition de loi … ») et de
    # résolution ; pas les projets du gouvernement, ni les rapports et missions d'information, qui portent le même titre
    dossiers_ppl = [(uid, d["titreDossier"]["titre"], premier_depot(d)) for uid, d in dossiers.items()
                    if d["procedureParlementaire"]["libelle"].lower().startswith(("proposition", "résolution", "projet ou proposition", "commission d'enquête"))]
    titres_tous = [d["titreDossier"]["titre"] for d in dossiers.values()]   # rapports compris : noms possibles d'une ligne
    utilises, textes = set(), {}

    class ListeSansDoublon(list):
        def append(self, x):
            if x not in self:
                super().append(x)
    a_verifier = ListeSansDoublon()
    debattus = debattus_par_jour(dossiers)
    vote_vers_dossier = votes_des_dossiers(dossiers, scrutins, debattus, a_verifier)

    # Groupes
    groupes = {}
    for uid, o in organes.items():
        g = groupes.setdefault(o["abrev"], {"abrev": o["abrev"], "nom": o["nom"], "couleur": o["couleur"], "position": o["position"],
                                            "organes": [], "_debut": ""})
        g["organes"].append(uid)
        if not o["fin"] or o["debut"] > g["_debut"]:   # le nom le plus récent l'emporte
            g.update(nom=o["nom"], couleur=o["couleur"], position=o["position"], _debut=o["debut"] if o["fin"] else "9999")
    for g in groupes.values():
        del g["_debut"]
    dernier_vote = max(scrutins.values(), key=lambda s: (s["date"], s["numero"]))
    for r in dernier_vote["groupes"]:
        if r["g"] in groupes:
            groupes[r["g"]]["deputes"] = r["m"]
    # Groupe dissous en cours de législature (EDS, 2020) : ses sièges à son dernier vote, et la date de ce vote
    for vote in sorted(scrutins.values(), key=lambda s: (s["date"], s["numero"]), reverse=True):
        for r in vote["groupes"]:
            if r["g"] in groupes and "deputes" not in groupes[r["g"]]:
                groupes[r["g"]].update(deputes=r["m"], fin=vote["date"])
    liste_groupes = sorted(groupes.values(), key=lambda g: ORDRE_HEMICYCLE[leg].index(g["abrev"]) if g["abrev"] in ORDRE_HEMICYCLE[leg] else 99)

    # Niches : détection, puis validation manuelle
    print("Détection des niches…", flush=True)
    candidats = detecter_niches(jours, dossiers, mandats)
    chemin_validation = VALIDATION / f"niches-{leg}.json"
    validation = {v["date"]: v for v in lire_json(chemin_validation, [])}
    for c in candidats:
        validation.setdefault(c["date"], {"date": c["date"], "groupe": c["groupe"], "statut": "a_valider"})
    ecrire_json(chemin_validation, sorted(validation.values(), key=lambda v: v["date"]))

    niches, textes_niche = [], []
    for v in sorted(validation.values(), key=lambda v: v["date"]):
        if v["statut"] == "rejete":
            continue
        jour = v["date"]
        print(f"  niche du {jour} ({v['groupe']})…", flush=True)
        segments = segments_du_jour(leg, jours.get(jour, []))
        programme = []
        for p in points_du_jour(jours.get(jour, [])):
            uid = relier_dossier(p, dossiers_ppl, jour, debattus)
            if not uid:
                a_verifier.append(f"Niche du {jour} : pas de dossier trouvé pour « {p['objet'][:90]} »")
            ligne = statut_point(p, uid, dossiers, scrutins, segments, jour, vote_vers_dossier, debattus)
            # Les autres noms de la ligne (intitulé de l'ordre du jour, titres des dossiers ressemblants) : les corrections
            # de donnees/validation désignent une ligne par le titre qu'elle avait lors de la vérification
            ligne["alias"] = [t for t in titres_tous if not p["dossier"] and proximite(p["objet"], t) >= 0.75]
            ligne["objet"] = p["objet"]
            # Un même texte peut figurer deux fois à l'ordre du jour (avec ou sans référence, ou sous deux dossiers) :
            # on garde une seule ligne, avec le statut le plus avancé
            doublon = next((x for x in programme if (uid and x["dossier"] == uid) or proximite(x["titre"], ligne["titre"]) >= 0.9), None)
            # Un vote rattaché par l'open data à un autre texte, ou déjà retenu pour un autre texte : pas pour celui-ci
            autre = ligne["scrutin"] and (vote_vers_dossier.get(ligne["scrutin"], uid) != uid
                                         or any(l["scrutin"] == ligne["scrutin"] for l in programme if l is not doublon)
                                         or any(t["scrutin"] == ligne["scrutin"] and t["dossier"] != uid for t in textes_niche))
            if autre:
                a_verifier.append(f"Niche du {jour} : le vote n° {scrutins[ligne['scrutin']]['numero']} retrouvé pour « {ligne['titre'][:60]} » "
                                  f"porte sur un autre texte, écarté")
                ligne.update(scrutin=None, inverse=False)
            if ligne["scrutin"]:
                utilises.add(ligne["scrutin"])
            if ligne["statut"] in ("adopte", "rejete") and uid:
                d = dossiers[uid]
                textes_niche[:] = [t for t in textes_niche if not (t["dossier"] == uid and t["date"] == jour)]
                textes_niche.append({"id": uid, "dossier": uid, "origine": "niche", "date": jour, "titre": ligne["titre"],
                                     "procedure": d["procedureParlementaire"]["libelle"], "auteur": auteur(d, mandats, jour),
                                     "statut": ligne["statut"], "scrutin": ligne["scrutin"], "inverse": ligne["inverse"],
                                     "suite": suite_donnee(d), "resume": None, "arguments": None, "relu": False})
                if not ligne["scrutin"]:
                    a_verifier.append(f"Niche du {jour} : « {ligne['titre'][:80]} » {ligne['statut']} sans vote public retrouvé (main levée ?)")
            if doublon:
                # La ligne au statut le plus avancé ; à statut égal, celle qui a un dossier
                rang, rang_doublon = RANG_STATUT.get(ligne["statut"], 0), RANG_STATUT.get(doublon["statut"], 0)
                if rang > rang_doublon or (rang == rang_doublon and ligne["dossier"] and not doublon["dossier"]):
                    doublon.update({k: ligne[k] for k in ("titre", "dossier", "statut", "scrutin", "inverse")})
                continue
            programme.append({k: ligne[k] for k in ("titre", "dossier", "statut", "scrutin", "inverse", "alias", "objet")})
        # Corrections faites lors de la vérification (donnees/validation) : statut rectifié, ou ligne qui n'appartient pas à la niche.
        # La ligne est retrouvée par son titre, sinon par l'un de ses autres noms (début, puis partie du titre)
        for c in v.get("corrections", []):
            titre_c = normaliser(c["titre"])
            cible = (next((l for l in programme if normaliser(l["titre"]).startswith(titre_c)), None)
                     or next((l for l in programme if titre_c in normaliser(l["titre"])), None)
                     or next((l for l in programme if any(normaliser(a).startswith(titre_c) for a in l["alias"] + [l["objet"]])), None)
                     or next((l for l in programme if titre_c in normaliser(l["objet"])), None))
            if not cible:
                a_verifier.append(f"Niche du {jour} : correction sans ligne correspondante « {c['titre'][:60]} »")
            elif c.get("exclure"):
                programme.remove(cible)
            else:
                cible.update(statut=c["statut"], corrige=True)
        for l in programme:
            del l["alias"], l["objet"]
        nb_votes = sum(1 for s in scrutins.values() if s["date"] == jour)
        niches.append({"date": jour, "groupe": v["groupe"], "validee": v["statut"] == "valide", "votesDuJour": nb_votes, "programme": programme})

    # Un même dossier voté dans plusieurs niches de la législature (lectures successives) : la plus récente garde
    # l'identifiant « dossier », les précédentes deviennent « dossier@date »
    for t in textes_niche:
        if any(x["dossier"] == t["dossier"] and x["date"] > t["date"] for x in textes_niche):
            t["id"] = f"{t['dossier']}@{t['date']}"
        textes[t["id"]] = t

    # Votes solennels
    print("Votes solennels…", flush=True)
    votes_des_niches = {t["scrutin"] for t in textes.values() if t["scrutin"]} | {l["scrutin"] for n in niches for l in n["programme"] if l["scrutin"]}
    nb_solennels, ignores = 0, collections.Counter()
    for vuid, s in sorted(scrutins.items(), key=lambda x: x[1]["numero"]):
        if s["type"] != "SPS":
            continue
        if s["titre"].startswith("la déclaration"):
            ignores["déclarations du gouvernement"] += 1
            continue
        nb_solennels += 1
        if vuid in votes_des_niches:   # vote solennel pendant une niche : le texte est déjà publié avec sa niche
            ignores["déjà dans une niche"] += 1
            continue
        if vuid in vote_vers_dossier:
            uid = vote_vers_dossier[vuid]
        else:   # secours : parmi les dossiers discutés en séance ce jour-là, celui dont le titre correspond le mieux
            uid = meilleur([(correspondance(dossiers[u], s), u) for u in debattus[s["date"]] if premier_depot(dossiers[u]) <= s["date"]],
                           f"Vote solennel n° {s['numero']} du {s['date']} : dossier")
        if not uid:
            a_verifier.append(f"Vote solennel n° {s['numero']} du {s['date']} sans dossier relié : « {s['titre'][:90]} »")
            continue
        d = dossiers[uid]
        cle = f"{uid}@{s['date']}"   # un même texte peut avoir plusieurs votes solennels (lectures successives)
        # Vote sur une motion de procédure (rejet préalable, renvoi en commission) ou sur des conclusions de rejet :
        # voter pour, c'est voter contre le texte ; le sens est inversé, comme pour les niches
        inverse = s["titre"].startswith(REJET + ("la motion de renvoi en commission",))
        adopte = (s["sort"] == "adopté") != inverse
        if cle in textes:   # deux votes solennels le même jour sur le même texte : le dernier, sauf s'il porte sur une motion
            if inverse and not textes[cle]["inverse"]:
                continue
            utilises.discard(textes[cle]["scrutin"])
        textes[cle] = {"id": cle, "dossier": uid, "origine": "solennel", "date": s["date"], "titre": d["titreDossier"]["titre"].replace("\r", " "),
                       "lecture": s["titre"][s["titre"].rfind("(") + 1:].rstrip(").") if "(" in s["titre"] else None,
                       "procedure": d["procedureParlementaire"]["libelle"], "auteur": auteur(d, mandats, s["date"]),
                       "statut": "adopte" if adopte else "rejete", "scrutin": vuid, "inverse": inverse,
                       "suite": suite_donnee(d), "resume": None, "arguments": None, "relu": False}
        utilises.add(vuid)

    for x in EX_AEQUO:
        a_verifier.append(x)
    for ref in CR_ABSENTS:
        a_verifier.append(f"Compte rendu pas encore publié : {ref}. Statuts de ce jour à reprendre à la prochaine mise à jour")
    for t in textes.values():
        if t["auteur"]["type"] == "inconnu":
            a_verifier.append(f"Auteur non identifié : « {t['titre'][:80]} » ({t.get('dossier') or t['id']})")

    # Écriture
    ecrire_json(sortie / "groupes.json", liste_groupes)
    ecrire_json(sortie / "niches.json", niches)
    ecrire_json(sortie / "textes.json", sorted(textes.values(), key=lambda t: t["date"]))
    ecrire_json(sortie / "scrutins.json", {uid: scrutins[uid] for uid in sorted(utilises, key=lambda u: scrutins[u]["numero"])})

    statuts = collections.Counter(l["statut"] for n in niches for l in n["programme"])
    lignes = [f"# Base de la {leg}e législature", "",
              f"Construite le {datetime.date.today().isoformat()} à partir de l'open data de l'Assemblée nationale.", "",
              "## Chiffres", "",
              f"- Groupes : {len(liste_groupes)}",
              f"- Niches : {len(niches)} ({sum(validation[n['date']]['statut'] == 'valide' for n in niches)} validées à la main, "
              f"{sum(validation[n['date']]['statut'] == 'verifie_ia' for n in niches)} vérifiées par IA, "
              f"{sum(validation[n['date']]['statut'] == 'a_valider' for n in niches)} à valider)",
              f"- Textes au programme des niches : {sum(statuts.values())} — " + ", ".join(f"{k} : {v}" for k, v in statuts.most_common()),
              f"- Votes solennels sur des textes : {nb_solennels} (écartés : " + ", ".join(f"{k} : {v}" for k, v in ignores.items()) + ")",
              f"- Textes dans la base : {len(textes)}",
              f"- Votes enregistrés dans la base : {len(utilises)}", "",
              "## Niches à valider", "",
              f"Dans `donnees/validation/niches-{leg}.json`, passer chaque niche à `valide` ou `rejete` après vérification.", ""]
    lignes += [f"- {n['date']} : {n['groupe']}" for n in niches if not n["validee"]] or ["Aucune."]
    lignes += ["", "## Points à vérifier", ""] + ([f"- {x}" for x in a_verifier] or ["Aucun."])
    (sortie / "rapport.md").write_text("\n".join(lignes) + "\n", encoding="utf-8")
    print("\n".join(lignes[:12]))


if __name__ == "__main__":
    main()
