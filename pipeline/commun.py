"""Outils partagés par la chaîne de traitement : chemins, téléchargement, lecture des fichiers de l'open data."""
import json
import re
import shutil
import subprocess
import time
import unicodedata
import urllib.request
import zipfile
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
BRUT = RACINE / "donnees" / "brut"
BASE = RACINE / "donnees" / "base"
VALIDATION = RACINE / "donnees" / "validation"

OPEN_DATA = "https://data.assemblee-nationale.fr/static/openData/repository"
SITE_AN = "https://www.assemblee-nationale.fr/dyn/opendata"
# L'Assemblée nationale a un identifiant différent à chaque législature
ORGANE_ASSEMBLEE = {"15": "PO717460", "16": "PO791932", "17": "PO838901"}
ORGANE_SENAT = "PO78718"

# Fichiers de l'open data par législature. La 15e utilise des noms suffixés « _XV ».
# Le fichier des députés et des groupes est un historique commun à toutes les législatures.
ACTEURS = "17/amo/tous_acteurs_mandats_organes_xi_legislature/AMO30_tous_acteurs_tous_mandats_tous_organes_historique.json.zip"
SOURCES = {
    "17": {
        "scrutins": "17/loi/scrutins/Scrutins.json.zip",
        "dossiers": "17/loi/dossiers_legislatifs/Dossiers_Legislatifs.json.zip",
        "agenda": "17/vp/reunions/Agenda.json.zip",
        "acteurs": ACTEURS,
    },
    "16": {
        "scrutins": "16/loi/scrutins/Scrutins.json.zip",
        "dossiers": "16/loi/dossiers_legislatifs/Dossiers_Legislatifs.json.zip",
        "agenda": "16/vp/reunions/Agenda.json.zip",
        "acteurs": ACTEURS,
    },
    "15": {
        "scrutins": "15/loi/scrutins/Scrutins_XV.json.zip",
        "dossiers": "15/loi/dossiers_legislatifs/Dossiers_Legislatifs_XV.json.zip",
        "agenda": "15/vp/reunions/Agenda_XV.json.zip",
        "acteurs": ACTEURS,
    },
}


def telecharger(url, destination, essais=3):
    """Télécharge un fichier, avec quelques nouvelles tentatives en cas d'erreur réseau.

    curl est utilisé s'il est disponible : il est nettement plus rapide que urllib sur les gros fichiers.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    if shutil.which("curl"):
        partiel = destination.with_suffix(destination.suffix + ".partiel")
        try:
            subprocess.run(["curl", "-sSfL", "--retry", str(essais), "-A", "qui-a-vote-quoi (open data)", "-o", str(partiel), url], check=True)
        except subprocess.CalledProcessError:
            partiel.unlink(missing_ok=True)
            raise
        partiel.replace(destination)
        return destination
    for essai in range(essais):
        try:
            requete = urllib.request.Request(url, headers={"User-Agent": "qui-a-vote-quoi (open data)"})
            with urllib.request.urlopen(requete, timeout=120) as reponse, open(destination, "wb") as sortie:
                while True:
                    bloc = reponse.read(1 << 20)
                    if not bloc:
                        break
                    sortie.write(bloc)
            return destination
        except OSError:
            if essai == essais - 1:
                raise
            time.sleep(3 * (essai + 1))


def lire_zip(chemin, sous_dossier):
    """Parcourt les fichiers JSON d'une archive dont le chemin contient `sous_dossier`."""
    with zipfile.ZipFile(chemin) as archive:
        for nom in archive.namelist():
            if nom.endswith(".json") and f"/{sous_dossier}/" in f"/{nom}":
                with archive.open(nom) as f:
                    yield json.load(f)


def en_liste(valeur):
    """L'open data met un objet seul là où il y en a un, une liste quand il y en a plusieurs."""
    if valeur is None:
        return []
    return valeur if isinstance(valeur, list) else [valeur]


def actes(dossier):
    """Toutes les étapes (actes législatifs) d'un dossier, à plat."""
    resultat = []

    def parcourir(noeud):
        for acte in en_liste(((noeud or {}).get("actesLegislatifs") or {}).get("acteLegislatif")):
            resultat.append(acte)
            parcourir(acte)

    parcourir(dossier)
    return resultat


def normaliser(texte):
    """Minuscules, sans accents ni ponctuation : pour comparer des titres écrits différemment."""
    texte = unicodedata.normalize("NFKD", texte.lower().replace("’", "'"))
    texte = texte.encode("ascii", "ignore").decode()
    return re.sub(r"\W+", " ", texte).strip()


MOTS_VIDES = set("de la le les des du d l a au aux en et un une pour par sur visant vise a relative relatif proposition loi projet resolution ".split())


def mots(texte):
    return {m for m in normaliser(texte).split() if m not in MOTS_VIDES and len(m) > 2}


def proximite(a, b):
    """Part des mots significatifs en commun entre deux titres (0 à 1)."""
    ma, mb = mots(a), mots(b)
    if not ma or not mb:
        return 0.0
    return len(ma & mb) / min(len(ma), len(mb))


def ecrire_json(chemin, donnees):
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(donnees, f, ensure_ascii=False, indent=1)
        f.write("\n")


def lire_json(chemin, defaut=None):
    if not chemin.exists():
        return defaut
    with open(chemin, encoding="utf-8") as f:
        return json.load(f)
