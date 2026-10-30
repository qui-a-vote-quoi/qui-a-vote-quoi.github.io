# Qui a voté quoi

Un site simple et neutre qui montre, pour chaque texte examiné à l'Assemblée nationale, qui l'a proposé, ce qu'il change, et ce que chaque groupe de députés a voté. Période couverte : 2017-2026.

- [PROJET.md](PROJET.md) : objectif, décisions, architecture et feuille de route.
- [CHARTE-NEUTRALITE.md](CHARTE-NEUTRALITE.md) : les règles de neutralité.
- [ACCESSIBILITE.md](ACCESSIBILITE.md) : les règles d'accessibilité.
- [EN-RESERVE.md](EN-RESERVE.md) : les idées mises de côté.

## Organisation

| Dossier | Contenu |
|---|---|
| `site/` | Le site publié (version de test) : une page, ses données (`donnees.js`, produit par la chaîne) et ses polices. |
| `maquette/` | La maquette cliquable d'origine (données recopiées à la main), gardée pour mémoire. |
| `pipeline/` | La chaîne de traitement : téléchargement de l'open data, puis construction de la base. |
| `donnees/brut/` | Les fichiers bruts de l'open data (non versionnés, re-téléchargeables). |
| `donnees/base/` | La base JSON produite par la chaîne de traitement. |
| `donnees/validation/` | Les vérifications faites à la main (par exemple la liste des niches validées). |
| `donnees/redaction/` | Ce qui est rédigé pour chaque texte : sujet, titre clair, résumé « en clair », qui est concerné, arguments, avec leur niveau (à venir, rédigé par IA, relu). Voir CHARTE-NEUTRALITE.md. |

## Lancer la chaîne de traitement

Python 3.9 ou plus récent, sans dépendance externe.

Première construction d'une législature (15 pour 2017-2022, 16 pour 2022-2024, 17 pour 2024-2026) :

```bash
python3 pipeline/telecharger.py 17
python3 pipeline/construire.py 17
```

Le premier passage télécharge aussi les comptes rendus des séances utiles (une dizaine de minutes). Ils restent en cache dans `donnees/brut/`, et une reconstruction prend ensuite quelques secondes.

## Le site

```bash
python3 pipeline/publier.py
```

Produit `site/donnees.js` à partir de la base et des rédactions, pour les trois législatures. Sont publiés les votes solennels et les niches vérifiées (par IA ou par un humain). Chaque résumé affiche son niveau : à venir, rédigé par IA et non vérifié, ou relu par un humain. Mon bilan ne propose que les textes résumés.

Pour rédiger les brouillons de résumés, `python3 pipeline/extraits.py 17` prépare un extrait du texte officiel de chaque dossier (dans `donnees/brut/`, non versionné).

Pour « Vivre le débat » : `python3 pipeline/debats.py 17` extrait des comptes rendus la présentation et la discussion générale de chaque texte (orateur, qualité, groupe, texte exact). Les répliques choisies par IA sont ensuite contrôlées et enregistrées par `python3 pipeline/verifier_debats.py 17 <fichier de répliques>` : citation mot pour mot, aucun nom avant le vote, autant de répliques de chaque camp.

Pour voir le site en local : `python3 -m http.server 8738 --directory site`, puis http://localhost:8738.

Le site est publié sur GitHub Pages par `.github/workflows/site.yml` à chaque modification de `site/` poussée sur `main`.

## Mise à jour mensuelle

