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

La liste des niches validées à la main se trouve dans donnees/validation/niches-<législature>.json.
"""
import collections
import datetime
import html
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

from commun import (BASE, BRUT, ORGANE_ASSEMBLEE, ORGANE_SENAT, SITE_AN, VALIDATION, actes, ecrire_json,
                    en_liste, lire_json, lire_zip, normaliser, proximite, telecharger)

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
    return scrutins


def charger_dossiers(legislature):
    dossiers = {}
    for doc in lire_zip(BRUT / legislature / "dossiers.zip", "dossierParlementaire"):
        d = doc["dossierParlementaire"]
        dossiers[d["uid"]] = d
    return dossiers


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


def decisions_assemblee(dossier):
    """Décisions de l'Assemblée sur ce texte : date, résultat, votes associés."""
    res = []
    for a in actes(dossier):
        if a["codeActe"].endswith("DEBATS-DEC") and a.get("organeRef") in ORGANE_ASSEMBLEE.values() and a.get("dateActe"):
            res.append({"date": a["dateActe"][:10], "statut": (a.get("statutConclusion") or {}).get("libelle", ""),
                        "votes": en_liste((a.get("voteRefs") or {}).get("voteRef"))})
    return res


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


def relier_dossier(point, dossiers_ppl):
    """Retrouve le dossier d'un point de l'ordre du jour qui n'en cite pas (comparaison des titres)."""
    if point["dossier"]:
        return point["dossier"], 1.0
    meilleur, score = None, 0.0
    for uid, titre in dossiers_ppl:
        s = proximite(point["objet"], titre)
        if s > score:
            meilleur, score = uid, s
    return (meilleur, score) if score >= 0.75 else (None, score)


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
    candidats = [c for c in candidats if c[0] >= 0.75]
    return max(candidats)[1] if candidats else None


def vote_de_suppression(titre, scrutins, jour, articles=("article unique", "article premier")):
    """Le vote qui a supprimé l'article unique, ou le premier article, d'un texte (le texte est alors vidé)."""
    candidats = [(proximite(titre, titre_vise(s["titre"])), uid) for uid, s in scrutins.items()
                 if s["date"] == jour and s["titre"].startswith(("l'amendement de suppression", "l’amendement de suppression"))
                 and any(a in s["titre"] for a in articles) and s["sort"] == "adopté"]
    candidats = [c for c in candidats if c[0] >= 0.75]
    return max(candidats)[1] if candidats else None


# Votes qui rejettent un texte sans examiner ses articles. Pour une proposition de résolution (commission d'enquête),
# la commission peut conclure au rejet : adopter ces conclusions revient à rejeter le texte
REJET = ("la motion de rejet préalable", "les conclusions de rejet de la commission")


def vote_premier_article(titre, scrutins, jour):
    """Le vote rejetant l'article premier d'un texte (le texte est alors vidé de son contenu principal)."""
    candidats = [(proximite(titre, s["titre"]), uid) for uid, s in scrutins.items()
                 if s["date"] == jour and s["titre"].startswith(("l'article premier", "l’article premier")) and s["sort"] == "rejeté"]
    candidats = [c for c in candidats if c[0] >= 0.75]
    return max(candidats)[1] if candidats else None


def vote_de_motion(titre, scrutins, jour, motion):
    """Une motion de procédure adoptée sur ce texte : « la motion de rejet préalable » ou « la motion de renvoi en commission »."""
    candidats = [(proximite(titre, s["titre"].split(" de la proposition de ", 1)[-1]), uid) for uid, s in scrutins.items()
                 if s["date"] == jour and s["titre"].startswith(motion) and s["sort"] == "adopté"]
    candidats = [c for c in candidats if c[0] >= 0.75]
    return max(candidats)[1] if candidats else None


