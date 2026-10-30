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

Première construction d'une législature (15 pour 2017-2022, 16 pour 2022-2024, 17 pour 2024-2026) :

```bash
python3 pipeline/telecharger.py 17
python3 pipeline/construire.py 17
```

Le premier passage télécharge aussi les comptes rendus des séances utiles (une dizaine de minutes). Ils restent en cache dans `donnees/brut/`, et une reconstruction prend ensuite quelques secondes.

## Mise à jour mensuelle

Une seule commande, vers le 5 à 10 de chaque mois (le temps que l'Assemblée publie les comptes rendus des dernières séances) :

```bash
python3 pipeline/mettre_a_jour.py
```

Elle :
1. re-télécharge les fichiers de l'open data : l'Assemblée ne publie que des fichiers complets (~60 Mo), pas les seules modifications ;
2. re-télécharge les comptes rendus des 45 derniers jours, qui peuvent être corrigés après publication ;
3. reconstruit toute la base. On recalcule tout plutôt que de compléter : un texte peut changer de sort des mois plus tard (adopté au Sénat, promulgué, censuré), et le recalcul le prend en compte ;
4. compare avec la base précédente et écrit `donnees/base/17/nouveautes.md` : niches détectées, nouveaux textes votés, textes dont le sort a changé, statuts changés dans un programme de niche.

Les vérifications faites à la main, dans `donnees/validation/`, ne sont jamais refaites : seuls les nouveaux cas sont à valider. Un compte rendu pas encore publié est signalé dans `rapport.md` et repris à la mise à jour suivante. Les législatures terminées (15ᵉ et 16ᵉ) se construisent une fois pour toutes.

En été (fin de la session ordinaire en juin), il y a peu ou pas de séances : la mise à jour d'août peut être sautée.

## Source des données

Open data de l'Assemblée nationale : https://data.assemblee-nationale.fr (Licence Ouverte Etalab).

## Licences

- **Le code** (chaîne de traitement, site) : [AGPL-3.0](LICENSE). Toute version modifiée mise en ligne doit publier son code : une copie du site ne peut pas changer discrètement les calculs ou la présentation des votes.
- **Les données et les textes** (base JSON, résumés, arguments) : [Licence Ouverte 2.0](LICENCE-DONNEES.md), la licence des données de l'Assemblée. Réutilisation libre, en citant la source.
