"""« En mots simples » : une version simple de chaque réplique de « Vivre le débat » (consignes : pipeline/consignes/mots-simples.md).

Usage :
  python3 pipeline/vulgariser.py preparer DOSSIER_DE_SORTIE [TAILLE_DES_LOTS]
      écrit des lots de débats dont une réplique n'a pas encore de version simple (lot-01.json…), pour les agents IA.
  python3 pipeline/vulgariser.py verifier FICHIER_DE_VERSIONS.json [...]
      contrôle les versions produites ({"<dossier>": [{"n", "simple"}]}) et les enregistre dans donnees/redaction/<législature>.json.

Une version n'est gardée que si elle ne nomme personne (anonymat avant le vote), ne commence pas par le rôle (déjà affiché),
n'ajoute pas « je pense que » absent de la citation et fait 80 mots au plus. Le jargon resté sans explication et les phrases
trop longues sont signalés, sans écarter la version.
"""
import json
import re
import sys
from pathlib import Path

from commun import RACINE, ecrire_json, lire_json
from verifier_debats import NOMS_INTERDITS

LEGISLATURES = ("15", "16", "17")
REDACTION = RACINE / "donnees" / "redaction"
GLOSSAIRE = RACINE / "pipeline" / "consignes" / "glossaire.json"
ROLE_EN_TETE = re.compile(r"^\s*(pour|contre|présente le texte|le gouvernement|le rapporteur|la rapporteure)\s*:", re.I)
OPINION = re.compile(r"\b(je pense que|je crois que|selon moi|à mon avis)\b", re.I)
VIDES = set("le la les un une des de du et ou au aux en pour par qui que sur avec sans ce cette ses son sa leur leurs est sont".split())


def termes():
    """(mot difficile, mots de son explication) : un mot est expliqué si deux mots de son explication sont dans la phrase."""
    for cle, val in lire_json(GLOSSAIRE).items():
        if cle.startswith("_"):
            continue
        indices = {m for m in re.findall(r"\w{5,}", val["dire"].lower()) if m not in VIDES}
        for t in re.split(r"\s*/\s*", cle):
            yield t.strip().lower(), indices


def preparer(sortie, taille):
    lots, lot = [], {}
    for leg in LEGISLATURES:
        for dossier, r in lire_json(REDACTION / f"{leg}.json").items():
            reps = (r.get("debat") or {}).get("repliques") or []
            if reps and not all(x.get("simple") for x in reps):
                lot[dossier] = {"titre": r.get("titreClair"), "enClair": r.get("enClair"),
                                "repliques": [{"n": i, "role": x["role"], "qualite": x["orateur"]["qualite"], "citation": x["citation"]}
                                              for i, x in enumerate(reps)]}
                if len(lot) == taille:
                    lots.append(lot); lot = {}
    lots += [lot] if lot else []
    for i, l in enumerate(lots, 1):
        ecrire_json(sortie / f"lot-{i:02}.json", l)
    print(f"{sum(len(l) for l in lots)} débats en {len(lots)} lots dans {sortie}")


def verifier(fichiers):
    redactions = {leg: lire_json(REDACTION / f"{leg}.json") for leg in LEGISLATURES}
    # Un même dossier peut figurer dans plusieurs législatures : on prend celle qui a son débat
    ou = {dossier: leg for leg, red in redactions.items() for dossier, r in red.items() if r.get("debat")}
    liste, gardees, ecartees, signalees = list(termes()), 0, [], []
    for fichier in fichiers:
        for dossier, versions in lire_json(Path(fichier)).items():
            reps = redactions[ou[dossier]][dossier]["debat"]["repliques"] if dossier in ou else []
            for v in versions:
                n, simple = v.get("n"), re.sub(r"\s+", " ", v.get("simple") or "").strip()
                if not isinstance(n, int) or not 0 <= n < len(reps) or not simple:
                    ecartees.append(f"{dossier} n{n} : réplique ou version introuvable"); continue
                r = reps[n]
                nomme = NOMS_INTERDITS.search(simple) if r["role"] != "gouvernement" else None
                pourquoi = (f"nom cité ({nomme.group(0)})" if nomme
                            else "commence par le rôle" if ROLE_EN_TETE.search(simple)
                            else "opinion ajoutée" if OPINION.search(simple) and not OPINION.search(r["citation"])
                            else "trop longue" if len(simple.split()) > 80 else None)
                if pourquoi:
                    r.pop("simple", None)
                    ecartees.append(f"{dossier} n{n} : {pourquoi}"); continue
                r["simple"] = simple
                gardees += 1
                bas = simple.lower()
                jargon = [t for t, indices in liste if re.search(r"\b" + re.escape(t) + r"s?\b", bas) and sum(i in bas for i in indices) < 2]
                longues = [p for p in re.split(r"(?<=[.!?])\s", simple) if len(p.split()) > 30]
                if jargon or longues:
                    signalees.append(f"{dossier} n{n} : " + ", ".join([f"« {t} » sans explication" for t in jargon] + ["phrase de plus de 30 mots"] * bool(longues)))
    for leg, red in redactions.items():
        ecrire_json(REDACTION / f"{leg}.json", red)
    print(f"{gardees} versions gardées, {len(ecartees)} écartées, {len(signalees)} signalées")
    for e in ecartees:
        print("  écartée :", e)
    for s in signalees:
        print("  à revoir :", s)


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "preparer":
        preparer(Path(sys.argv[2]), int(sys.argv[3]) if len(sys.argv) > 3 else 40)
    elif len(sys.argv) >= 3 and sys.argv[1] == "verifier":
        verifier(sys.argv[2:])
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
