"""Mise à jour mensuelle de la législature en cours.

Usage : python3 pipeline/mettre_a_jour.py [17]

1. re-télécharge les fichiers de l'open data (l'Assemblée ne publie que des fichiers complets) ;
2. re-télécharge les comptes rendus des 45 derniers jours (ils peuvent être corrigés après publication) ;
3. reconstruit toute la base, puis les données du site (site/donnees.js) ;
4. compare avec la base précédente et écrit donnees/base/<législature>/nouveautes.md :
   ce qui est nouveau ou a changé, donc ce qui est à vérifier à la main.

Les législatures terminées (15 et 16) n'ont pas besoin de mise à jour.
"""
import datetime
import subprocess
import sys
from pathlib import Path

from commun import BASE, VALIDATION, lire_json

DOSSIER = Path(__file__).resolve().parent
JOURS_A_RAFRAICHIR = 45


def lancer(*arguments):
    subprocess.run([sys.executable, *arguments], cwd=DOSSIER, check=True)


def photo(leg):
    """Ce qu'on compare d'une base à l'autre : les textes, les lignes des programmes de niches, les niches à valider."""
    textes = {t["id"]: t for t in lire_json(BASE / leg / "textes.json", [])}
    lignes = {(n["date"], l["dossier"] or l["titre"]): l for n in lire_json(BASE / leg / "niches.json", []) for l in n["programme"]}
    a_valider = {v["date"]: v for v in lire_json(VALIDATION / f"niches-{leg}.json", []) if v["statut"] == "a_valider"}
    return textes, lignes, a_valider


def etat_texte(t):
    s = t["suite"]
    return (t["statut"], s["derniereEtape"], s["promulgation"], s["conseilConstitutionnel"])


def main():
    leg = sys.argv[1] if len(sys.argv) > 1 else "17"
    avant = photo(leg)
    depuis = (datetime.date.today() - datetime.timedelta(days=JOURS_A_RAFRAICHIR)).isoformat()
    lancer("telecharger.py", leg, "--forcer")
    lancer("construire.py", leg, "--rafraichir-cr", depuis)
    lancer("publier.py")   # le site regroupe toutes les législatures
    apres = photo(leg)

    (textes_av, lignes_av, valider_av), (textes_ap, lignes_ap, valider_ap) = avant, apres
    nouveaux = [t for i, t in textes_ap.items() if i not in textes_av]
    changes = [(textes_av[i], t) for i, t in textes_ap.items() if i in textes_av and etat_texte(textes_av[i]) != etat_texte(t)]
    disparus = [t for i, t in textes_av.items() if i not in textes_ap]
    lignes_changees = [(lignes_av[k], l, k[0]) for k, l in lignes_ap.items() if k in lignes_av and lignes_av[k]["statut"] != l["statut"]]
    niches_nouvelles = [v for d, v in valider_ap.items() if d not in valider_av]

    md = [f"# Mise à jour du {datetime.date.today().isoformat()} ({leg}e législature)", "",
          f"Comptes rendus re-téléchargés à partir du {depuis}.", ""]

    def section(titre, elements):
        md.extend([f"## {titre} ({len(elements)})", ""] + (elements or ["Rien."]) + [""])

    section("Niches détectées, à valider", [f"- {v['date']} : {v['groupe']}" for v in niches_nouvelles])
    section("Nouveaux textes votés (résumé et arguments à rédiger)", [f"- {t['date']} · {t['origine']} · {t['titre'][:100]}" for t in nouveaux])
    section("Textes dont le sort a changé (à relire)",
            [f"- {t['titre'][:90]} : {' / '.join(str(x) for x in etat_texte(a))} → {' / '.join(str(x) for x in etat_texte(t))}"
             + (" — **déjà relu, à revérifier**" if a.get("relu") else "") for a, t in changes])
    section("Statut changé dans un programme de niche", [f"- {d} · {l['titre'][:90]} : {a['statut']} → {l['statut']}" for a, l, d in lignes_changees])
    section("Textes qui ont disparu de la base (anomalie à comprendre)", [f"- {t['date']} · {t['titre'][:100]}" for t in disparus])
    md.append(f"Le reste des points à vérifier est dans [rapport.md](rapport.md). Niches encore à valider au total : {len(valider_ap)}.")
    (BASE / leg / "nouveautes.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(f"\n{len(niches_nouvelles)} niche(s) détectée(s), {len(nouveaux)} nouveau(x) texte(s), {len(changes)} sort(s) changé(s), "
          f"{len(lignes_changees)} statut(s) de niche changé(s), {len(disparus)} disparu(s).")
    print(f"Détail : donnees/base/{leg}/nouveautes.md")


if __name__ == "__main__":
    main()
