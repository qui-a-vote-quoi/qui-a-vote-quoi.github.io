"""Prépare les données du site à partir de la base et des textes rédigés à la main.

Usage : python3 pipeline/publier.py [15 16 17]   (par défaut, les trois législatures)

Lit donnees/base/<législature>/, donnees/validation/niches-<législature>.json et donnees/redaction/*.json
(sujet, titre clair, résumé, arguments de chaque texte), et écrit site/donnees.js.

Niveaux affichés sur le site :
- une niche est publiée si elle a été vérifiée, par un humain (« valide ») ou par IA dans les comptes rendus (« verifie_ia ») ;
- un résumé est « a_venir », « ia » (rédigé par IA, non vérifié par un humain) ou « relu » (relu par un humain).
Les votes solennels sont tous publiés.
"""
import datetime
import hashlib
import json
import re
import sys

from commun import BASE, RACINE, VALIDATION, lire_json

SITE = RACINE / "site"
# Un député élu sous la législature précédente : son groupe d'alors, rattaché au groupe qui lui a succédé
NICHES_PUBLIEES = ("valide", "verifie_ia")
# Couleurs choisies à la main pour la législature actuelle (contraste vérifié) ; ailleurs, celles de l'Assemblée
COULEURS = {
    "LFI-NFP": "#c0272d", "GDR": "#8e1b1b", "ECOS": "#2e7d3a", "SOC": "#c2306a", "LIOT": "#b08850", "DEM": "#e9862b",
    "EPR": "#d8b31c", "HOR": "#3aa6c2", "DR": "#2f6fd0", "UDR": "#43497f", "RN": "#1f2f7a", "NI": "#6b707a",
}
SUCCESSEUR = {"ECOLO": "ECOS", "GDR-NUPES": "GDR", "LFI-NUPES": "LFI-NFP", "RE": "EPR", "LR": "DR", "SOC-A": "SOC"}
MOIS = "janvier février mars avril mai juin juillet août septembre octobre novembre décembre".split()
STATUTS = {"retire": "retiree", "commence": "commence", "pas_examine": "pas_examine", "renvoye": "renvoye"}


def insecables(texte):
    """Typographie française : espace insécable devant % : ; ? ! » et après «, pour qu'ils ne se retrouvent pas seuls en début de ligne."""
    if not texte:
        return texte
    texte = re.sub(r" ([%:;?!»])", "\u00a0\\1", texte)
    return re.sub(r"« ", "«\u00a0", texte)


def titre_lisible(titre):
    """« Proposition de loi visant à interdire … » → « Interdire … ». Les projets de loi gardent leur titre."""
    t = re.sub(r"^Proposition de (loi|résolution)( organique| constitutionnelle)? (visant à|tendant à|relative à|portant|pour) ", "", titre.strip())
    return t[:1].upper() + t[1:]


def vote_sur(scrutin):
    """Ce sur quoi portait le vote retenu, quand ce n'est pas l'ensemble du texte."""
    t = scrutin["titre"]
    if t.startswith("la motion de rejet préalable"):
        return "motion_rejet"
    if t.startswith("les conclusions de rejet"):
        return "conclusions_rejet"
    if t.startswith("la motion de renvoi en commission"):
        return "renvoi"
    if "amendement de suppression" in t:
        return "suppression_article_unique" if "article unique" in t else "suppression_premier_article"
    if t.startswith(("l'article premier", "l’article premier")):
        return "premier_article"
    return None


def etape(t):
    """Ce qui s'est passé ensuite, en une phrase."""
    s = t["suite"]
    if s["promulgation"]:
        d = datetime.date.fromisoformat(s["promulgation"])
        return f"C'est une loi depuis le {d.day} {MOIS[d.month - 1]} {d.year}" + (f" (loi n° {s['numeroLoi']})." if s["numeroLoi"] else ".")
    code = re.sub(r"\d", "", s["derniereEtape"] or "")
    if code.startswith("CC-"):
        return "Le Conseil constitutionnel s'est prononcé ; la loi n'est pas encore promulguée."
    if code.startswith("CMP"):
        return "Une commission de députés et de sénateurs cherche un texte commun."
    if code.startswith("SN"):
        return "Le texte est au Sénat, qui doit l'examiner à son tour."
    if t["statut"] == "rejete":
        return "Rien n'est prévu pour l'instant : le texte s'arrête à cette étape."
    return "Le texte doit poursuivre son parcours au Parlement."


def vote(scrutin):
    return {"scrutin": scrutin["numero"], "date": scrutin["date"], "pour": scrutin["pour"], "contre": scrutin["contre"],
            "abst": scrutin["abst"], "groupes": scrutin["groupes"], "voteSur": vote_sur(scrutin)}


def luminance(couleur):
    r, g, b = (int(couleur[i:i + 2], 16) / 255 for i in (1, 3, 5))
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in (r, g, b)]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def couleur_texte(fond):
    """Blanc ou presque noir : celui qui contraste le plus avec la couleur du groupe."""
    l = luminance(fond)
    return "#fff" if (1.05 / (l + 0.05)) >= ((l + 0.05) / 0.0603) else "#161a22"


def groupes(legs):
    """Les groupes de toutes les législatures, par sigle : nom et couleur les plus récents, sièges par législature."""
    resultat = {}
    for leg in sorted(legs):
        for g in lire_json(BASE / leg / "groupes.json"):
            if not g.get("deputes"):
                continue
            couleur = COULEURS.get(g["abrev"]) or g["couleur"] or "#6b707a"
            entree = resultat.setdefault(g["abrev"], {"periodes": {}})
            entree.update(nom=g["nom"], c=couleur, t=couleur_texte(couleur))
            entree["periodes"][leg] = {"deputes": g["deputes"], "position": g.get("position")}
    return resultat