Une seule commande, vers le 5 à 10 de chaque mois (le temps que l'Assemblée publie les comptes rendus des dernières séances) :

```bash
python3 pipeline/mettre_a_jour.py
```

Elle :
1. re-télécharge les fichiers de l'open data : l'Assemblée ne publie que des fichiers complets (~60 Mo), pas les seules modifications ;
2. re-télécharge les comptes rendus des 45 derniers jours, qui peuvent être corrigés après publication ;
3. reconstruit toute la base, puis les données du site. On recalcule tout plutôt que de compléter : un texte peut changer de sort des mois plus tard (adopté au Sénat, promulgué, censuré), et le recalcul le prend en compte ;
4. compare avec la base précédente et écrit `donnees/base/17/nouveautes.md` : niches détectées, nouveaux textes votés, textes dont le sort a changé, statuts changés dans un programme de niche.

Les vérifications faites à la main, dans `donnees/validation/`, ne sont jamais refaites : seuls les nouveaux cas sont à valider. Un compte rendu pas encore publié est signalé dans `rapport.md` et repris à la mise à jour suivante. Les législatures terminées (15ᵉ et 16ᵉ) se construisent une fois pour toutes.

En été (fin de la session ordinaire en juin), il y a peu ou pas de séances : la mise à jour d'août peut être sautée.

## Source des données

Open data de l'Assemblée nationale : https://data.assemblee-nationale.fr (Licence Ouverte Etalab).

## Où sont les données, et combien de temps

| Quoi | Où | Sauvegardé ? | Si on le perd |
|---|---|---|---|
| **Fichiers bruts** de l'Assemblée (votes, dossiers, agenda, députés), comptes rendus, textes officiels, extraits, débats (`donnees/brut/`, ~850 Mo) | Seulement sur l'ordinateur qui fait tourner la chaîne. Non versionnés (`.gitignore`). | Non | On les re-télécharge : `telecharger.py`, puis `construire.py`, `extraits.py` et `debats.py` les retrouvent (quelques heures pour tout, à cause des comptes rendus). Les archives des législatures passées restent publiées par l'Assemblée. |
| **Base** produite par la chaîne (`donnees/base/`) | Git, et le dépôt public sur GitHub | Oui | On la reconstruit à partir des fichiers bruts. |
| **Travail de vérification et de rédaction** : niches vérifiées et leurs corrections (`donnees/validation/`, avec les rapports détaillés dans `verifications/`), résumés, sujets, classements, débats retenus (`donnees/redaction/`) | Git, et le dépôt public sur GitHub | Oui | C'est la seule partie qui ne se refait pas automatiquement : à ne jamais perdre. Garder une copie du dépôt ailleurs (un second ordinateur, un disque) en plus de GitHub. |
| **Site publié** (`site/`) | Git, GitHub, et GitHub Pages pour la mise en ligne | Oui | On le republie avec `publier.py` puis un `git push`. |
| **Brouillons des sous-agents IA** (lots, brouillons, rapports bruts) | Dossier temporaire de la session de travail | Non, effacé à la fin de la session | Rien à perdre : tout ce qui compte est recopié dans `donnees/redaction/` et `donnees/validation/` au moment de l'intégration. |
| **Votes des visiteurs** dans « À vous de voter » | Dans le navigateur du visiteur (stockage local), jamais envoyés | Non | Ils restent tant que le visiteur ne les efface pas. Certains navigateurs les suppriment d'eux-mêmes : Safari après 7 jours sans visite du site, et la navigation privée à la fermeture. |

**Le cache des navigateurs** : la page charge `donnees.js?v=<empreinte>`. L'empreinte change quand les données changent, ce qui oblige les navigateurs à recharger les nouvelles données après chaque mise à jour, au lieu de garder l'ancienne version en mémoire. GitHub Pages garde aussi une copie quelques minutes : une nouvelle publication peut mettre jusqu'à 10 minutes à apparaître partout.

## Licences

- **Le code** (chaîne de traitement, site) : [AGPL-3.0](LICENSE). Toute version modifiée mise en ligne doit publier son code : une copie du site ne peut pas changer discrètement les calculs ou la présentation des votes.
- **Les données et les textes** (base JSON, résumés, arguments) : [Licence Ouverte 2.0](LICENCE-DONNEES.md), la licence des données de l'Assemblée. Réutilisation libre, en citant la source.
