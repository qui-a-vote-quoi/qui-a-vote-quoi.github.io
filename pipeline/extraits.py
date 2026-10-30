"""Prépare, pour chaque texte de la base, un extrait du texte officiel déposé (exposé des motifs et articles).

Usage : python3 pipeline/extraits.py 17

Ces extraits servent à rédiger les brouillons de résumés « en clair » (voir CHARTE-NEUTRALITE.md) :
on résume à partir du texte officiel, pas de mémoire. Ils sont écrits dans donnees/brut/<législature>/extraits/
(non versionné), un fichier texte par dossier.
"""
import html
import re
import subprocess
import sys

from commun import BASE, BRUT, SITE_AN, actes, lire_json, lire_zip, telecharger

TAILLE_MAX = 15000   # caractères gardés par extrait : assez pour l'exposé des motifs et les premiers articles


def documents_deposes(legislature):
    """Pour chaque dossier : l'identifiant du premier texte déposé à l'Assemblée (proposition ou projet de loi).

    Un texte venu du Sénat est d'abord déposé au Sénat, dont l'Assemblée ne publie pas les documents :
    on prend alors le texte transmis à l'Assemblée."""
    depots = {}
    for doc in lire_zip(BRUT / legislature / "dossiers.zip", "dossierParlementaire"):
        d = doc["dossierParlementaire"]
        candidats = sorted((a.get("dateActe") or "9999", a["texteAssocie"]) for a in actes(d)
                           if a["codeActe"].endswith("DEPOT") and "ANR5" in (a.get("texteAssocie") or ""))
        if candidats:
            depots[d["uid"]] = candidats[0][1]
    return depots


def texte_brut(page):
    page = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", page)
    page = re.sub(r"(?i)<(br|/p|/div|/h\d|/li)[^>]*>", "\n", page)
    texte = html.unescape(re.sub(r"<[^>]+>", " ", page))
    texte = re.sub(r"[ \t\xa0]+", " ", texte)
    return re.sub(r"\n\s*\n+", "\n\n", texte).strip()


def main():
    if len(sys.argv) < 2:
        sys.exit("Usage : python3 pipeline/extraits.py <législature>")
    leg = sys.argv[1]
    dossiers = sorted({t.get("dossier") or t["id"] for t in lire_json(BASE / leg / "textes.json")})
    depots = documents_deposes(leg)
    sortie, pages = BRUT / leg / "extraits", BRUT / leg / "textes-officiels"
    sortie.mkdir(parents=True, exist_ok=True)
    manquants = []
    for i, uid in enumerate(dossiers, 1):
        doc = depots.get(uid)
        if not doc:   # dossier ouvert sous une législature précédente : on cherche dans ses fichiers
            for autre in ("16", "15"):
                if autre != leg and (BRUT / autre / "dossiers.zip").exists() and f"L{autre}N" in uid:
                    doc = documents_deposes(autre).get(uid)
        if not doc:
            manquants.append(uid)
            continue
        page = pages / f"{doc}.html"
        if not page.exists():
            try:
                telecharger(f"{SITE_AN}/{doc}.html", page)
            except (OSError, subprocess.CalledProcessError):
                manquants.append(uid)
                continue
        texte = texte_brut(page.read_text(encoding="utf-8", errors="ignore"))
        (sortie / f"{uid}.txt").write_text(f"Dossier {uid}, texte déposé {doc}\n\n{texte[:TAILLE_MAX]}\n", encoding="utf-8")
        if i % 25 == 0:
            print(f"{i} / {len(dossiers)}", flush=True)
    print(f"{len(dossiers) - len(manquants)} extraits dans {sortie} ; sans texte trouvé : {', '.join(manquants) or 'aucun'}")


if __name__ == "__main__":
    main()
