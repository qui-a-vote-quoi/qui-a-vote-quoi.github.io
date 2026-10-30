# Qui a voté quoi : le projet

Dernière mise à jour : 30 octobre 2026.

## Objectif

Un site très simple qui répond à trois questions : **quel parti a proposé quelle loi, qui l'a votée, et qu'est-ce que ça change pour moi ?** Le but est de montrer à ceux qui pensent que voter ne sert à rien que leur voix, et le choix du parti, comptent vraiment.

Principe directeur : **simple et efficace**. Les idées qui ajoutent de la complexité vont dans [EN-RESERVE.md](EN-RESERVE.md).

## Décisions prises

| Sujet | Décision |
|---|---|
| Premier pilier : ce que les partis proposent | Les **niches parlementaires** : la journée où un parti choisit seul les textes discutés. |
| Second pilier : ce que les partis votent | Les **votes solennels** : les votes que l'Assemblée désigne elle-même comme majeurs, en conférence des présidents. C'est un critère officiel et neutre, qui remplace notre première idée de sélectionner nous-mêmes « les budgets et grandes réformes ». Il y en a environ 35 par an, soit ~300 sur 2017-2026. |
| Présentation des deux piliers | **Mêmes fiches, mêmes listes, mêmes calculs, sans étiquette dans les listes.** L'auteur et le verdict suffisent. L'origine (niche ou vote solennel) n'apparaît qu'en une phrase sur la fiche du texte, où elle aide à lire le résultat. La page d'une niche reste à part, accessible depuis la fiche du parti : c'est le récit d'une journée. |
| Code et hébergement | Projet **public et open source**, dans une **organisation GitHub** dédiée (GitHub n'autorise qu'un compte gratuit par personne), créée avec le compte personnel dont l'appartenance est masquée. Les commits portent une **identité neutre** (« Qui a voté quoi » et une adresse du projet), jamais l'adresse personnelle. Limite : GitHub affiche publiquement le pseudo du compte qui envoie les modifications. Licences : **AGPL-3.0** pour le code, **Licence Ouverte 2.0** pour les données et les textes (voir le README). |
| Rédaction des résumés et arguments | **Semi-automatique, sans clé d'API** : après chaque récupération des données, un script prépare la liste des textes à rédiger et leurs extraits officiels ; Claude Code rédige les brouillons dans une session ; un humain valide chaque fiche avant publication. Rien n'est publié sans validation manuelle. |
| Statistiques par groupe | **Pas de classement entre groupes** (« qui fait passer le plus de textes », « qui en voit le plus refusés »). Ces chiffres mesurent surtout la place d'un groupe dans le rapport de force (majorité ou opposition), pas son travail : les textes de l'opposition sont rarement adoptés, un dépôt ne coûte qu'une signature, l'influence par amendements n'est pas mesurée, et les périodes ne sont pas comparables (majorité absolue en 2017-2022, aucune depuis 2022). Les chiffres restent visibles sur la fiche de chaque groupe, **toujours avec leur contexte** (opposition ou majorité, nombre de députés). Pour le message « voter compte », on met plutôt en avant **les votes serrés**, qui montrent que le nombre de sièges change ce qui passe. |
| Vocabulaire | On parle de **« groupes »** (groupes politiques de l'Assemblée) et non de « partis » : les députés votent par groupe, et un groupe ne correspond pas toujours à un parti (LIOT réunit plusieurs partis, les non-inscrits n'ont pas de groupe). On parle de **« participation »** aux votes et non de « présence » : un député peut être présent sans voter. On parle de **« textes »** : le mot est juste qu'ils soient adoptés, rejetés ou pas examinés. « Loi » ne désigne que les textes adoptés, « mesure » est flou. Le mot « niche » n'apparaît qu'avec son explication (« journée réservée »). |
| Points ouverts | 1. **Les textes votés à main levée** (surtout en 2017-2022) : les afficher avec leur sort mais sans répartition par groupe, et les exclure de Mon bilan ? 2. **Le statut « renvoyé en commission »** (14 textes en 2017-2022) : nouveau statut à afficher, avec le vote sur la motion. 3. Les textes adoptés **par 49.3, sans vote**. Le seul vote est alors la motion de censure : il y en a eu 11 liées à un 49.3 depuis 2024, dont le budget 2025. À décider : les afficher comme « vote sur le texte » en expliquant le mécanisme. |
| Période | **2017-2026** : les 15ᵉ, 16ᵉ et 17ᵉ législatures, les seules dont l'open data est structuré et complet. |
| Mise à jour | **Une fois par mois, vers le 5 à 10 du mois**, avec `python3 pipeline/mettre_a_jour.py` (détail dans le [README](README.md)). Tout est re-téléchargé et recalculé (environ 20 secondes) ; seul ce qui est nouveau est à valider à la main. |
| Entrées du site | Trois entrées à égalité : **Les groupes**, **Les textes** (tous les textes, filtrables par sujet, auteur, période ou mot ; « Mes sujets » jusqu'au 30/10/2026) et **À vous de voter** (« Mon bilan » jusqu'au 30/10/2026). |
| Mon bilan | « Si vous étiez député, qu'auriez-vous voté ? » : **Pour / Contre / Je ne sais pas**, avec le parti caché jusqu'au résultat. |
| Neutralité | Le site montre les faits, l'utilisateur juge. Les règles sont dans [CHARTE-NEUTRALITE.md](CHARTE-NEUTRALITE.md). |
| Débats « en mots simples » | Retour d'un lecteur adolescent (30/10/2026) : les citations des débats sont utiles mais parfois dures à comprendre. Un **interrupteur au-dessus de chaque débat**, « Citations exactes » (par défaut) / « En mots simples », gardé comme préférence sur l'appareil, pas dans un menu. Versions écrites par IA en trois passes (rédiger, lire comme un élève de 4e, corriger), méthode retenue après trois tours de tests à l'aveugle ; contrôlées par script, **pas relues par un humain**, ce qui est affiché. C'est aussi ce qui justifie l'IA dans ce projet porté par une seule personne : un très grand jeu de données, et un vrai besoin de vulgarisation. |
| Accessibilité | RGAA 4.1 / WCAG 2.1 AA, à vérifier à chaque évolution. Les règles sont dans [ACCESSIBILITE.md](ACCESSIBILITE.md). |
| Architecture | **Site 100 % statique, sans serveur** (voir plus bas). |

