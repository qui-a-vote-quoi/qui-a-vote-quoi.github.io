"""Vérifie les répliques choisies pour « Vivre le débat » et les enregistre dans donnees/redaction/<législature>.json.

Usage : python3 pipeline/verifier_debats.py 17 FICHIER_REPLIQUES.json [...]

Chaque fichier de répliques (produit par IA) associe à un dossier une liste {n, role, citation}, où n renvoie à une
intervention de donnees/brut/<législature>/debats/<dossier>.json. Une réplique n'est gardée que si :
- sa citation figure mot pour mot dans le texte de cette intervention (aucune phrase inventée ou reformulée) ;
- les répliques « pour » et « contre » restent en nombre égal (sinon le débat entier est écarté).
Le nom, la qualité et le groupe de l'orateur viennent du compte rendu, jamais de l'IA.
"""
import re
import sys
from pathlib import Path

from commun import BRUT, RACINE, ecrire_json, lire_json

ROLES = ("presentation", "gouvernement", "pour", "contre")
# Anonymat avant le vote : une citation qui nomme une personne, un parti ou un groupe est écartée
NOMS_INTERDITS = re.compile(
    r"\b(?:M\.|Mme|Monsieur|Madame)\s+[A-ZÉÈ][\w’'-]+|insoumis|Rassemblement national|\bRN\b|macronist|Renaissance|Ensemble pour la République|"
    r"Les Républicains|Droite républicaine|socialistes?\b|écologistes?\b|communistes?\b|Horizons|MoDem|Démocrates|\bLIOT\b|\bUDR\b|\bLFI\b|NUPES|"
    r"Nouveau Front populaire|ciottistes?|lepénistes?", re.I)


def normal(texte):
    return re.sub(r"\s+", " ", texte.replace("’", "'").replace(" ", " ")).strip()


def seance(leg, ref):
    """Un compte rendu, avec la date et le numéro de sa séance dans la journée (« 2e séance du 13 octobre »)."""
    xml = (BRUT / leg / "comptes-rendus" / f"{ref}.xml").read_text(encoding="utf-8")
    date = re.search(r"<dateSeance>(\d{4})(\d{2})(\d{2})", xml).groups()
    return {"ref": ref, "date": "-".join(date), "numJour": int(re.search(r"<numSeanceJour>(\d*)", xml).group(1) or 1)}   # « Unique » : seule séance du jour


def main():
    if len(sys.argv) < 3:
        sys.exit("Usage : python3 pipeline/verifier_debats.py <législature> FICHIER_REPLIQUES.json [...]")
    leg = sys.argv[1]
    chemin_redaction = RACINE / "donnees" / "redaction" / f"{leg}.json"
    redaction = lire_json(chemin_redaction, {})
    for fichier in sys.argv[2:]:
        for dossier, choix in lire_json(Path(fichier)).items():
            debat = lire_json(BRUT / leg / "debats" / f"{dossier}.json")
            if not debat or not choix.get("repliques"):
                print(f"{dossier} : pas de répliques ({choix.get('remarque') or 'débat introuvable'})")
                continue
            gardees, rejetees = [], []
            simples = {normal(r["citation"]): r["simple"] for r in (redaction.get(dossier, {}).get("debat") or {}).get("repliques", []) if r.get("simple")}
            for r in choix["repliques"]:
                n = r.get("n")
                ok = r.get("role") in ROLES and isinstance(n, int) and 0 <= n < len(debat["interventions"])
                inter = debat["interventions"][n] if ok else None
                nomme = NOMS_INTERDITS.search(r.get("citation", ""))
                if nomme and r.get("role") in ("pour", "contre", "presentation"):
                    rejetees.append(f"nom cité ({nomme.group(0)}) : " + r.get("citation", "")[:40]); continue
                if ok and normal(r["citation"]) and normal(r["citation"]) in normal(inter["texte"]):
                    gardees.append({"role": r["role"], "citation": r["citation"].strip(), "partie": inter["partie"],
                                    "orateur": {"nom": inter["nom"], "qualite": inter["qualite"], "groupe": inter["groupe"]}})
                    if normal(r["citation"]) in simples:   # même citation qu'avant : sa version en mots simples reste valable
                        gardees[-1]["simple"] = simples[normal(r["citation"])]
                else:
                    rejetees.append(r.get("citation", "")[:60])
            # Une citation écartée d'un côté : on retire la dernière réplique de l'autre côté, pour garder l'égalité
            while abs(sum(r["role"] == "pour" for r in gardees) - sum(r["role"] == "contre" for r in gardees)) > 0:
                trop = "pour" if sum(r["role"] == "pour" for r in gardees) > sum(r["role"] == "contre" for r in gardees) else "contre"
                gardees.remove([r for r in gardees if r["role"] == trop][-1])
            pour = sum(r["role"] == "pour" for r in gardees)
            contre = sum(r["role"] == "contre" for r in gardees)
            # Texte consensuel : personne ne s'y oppose sur le fond ; on garde la présentation (et le gouvernement), sans camp inventé
            consensuel = bool(choix.get("consensuel")) and not pour and any(r["role"] == "presentation" for r in gardees)
            if consensuel:
                gardees = [r for r in gardees if r["role"] in ("presentation", "gouvernement")]
            elif not pour:
                print(f"{dossier} : écarté, plus aucune réplique d'un des deux camps ({len(rejetees)} citation(s) introuvable(s))")
                redaction.get(dossier, {}).pop("debat", None)
                continue
            redaction.setdefault(dossier, {})["debat"] = {
                "date": debat["date"], "comptesRendus": [seance(leg, ref) for ref in debat["comptesRendus"]], "repliques": gardees,
                "niveau": "ia",   # choisi par IA, citations vérifiées mot pour mot, pas encore relu
                **({"consensuel": True} if consensuel else {}),
            }
            print(f"{dossier} : {len(gardees)} répliques gardées{' (consensuel)' if consensuel else ''}" + (f", {len(rejetees)} écartée(s) (citation introuvable)" if rejetees else ""))
    ecrire_json(chemin_redaction, dict(sorted(redaction.items())))


if __name__ == "__main__":
    main()
