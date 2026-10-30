"""Télécharge les fichiers de l'open data de l'Assemblée nationale pour une législature.

Usage : python3 pipeline/telecharger.py 17 [--forcer]

Sans --forcer, un fichier déjà présent n'est pas re-téléchargé. Les comptes rendus de séance,
nécessaires aux statuts des textes, sont téléchargés au besoin par construire.py.
"""
import sys

from commun import BRUT, OPEN_DATA, SOURCES, telecharger


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in SOURCES:
        sys.exit(f"Usage : python3 pipeline/telecharger.py <législature> [--forcer]  (disponibles : {', '.join(SOURCES)})")
    legislature, forcer = sys.argv[1], "--forcer" in sys.argv
    for nom, chemin in SOURCES[legislature].items():
        destination = BRUT / legislature / f"{nom}.zip"
        if destination.exists() and not forcer:
            print(f"{nom} : déjà présent ({destination.stat().st_size // 1_000_000} Mo)")
            continue
        print(f"{nom} : téléchargement…", flush=True)
        telecharger(f"{OPEN_DATA}/{chemin}", destination)
        print(f"{nom} : {destination.stat().st_size // 1_000_000} Mo")


if __name__ == "__main__":
    main()
