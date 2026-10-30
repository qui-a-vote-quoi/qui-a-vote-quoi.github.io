# Qui a voté quoi

Un site simple et neutre qui montre, pour chaque texte examiné à l'Assemblée nationale, qui l'a proposé, ce qu'il change, et ce que chaque groupe de députés a voté. Période couverte : 2017-2026.

- [PROJET.md](PROJET.md) : objectif, décisions, architecture et feuille de route.
- [CHARTE-NEUTRALITE.md](CHARTE-NEUTRALITE.md) : les règles de neutralité.
- [ACCESSIBILITE.md](ACCESSIBILITE.md) : les règles d'accessibilité.
- [EN-RESERVE.md](EN-RESERVE.md) : les idées mises de côté.

## Organisation

| Dossier | Contenu |
|---|---|
| `maquette/` | La maquette cliquable (données recopiées à la main). |
| `pipeline/` | La chaîne de traitement : téléchargement de l'open data, puis construction de la base. |
| `donnees/brut/` | Les fichiers bruts de l'open data (non versionnés, re-téléchargeables). |
| `donnees/base/` | La base JSON produite par la chaîne de traitement. |
| `donnees/validation/` | Les vérifications faites à la main (par exemple la liste des niches validées). |

## Lancer la chaîne de traitement

Python 3.9 ou plus récent, sans dépendance externe.

```bash
python3 pipeline/telecharger.py 17
python3 pipeline/construire.py 17
```

## Source des données

Open data de l'Assemblée nationale : https://data.assemblee-nationale.fr (licence ouverte Etalab).
