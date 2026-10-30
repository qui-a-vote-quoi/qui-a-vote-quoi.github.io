# Grille : ce que fait un texte

Cette grille décrit **le mécanisme juridique** qu'utilise un texte, tel qu'on le lit dans ses articles. Elle ne dit pas si le texte est bon ou mauvais : chaque lecteur en juge selon ses propres valeurs (voir [CHARTE-NEUTRALITE.md](CHARTE-NEUTRALITE.md)).

Elle remplace l'idée d'un critère de « bienveillance », écartée le 30/10/2026 parce qu'elle reposait sur un jugement de valeur : une même mesure peut être vue comme protectrice par les uns et punitive par les autres.

## Règles

1. **On lit les articles, pas l'exposé des motifs.** On classe ce que le texte change dans le droit, pas ce que ses auteurs disent vouloir faire.
2. **Un à trois mécanismes par texte**, du plus important au moins important. Beaucoup de textes combinent une aide et une sanction, ou une obligation et une aide.
3. **Chaque mécanisme a son contraire** (créer / alléger), pour que la grille voie aussi ce qui se retire ou se simplifie.
4. **On décrit l'effet direct, pas les effets supposés.** Une hausse d'impôt reste une hausse d'impôt, même si elle finance une aide.
5. **En cas de doute entre deux catégories**, on garde les deux. Si le texte est trop flou pour être classé (extrait illisible), on ne le classe pas.

## Les catégories

| Code | Libellé affiché | Définition | Exemples |
|---|---|---|---|
| `aide_plus` | Crée ou étend une aide, un droit ou une prise en charge | Prestation, remboursement, allocation, droit nouveau, accès élargi à un service, revalorisation | Soins remboursés à 100 % après des violences sexuelles ; allocations familiales dès le premier enfant ; repas à 1 € pour tous les étudiants |
| `aide_moins` | Réduit ou supprime une aide ou un droit | Baisse, suppression ou conditions plus strictes pour une prestation ou un droit existant | Report de l'âge de départ à la retraite ; suspension d'allocations ; conditions plus strictes pour une aide |
| `sanction_plus` | Crée ou aggrave une sanction | Nouveau délit ou nouvelle contravention, amende, peine plus lourde, peine minimale, déchéance, expulsion facilitée | Amende pour séjour irrégulier ; peines minimales ; pénalisation des rave-parties |
| `sanction_moins` | Supprime ou allège une sanction | Dépénalisation, abrogation d'un délit, peine réduite, amnistie | Suppression d'un délit ; allègement de peine |
| `contrainte_plus` | Crée une obligation, une interdiction ou un contrôle | Règle nouvelle imposée à des personnes, entreprises ou administrations, hors sanction pénale : obligation d'informer, interdiction d'un produit ou d'une pratique, encadrement, autorisation préalable | Étiquetage obligatoire de l'origine des aliments ; interdiction des sucres ajoutés pour les nourrissons ; encadrement des loyers |
| `contrainte_moins` | Lève une obligation, une interdiction ou un contrôle | Simplification, suppression d'une règle, d'une autorisation ou d'un contrôle, dérogation | Simplification de l'urbanisme ; levée d'une interdiction d'exploitation ; suppression de démarches |
| `impot_plus` | Crée ou augmente un impôt, une taxe ou une cotisation | Nouvel impôt, hausse de taux, élargissement de l'assiette, suppression d'une niche fiscale | Impôt plancher sur les grands patrimoines ; taxe sur les superprofits |
| `impot_moins` | Supprime ou baisse un impôt, une taxe ou une cotisation | Exonération, baisse de taux, crédit d'impôt, niche fiscale nouvelle | Exonération d'impôt pour les retraités qui travaillent ; baisse de TVA |
| `institutions` | Organise l'État, les institutions ou les élections | Règles de fonctionnement des pouvoirs publics, des collectivités, de la justice ou des élections, création ou réforme d'un organisme | Mode de scrutin municipal ; statut d'un parquet spécialisé ; organisation d'une collectivité |
| `budget` | Fixe le budget de l'État ou de la Sécurité sociale | Lois de finances, de financement de la Sécurité sociale, lois de programmation des finances publiques, lois spéciales | Projet de loi de finances pour 2025 |
| `international` | Approuve un accord international ou prend position sur l'étranger | Ratification ou approbation d'un traité, d'une convention ; résolution sur un pays ou une organisation internationale | Accord France-Andorre ; soutien à l'Ukraine |
| `symbolique` | Reconnaissance, mémoire ou déclaration sans effet juridique direct | Résolution (sans force de loi), reconnaissance historique, entrée au Panthéon, journée nationale, commission d'enquête | Entrée au Panthéon ; reconnaissance de la « double dette » d'Haïti |

## Cas limites

- **Une aide conditionnée à une obligation** (une prise en charge réservée à ceux qui suivent un parcours) : `aide_plus` et `contrainte_plus`.
- **Une réforme qui change à la fois des droits à la hausse et à la baisse** (une réforme des retraites avec des gagnants et des perdants) : les deux codes, dans l'ordre de leur poids dans le texte.
- **Une sanction administrative** (amende infligée par une autorité, retrait d'agrément) : `sanction_plus`. Une simple obligation sans sanction propre : `contrainte_plus`.
- **Une proposition de résolution** : `symbolique`, ou `international` si elle porte sur un pays étranger.
- **Un budget** : `budget` seul. On ne détaille pas ses centaines de mesures.

## Niveau de vérification

Comme les résumés : la catégorie est d'abord attribuée par IA à partir des articles (niveau « ia », affiché), puis relue par un humain (niveau « relu »). Elle est enregistrée dans `donnees/redaction/<législature>.json`, champs `mesures` (liste de codes) et `mesuresNiveau`.

## À faire évoluer

- **Nationalisations et privatisations** (EDF, ArcelorMittal, autoroutes) : aucune catégorie ne les décrit bien, elles ont été classées `institutions` ou `contrainte_plus`. Une paire `nationalise` / `privatise` serait plus juste ; à ajouter, puis reclasser les textes concernés.
- **Premier passage** (30/10/2026) : 376 textes classés par IA, 24 non classés faute de texte officiel lisible ou de résumé.