def publier_legislature(leg, redaction, sigles):
    validation = {v["date"]: v["statut"] for v in lire_json(VALIDATION / f"niches-{leg}.json", [])}
    niches = [n for n in lire_json(BASE / leg / "niches.json") if validation.get(n["date"]) in NICHES_PUBLIEES]
    dates_niches = {n["date"] for n in niches}
    scrutins = lire_json(BASE / leg / "scrutins.json")
    textes = []
    for t in lire_json(BASE / leg / "textes.json"):
        if not t["scrutin"] or (t["origine"] == "niche" and t["date"] not in dates_niches):
            continue
        dossier = t.get("dossier") or t["id"]
        r = redaction.get(dossier, {})
        a = t["auteur"]
        entree = {"id": t["id"], "type": t["origine"], "dossier": dossier, "leg": leg,
                  "legDossier": re.search(r"L(\d+)N", dossier).group(1),
                  "date": t["date"], "titre": r.get("titreClair") or titre_lisible(t["titre"]), "titreOfficiel": t["titre"],
                  "lecture": t.get("lecture"), "theme": r.get("theme") or "Autres sujets", "sujetNiveau": r.get("sujetNiveau"),
                  "enClair": r.get("enClair"), "concerne": r.get("concerne"), "arguments": r.get("arguments"),
                  "niveau": r.get("niveau") or "a_venir",
                  "mesures": r.get("mesures") or [], "mesuresNiveau": r.get("mesuresNiveau"),
                  "inverse": t["inverse"], "loi": bool(t["suite"]["promulgation"]), "etape": etape(t)}
        if a["type"] == "depute":
            # Auteur élu sous une législature précédente : son groupe d'alors, rattaché à celui qui lui a succédé
            entree["groupe"] = a["groupe"] if a["groupe"] in sigles else SUCCESSEUR.get(a["groupe"], a["groupe"])
        else:
            entree["auteur"], entree["auteurCourt"] = {"gouvernement": ("le gouvernement", "Gouvernement"),
                                                       "senat": ("des sénateurs", "Sénat")}.get(a["type"], ("un auteur non identifié", "?"))
        for champ in ("titre", "titreOfficiel", "enClair", "concerne"):
            entree[champ] = insecables(entree[champ])
        entree.update(vote(scrutins[t["scrutin"]]))
        textes.append(entree)
    ids = {t["id"] for t in textes}

    sortie_niches = []
    for n in niches:
        programme = []
        for l in n["programme"]:
            if l["dossier"] in ids and l["statut"] in ("adopte", "rejete"):
                programme.append({"id": l["dossier"]})
                continue
            ligne = {"titre": titre_lisible(l["titre"]), "dossier": l["dossier"]}
            if l["statut"] in ("adopte", "rejete"):
                # Sans scrutin public ce jour-là : vote à main levée, ou statut rectifié à la vérification (vote un autre jour…)
                ligne["statut"] = l["statut"] + ("_sans_detail" if l.get("corrige") else "_main_levee")
            else:
                ligne["statut"] = STATUTS[l["statut"]]
            if l["scrutin"]:
                ligne["vote"] = dict(vote(scrutins[l["scrutin"]]), inverse=l["inverse"])
            programme.append(ligne)
        sortie_niches.append({"date": n["date"], "leg": leg, "groupe": n["groupe"], "scrutins": n["votesDuJour"],
                              "verification": validation[n["date"]], "programme": programme})
    return sortie_niches, textes


def main():
    legs = sys.argv[1:] or ["15", "16", "17"]
    redaction = {}
    for fichier in sorted((RACINE / "donnees" / "redaction").glob("*.json")):
        redaction.update(lire_json(fichier))
    sigles = groupes(legs)
    niches, textes = [], []
    for leg in legs:
        n, t = publier_legislature(leg, redaction, {g for g, x in sigles.items() if leg in x["periodes"]})
        niches += n
        textes += t
        print(f"{leg}e législature : {len(n)} niches publiées, {len(t)} textes.")

    infos = {"legislatures": sorted(legs), "miseAJour": datetime.date.today().isoformat()}
    SITE.mkdir(exist_ok=True)
    with open(SITE / "donnees.js", "w", encoding="utf-8") as f:
        f.write("// Fichier produit par pipeline/publier.py à partir de l'open data de l'Assemblée nationale. Ne pas modifier à la main.\n")
        for nom, valeur in (("INFOS", infos), ("GROUPES", sigles), ("NICHES", niches), ("TEXTES", textes)):
            f.write(f"window.{nom} = {json.dumps(valeur, ensure_ascii=False, separators=(',', ':'))};\n")
    # La page charge donnees.js?v=<empreinte> : un navigateur ne garde pas en cache d'anciennes données
    empreinte = hashlib.sha1((SITE / "donnees.js").read_bytes()).hexdigest()[:10]
    page = SITE / "index.html"
    page.write_text(re.sub(r'<script src="donnees\.js[^"]*">', f'<script src="donnees.js?v={empreinte}">', page.read_text(encoding="utf-8")), encoding="utf-8")
    niveaux = {k: sum(1 for t in textes if t["niveau"] == k) for k in ("relu", "ia", "a_venir")}
    print(f"Résumés : {niveaux['relu']} relus, {niveaux['ia']} rédigés par IA, {niveaux['a_venir']} à venir.")
    print(f"Écrit : site/donnees.js ({(SITE / 'donnees.js').stat().st_size // 1000} Ko)")


if __name__ == "__main__":
    main()