## Architecture : un site statique

Aucun serveur n'est nécessaire.

1. **Une chaîne de traitement mensuelle**, sur un ordinateur ou sur un service gratuit comme GitHub Actions :
   - télécharger l'open data de l'Assemblée nationale ;
   - repérer les niches, puis tirer les statuts de chaque texte des comptes rendus officiels ;
   - recalculer les positions des groupes à partir du décompte des voix ;
   - faire rédiger par l'IA les brouillons des résumés « En clair » et des arguments des deux camps.
2. **La rédaction des brouillons avec Claude Code**, sans clé d'API, puis **une relecture humaine** de chaque brouillon, à valider texte par texte avant publication.
3. **La reconstruction du site**, sous forme de fichiers JSON et de pages, puis la publication sur un hébergement gratuit (Vercel ou GitHub Pages).

**Données** : 5 à 10 Mo au total, découpées en petits fichiers JSON (un par niche, un par texte). Chaque page ne charge que ce dont elle a besoin.

**Pourquoi un site statique :**
- hébergement gratuit, rapide, sans maintenance ;
- aucune base de données ni compte utilisateur à protéger ;
- **vie privée** : les réponses à Mon bilan sont des opinions politiques, une donnée sensible au sens du RGPD (article 9). Elles ne quittent jamais l'appareil de l'utilisateur, et on ne collecte rien ;
- transparence : les fichiers de données peuvent être publiés tels quels.

**Limite** : pas de fonctionnalité partagée entre utilisateurs, qui ne figure de toute façon pas dans le projet.

## Données disponibles

| Période | Législature | Open data |
|---|---|---|
| 2024-2026 | 17ᵉ | Complet |
| 2022-2024 | 16ᵉ | Complet |
| 2017-2022 | 15ᵉ | Complet (fichiers suffixés `_XV`) |
| 2012-2017 | 14ᵉ | Partiel, hors périmètre |
| 2009-2012 | 13ᵉ | Absent, hors périmètre |

