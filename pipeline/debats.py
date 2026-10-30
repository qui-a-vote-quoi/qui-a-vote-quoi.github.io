"""Extrait le débat d'un texte (présentation et discussion générale) des comptes rendus de séance.

Usage : python3 pipeline/debats.py 17 [DOSSIER ...]

Pour chaque texte d'une journée réservée (ou les dossiers donnés), écrit donnees/brut/<législature>/debats/<dossier>.json :
les interventions dans l'ordre, avec l'orateur, sa qualité (rapporteur, ministre…), son groupe à la date du débat
et le texte exact. Sert à « Vivre le débat » : les répliques sont ensuite choisies (par IA, voir CHARTE-NEUTRALITE.md)
puis vérifiées mot pour mot contre ce fichier (pipeline/verifier_debats.py).
"""
import re
import sys
import xml.etree.ElementTree as ET

from commun import BASE, BRUT, ORGANE_ASSEMBLEE, actes, ecrire_json, lire_json, lire_zip, proximite
from construire import NS, charger_groupes_et_mandats, charger_seances, compte_rendu, groupe_a_la_date

# Le fond du débat ; on laisse de côté articles, amendements, procédure. Les explications de vote (avant un vote solennel)
# disent pourquoi chaque groupe vote pour ou contre.
PARTIES = ("présentation", "discussion générale", "explications de vote")


def texte_de(element):
    return re.sub(r"\s+", " ", "".join(element.itertext())).strip() if element is not None else ""


def interventions(chemin, titre, jour, mandats):
    """Les interventions de fond sur ce texte dans un compte rendu : présentation et discussion générale."""
    sortie, dans_le_texte, partie = [], False, None
    points = [p for p in ET.parse(chemin).getroot().find(f"{NS}contenu") if p.tag == f"{NS}point"]
    intitule_de = lambda p: re.sub(r"\s*\(suite\)\s*$", "", texte_de(p.find(f"{NS}texte")))
    # Seuls les titres qui ressemblent le plus à celui du texte : un texte voisin au titre proche ne doit pas s'y mêler
    scores = [proximite(titre, intitule_de(p)) for p in points if p.get("nivpoint") == "1"]
    seuil = max([0.5] + [x - 0.05 for x in scores])
    for point in points:
        intitule = intitule_de(point)
        if point.get("nivpoint") == "1":
            dans_le_texte = proximite(titre, intitule) >= seuil
            partie = None
            continue
        if not dans_le_texte:
            continue
        if point.get("nivpoint") == "2":
            partie = next((p for p in PARTIES if intitule.lower().startswith(p)), None)
        if not partie:
            continue
        for para in point.iter(f"{NS}paragraphe"):
            orateur = para.find(f"{NS}orateurs/{NS}orateur")
            nom = texte_de(orateur.find(f"{NS}nom")) if orateur is not None else ""
            # La présidence de séance (président ou vice-président) ne débat pas : elle donne la parole
            if para.get("roledebat") == "president" or nom.startswith(("M. le président", "Mme la présidente")) or orateur is None or not para.get("id_acteur"):
                continue
            texte = texte_de(para.find(f"{NS}texte"))
            if len(texte) < 40:
                continue
            acteur = para.get("id_acteur")
            sortie.append({"partie": partie, "acteur": acteur, "nom": nom,
                           "qualite": texte_de(orateur.find(f"{NS}qualite")) or None,
                           "groupe": groupe_a_la_date(mandats, acteur, jour), "texte": texte})
    return sortie


def seances_du_vote(dossier, jour):
    """Séances de la lecture qui s'achève par ce vote : les deux premières (présentation, discussion générale) et celle du vote."""
    dec = next((a for a in actes(dossier) if a["codeActe"].endswith("-DEC") and a.get("organeRef") in ORGANE_ASSEMBLEE.values()
                and (a.get("dateActe") or "")[:10] == jour), None)
    if not dec:
        return []
    code = dec["codeActe"][:-4] + "-SEANCE"
    seances = sorted({(a["dateActe"][:10], a["reunionRef"]) for a in actes(dossier)
                      if a["codeActe"] == code and a.get("reunionRef") and (a.get("dateActe") or "")[:10] <= jour})
    choisies = seances[:2] + [s for s in seances[2:] if s[0] == jour]
    return [ref for _, ref in choisies]


def main():
    if len(sys.argv) < 2:
        sys.exit("Usage : python3 pipeline/debats.py <législature> [DOSSIER ...]")
    leg, voulus = sys.argv[1], set(sys.argv[2:])
    _, mandats = charger_groupes_et_mandats(leg)
    jours = charger_seances(leg)
    compte_rendu_de = {r["uid"]: r.get("compteRenduRef") for liste in jours.values() for r in liste}
    dossiers = {}
    for doc in lire_zip(BRUT / leg / "dossiers.zip", "dossierParlementaire"):
        dossiers[doc["dossierParlementaire"]["uid"]] = doc["dossierParlementaire"]
    sortie = BRUT / leg / "debats"
    sortie.mkdir(parents=True, exist_ok=True)
    faits, vus = 0, set()
    for t in lire_json(BASE / leg / "textes.json"):   # du plus ancien au plus récent : on garde le premier débat d'un texte
        dossier = t.get("dossier") or t["id"]
        if dossier in vus or (voulus and dossier not in voulus):
            continue
        if t["origine"] == "niche":
            refs_seances = [r.get("compteRenduRef") for r in jours.get(t["date"], [])]
        else:   # vote solennel : les séances de la lecture, souvent plusieurs jours avant le vote
            refs_seances = [compte_rendu_de.get(u) for u in seances_du_vote(dossiers.get(dossier, {}), t["date"])]
        liste, refs = [], []
        for ref in refs_seances:
            if not ref:
                continue
            compte_rendu(leg, ref, t["date"])   # télécharge au besoin
            chemin = BRUT / leg / "comptes-rendus" / f"{ref}.xml"
            if not chemin.exists():   # compte rendu pas encore publié par l'Assemblée
                continue
            trouvees = interventions(chemin, t["titre"], t["date"], mandats)
            if trouvees:
                liste += trouvees
                refs.append(ref)
        if liste:
            ecrire_json(sortie / f"{dossier}.json", {"dossier": dossier, "date": t["date"], "comptesRendus": refs, "interventions": liste})
            faits += 1
            vus.add(dossier)
            print(f"{dossier} : {len(liste)} interventions ({', '.join(refs)})")
        else:
            print(f"{dossier} : aucun débat trouvé")
    print(f"{faits} débats extraits dans {sortie}")


if __name__ == "__main__":
    main()