def statut_point(point, dossier_uid, dossiers, scrutins, segments, jour):
    """Statut d'un texte au programme d'une niche, d'après les décisions, les votes et le compte rendu."""
    d = dossiers.get(dossier_uid) if dossier_uid else None
    titre = d["titreDossier"]["titre"].replace("\r", " ") if d else point["objet"]
    resultat = {"titre": titre, "dossier": dossier_uid, "scrutin": None, "inverse": False}
    # En 2017-2022, les titres commencent souvent par un thème (« Société : … ») absent de l'intitulé des votes :
    # on cherche avec le titre complet, puis sans ce préfixe
    variantes = list(dict.fromkeys([titre, re.sub(r"^[^:]{3,40} : ", "", titre)]))

    def chercher(fonction, *args):
        return next((v for t in variantes for v in [fonction(t, scrutins, jour, *args)] if v), None)

    # 1. Une décision de l'Assemblée ce jour-là
    if d:
        for dec in decisions_assemblee(d):
            if dec["date"] == jour:
                # « modifiée » : adoptée en deuxième lecture avec des changements
                resultat["statut"] = "adopte" if dec["statut"].startswith(("adopt", "modifi")) else "rejete" if dec["statut"].startswith("rejet") else dec["statut"]
                resultat["scrutin"] = next((v for v in dec["votes"] if v in scrutins), None) or chercher(vote_final_du_jour)
                # Rejeté sans vote sur l'ensemble : par une motion de procédure, ou parce que ses articles ont été supprimés
                # un à un (vote inversé : « pour » la suppression = contre le texte)
                if resultat["statut"] == "rejete" and not resultat["scrutin"]:
                    resultat["scrutin"] = chercher(vote_de_motion, REJET) or chercher(vote_de_suppression)
                    resultat["inverse"] = bool(resultat["scrutin"])
                    if not resultat["scrutin"]:   # premier article rejeté : vote dans le même sens que le texte
                        resultat["scrutin"] = chercher(vote_premier_article)
                return resultat
    # 2. Une motion de rejet préalable adoptée, ou un article unique supprimé : le texte est rejeté (le vote est inversé)
    vote = chercher(vote_de_motion, REJET) or chercher(vote_de_suppression, ("article unique",))
    if vote:
        resultat.update(statut="rejete", scrutin=vote, inverse=True)
        return resultat
    # 3. Une motion de renvoi en commission adoptée : la discussion s'arrête, le texte retourne en commission
    vote = chercher(vote_de_motion, "la motion de renvoi en commission")
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
    dossiers_ppl = [(uid, d["titreDossier"]["titre"]) for uid, d in dossiers.items()
                    if not d["procedureParlementaire"]["libelle"].lower().startswith("projet")]
    utilises, textes, a_verifier = set(), {}, []

    class ListeSansDoublon(list):
        def append(self, x):
            if x not in self:
                super().append(x)
    a_verifier = ListeSansDoublon()

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
    liste_groupes = sorted(groupes.values(), key=lambda g: ORDRE_HEMICYCLE[leg].index(g["abrev"]) if g["abrev"] in ORDRE_HEMICYCLE[leg] else 99)

    # Niches : détection, puis validation manuelle
    print("Détection des niches…", flush=True)
    candidats = detecter_niches(jours, dossiers, mandats)
    chemin_validation = VALIDATION / f"niches-{leg}.json"
    validation = {v["date"]: v for v in lire_json(chemin_validation, [])}
    for c in candidats:
        validation.setdefault(c["date"], {"date": c["date"], "groupe": c["groupe"], "statut": "a_valider"})
    ecrire_json(chemin_validation, sorted(validation.values(), key=lambda v: v["date"]))

    niches = []
    for v in sorted(validation.values(), key=lambda v: v["date"]):
        if v["statut"] == "rejete":
            continue
        jour = v["date"]
        print(f"  niche du {jour} ({v['groupe']})…", flush=True)
        segments = segments_du_jour(leg, jours.get(jour, []))
        programme = []
        for p in points_du_jour(jours.get(jour, [])):
            uid, score = relier_dossier(p, dossiers_ppl)
            if not uid:
                a_verifier.append(f"Niche du {jour} : pas de dossier trouvé pour « {p['objet'][:90]} »")
            ligne = statut_point(p, uid, dossiers, scrutins, segments, jour)
            if ligne["scrutin"]:
                utilises.add(ligne["scrutin"])
            if ligne["statut"] in ("adopte", "rejete") and uid:
                d = dossiers[uid]
                textes[uid] = {"id": uid, "origine": "niche", "date": jour, "titre": ligne["titre"],
                               "procedure": d["procedureParlementaire"]["libelle"], "auteur": auteur(d, mandats, jour),
                               "statut": ligne["statut"], "scrutin": ligne["scrutin"], "inverse": ligne["inverse"],
                               "suite": suite_donnee(d), "resume": None, "arguments": None, "relu": False}
                if not ligne["scrutin"]:
                    a_verifier.append(f"Niche du {jour} : « {ligne['titre'][:80]} » {ligne['statut']} sans vote public retrouvé (main levée ?)")
            # Un même texte peut figurer deux fois à l'ordre du jour (avec ou sans référence, ou sous deux dossiers) :
            # on garde une seule ligne, avec le statut le plus avancé
            doublon = next((x for x in programme if (uid and x["dossier"] == uid) or proximite(x["titre"], ligne["titre"]) >= 0.9), None)
            if doublon:
                if RANG_STATUT.get(ligne["statut"], 0) > RANG_STATUT.get(doublon["statut"], 0):
                    doublon.update({k: ligne[k] for k in ("titre", "dossier", "statut", "scrutin", "inverse")})
                continue
            programme.append({k: ligne[k] for k in ("titre", "dossier", "statut", "scrutin", "inverse")})
        nb_votes = sum(1 for s in scrutins.values() if s["date"] == jour)
        niches.append({"date": jour, "groupe": v["groupe"], "validee": v["statut"] == "valide", "votesDuJour": nb_votes, "programme": programme})

    # Votes solennels
    print("Votes solennels…", flush=True)
    vote_vers_dossier = {}
    for uid, d in dossiers.items():
        for dec in decisions_assemblee(d):
            for v in dec["votes"]:
                vote_vers_dossier[v] = uid
    nb_solennels, ignores = 0, collections.Counter()
    for vuid, s in sorted(scrutins.items(), key=lambda x: x[1]["numero"]):
        if s["type"] != "SPS":
            continue
        if s["titre"].startswith("la déclaration"):
            ignores["déclarations du gouvernement"] += 1
            continue
        nb_solennels += 1
        uid = vote_vers_dossier.get(vuid)
        if not uid:   # secours : le dossier dont le titre correspond le mieux à l'intitulé du vote
            vise = titre_vise(s["titre"])
            score, uid = max(((proximite(vise, d["titreDossier"]["titre"]), u) for u, d in dossiers.items()), default=(0, None))
            uid = uid if score >= 0.75 else None
        if not uid:
            a_verifier.append(f"Vote solennel n° {s['numero']} du {s['date']} sans dossier relié : « {s['titre'][:90]} »")
            continue
        d = dossiers[uid]
        cle = f"{uid}@{s['date']}"   # un même texte peut avoir plusieurs votes solennels (lectures successives)
        textes[cle] = {"id": cle, "dossier": uid, "origine": "solennel", "date": s["date"], "titre": d["titreDossier"]["titre"].replace("\r", " "),
                       "lecture": s["titre"][s["titre"].rfind("(") + 1:].rstrip(").") if "(" in s["titre"] else None,
                       "procedure": d["procedureParlementaire"]["libelle"], "auteur": auteur(d, mandats, s["date"]),
                       "statut": "adopte" if s["sort"] == "adopté" else "rejete", "scrutin": vuid, "inverse": False,
                       "suite": suite_donnee(d), "resume": None, "arguments": None, "relu": False}
        utilises.add(vuid)

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
              f"- Niches : {len(niches)} ({sum(n['validee'] for n in niches)} validées à la main, {sum(not n['validee'] for n in niches)} à valider)",
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