Pièges connus des données :
- le champ `positionMajoritaire` des scrutins est faux dans environ 3 % des cas, et vaut « pour » quand personne n'a voté. **Il faut toujours recalculer les positions à partir du décompte des voix ;**
- l'open data n'a pas de marqueur « niche » : il faut repérer les journées, puis valider la liste à la main ;
- les étapes des dossiers ne disent pas si un texte a vraiment été discuté. **Les statuts viennent des comptes rendus de séance** (adopté, rejeté, retiré, commencé sans vote, pas examiné) ;
- un texte dont l'article unique est supprimé est affiché comme « rejeté », avec la précision sur sa fiche. En 2022-2024, c'est souvent chaque article qui est supprimé un à un : on retient alors le vote sur le premier article, lui aussi inversé ;
- d'une législature à l'autre, l'identifiant de l'Assemblée et les sigles des groupes changent (MODEM → DEM, NG → SOC, quatre sigles successifs pour l'UDI) : la chaîne les regroupe ;
- un texte peut aussi être écarté par une **motion de procédure** : la motion de rejet préalable (ou, pour une proposition de résolution, les conclusions de rejet de la commission) le rejette sans examiner ses articles, la motion de renvoi en commission arrête la discussion. Le vote sur la motion est retenu, inversé. Fréquent en 2017-2022 ;
- en 2017-2022, beaucoup de textes ont été adoptés ou rejetés **à main levée**, sans scrutin public : le vote de chaque groupe n'existe alors pas dans les données (51 cas sur 295 textes de niches) ;
- la position officielle des groupes (opposition, minoritaire, majoritaire) est fournie pour 2017-2024, mais pas encore pour 2024-2026 : à saisir à la main pour la 17ᵉ législature.

## Ampleur estimée (2017-2026)

| Élément | Estimation |
|---|---|
| Niches | ~90 |
| Textes au programme | ~600, dont ~250 votés jusqu'au bout |
| Votes solennels | ~300 |
| Données brutes | ~350 Mo compressés |
| Base finale | 20 à 50 Mo |

**Temps**
- Développement : **4 à 6 semaines.**
- Relecture humaine : **150 à 200 heures** pour les niches, plus **60 à 80 heures** pour les votes solennels, dont ~15 h pour les niches, ~50 h pour les résumés, ~60 h pour les arguments, ~20 h pour les budgets et ~20 h pour les vérifications de neutralité et d'accessibilité.
- Entretien : **3 à 4 heures par mois.**

**Coût de l'IA (effort medium)**

Volume pour les niches : ~26,5 M tokens lus et ~4 M tokens écrits. Les votes solennels ajoutent quelques dizaines de dollars.

| Modèle | Tarif (par M de tokens) | Prix standard | En traitement par lots (-50 %) | Avec une 2ᵉ passe de contrôle |
|---|---|---|---|---|
| Claude Sonnet 5.5 | 2 $ entrée / 10 $ sortie | ~94 $ | **~47 $** | ~61 $ |
| Claude Opus 5.5 | 4 $ entrée / 20 $ sortie | ~188 $ | **~94 $** | ~122 $ |

Coût mensuel ensuite : **1 à 2 $.** Ces chiffres sont à confirmer par un essai sur 10 textes, qui coûterait 2 à 5 $.

## Prochaines étapes

1. ~~Mettre le projet sous Git.~~ Fait. Organisation GitHub `qui-a-vote-quoi` créée (appartenance du propriétaire masquée). Les commits portent l'identité neutre « Qui a voté quoi <contact@qui-a-vote-quoi.invalid> », reliée à aucun compte.
2. ~~Chaîne de données pour 2024-2026 (phase 1).~~ Première version faite : `pipeline/`, base dans `donnees/base/17/`, rapport de vérification dans `donnees/base/17/rapport.md`.
3. ~~Commande de mise à jour mensuelle.~~ Faite : `pipeline/mettre_a_jour.py`, qui écrit la liste des nouveautés à vérifier.
4. ~~Étendre la chaîne à 2022-2024 puis 2017-2022.~~ Fait : bases dans `donnees/base/16/` et `donnees/base/15/`, avec leurs rapports.
5. Valider à la main les niches détectées (14 pour 2024-2026, 21 pour 2022-2024, 45 pour 2017-2022, dans `donnees/validation/`) et les points listés dans chaque rapport. Les jours attribués au groupe majoritaire (LAREM, RE) sont probablement de faux positifs : la Constitution réserve ces journées à l'opposition et aux groupes minoritaires.
6. ~~Version de test sur les vraies données.~~ Faite pour 2017-2026 : `site/`, produit par `pipeline/publier.py`. Contenu publié au maximum, avec son niveau affiché (voir CHARTE-NEUTRALITE.md) : niches vérifiées par IA dans les comptes rendus (83 publiées, 7 niches manquées retrouvées, 7 faux positifs écartés, 3 à valider), 453 textes dont 425 résumés rédigés par IA à partir des textes officiels (`pipeline/extraits.py`), 28 « à venir ». Reste : relire en priorité les résumés portant une `remarque`, un moyen de recueillir l'avis des testeurs, puis la tester sur 2 ou 3 personnes qui ne votent pas.
7. Phase 2 : brouillons des résumés et arguments avec Claude Code, puis relecture.
8. Phase 3 : brancher le site sur la base JSON, puis publier.

## Fichiers du projet

- [maquette/](maquette/) : la maquette cliquable (`index.html`, `data.js`), servie en local sur le port 8737.
- [CHARTE-NEUTRALITE.md](CHARTE-NEUTRALITE.md) : les règles de neutralité.
- [ACCESSIBILITE.md](ACCESSIBILITE.md) : les règles d'accessibilité.
- [EN-RESERVE.md](EN-RESERVE.md) : les idées mises de côté.
