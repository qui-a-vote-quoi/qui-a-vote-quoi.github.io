# Idées en réserve

Idées discutées mais mises de côté le 29/10/2026, pour ne pas ajouter de complexité. À reprendre plus tard, seulement si elles servent le principe de départ : **simple et efficace**.

## Lot 3 du design

- **Une vraie page « Les partis »** : une grille des groupes dans l'ordre de l'hémicycle, avec une carte par groupe (nom, nombre de députés, niches, textes adoptés sur proposés, dernière proposition).
  - Question ouverte : afficher les **groupes parlementaires** tels quels, ou des **familles politiques** qui regroupent les groupes successifs (UMP → LR → DR, LREM → RE → EPR) pour un historique continu ?
  - Question ouverte : afficher la présence aux votes sur la carte, ou seulement sur la fiche parti avec son explication ?
  - Cas particulier : un groupe sans niche (EPR, a priori parce qu'il soutient le gouvernement).
- **Une frise de la journée de niche**, de 9 h à minuit, pour montrer comment le temps a été utilisé (sans parler d'« obstruction », voir la charte).
- **Un « fait du jour » sur l'accueil**, tiré des données. Exemple : un texte rejeté à 25 voix près, avec 246 députés absents.
- **Mes sujets trié par importance** (Retraites, Impôts, Santé, Logement en premier), avec une icône et un texte phare par carte.
- **Le taux d'adoption remis en contexte** sur la fiche parti : « 0 / 4, la moyenne de l'opposition est X / Y ».

## Pistes tirées du menu « Travaux parlementaires » de l'Assemblée

- **L'application des lois** (rubriques « Rapports sur l'application des lois » et « Baromètre de l'application des lois »). Une loi votée peut rester sans effet tant que ses décrets d'application ne sont pas publiés : le débat sur l'étiquetage citait justement des mesures d'Egalim 2 jamais appliquées. Un statut du type « Loi votée, en attente de ses décrets » répondrait honnêtement à « qu'est-ce que ça change pour moi ? ». Les dossiers de l'open data prévoient un lien vers l'échéancier des décrets, à vérifier.
- **Les amendements.** C'est par là que l'opposition influence vraiment les lois des autres. Fichier très volumineux (~350 Mo compressés pour la législature actuelle).
- **Les pétitions citoyennes.** Elles montrent une autre façon pour un citoyen de peser, en lien avec le message « votre voix compte ». Exemple : la pétition contre la loi Duplomb.
- **Les questions écrites et orales au gouvernement.** Elles montrent les sujets portés par chaque groupe, ce qui était la question de départ du projet.
- **Le Congrès** (révisions de la Constitution, votées par députés et sénateurs réunis). Rare, mais ce sont des votes majeurs.

## Autres sujets en attente

- **Les simulateurs** impôts, retraites et héritage. Ils sont annoncés « bientôt » sur les pages Impôts et Retraites.
- **Remonter avant 2017** : la période retenue est 2017-2026. Avant, l'open data est partiel (2012-2017) ou absent (2009-2012).
- **Le résumé du texte sur le DPE** est à vérifier : le texte complet n'était pas disponible en ligne.
- **Le champ `positionMajoritaire`** de l'open data est incohérent dans environ 3 % des cas. Ça peut valoir un signalement à l'Assemblée.

## Relecture citoyenne

Idée discutée le 30/10/2026 : faire relire les résumés par des citoyens plutôt que par une seule personne (plus de 400 résumés rédigés par IA à relire).

**Prérequis : un formulaire** (le même que pour les avis des testeurs), pour recevoir les propositions sans collecter de données sur le site.

**Dangers identifiés :**
- capture partisane : des militants organisés pourraient réécrire les résumés en faveur de leur camp ;
- responsabilité de l'éditeur : un contenu modifié par des inconnus doit être modéré ;
- données personnelles : il faut savoir qui relit, donc collecter des contacts (RGPD) ;
- qualité inégale et désaccords à arbitrer.

**À éviter :** l'édition ouverte façon wiki (comptes, serveur, modération lourde, contraire au site statique).

**Recommandation, par étapes :**
1. **« Proposer une correction »** sur chaque fiche : un lien vers le formulaire, avec le texte concerné indiqué. Le responsable du projet arbitre ; rien n'est publié sans lui.
2. **Un petit panel de relecteurs choisis** (4 à 8 personnes de sensibilités différentes), avec **relecture croisée** : un résumé passe à « relu » seulement quand deux relecteurs de sensibilités différentes l'ont approuvé, selon une grille tirée de la charte de neutralité. Outil simple : tableur partagé, ou GitHub pour ceux qui savent.
3. **Afficher la relecture** : « relu par 2 relecteurs de sensibilités différentes », avec la liste publique des relecteurs (pseudonymes) s'ils l'acceptent.

Priorité de relecture : les résumés qui portent une `remarque` dans `donnees/redaction/*.json` (texte officiel coupé, résumé tiré de l'exposé des motifs).

## Votes ordinaires sur des textes entiers (30/10/2026)

Le site montre les votes solennels et les votes des journées réservées. Il manque **474 scrutins publics ordinaires sur l'ensemble d'un texte**, hors niches, de 2017 à 2026 (231 en 15e législature, 137 en 16e, 106 en 17e). Les données sont déjà téléchargées (`donnees/brut/<leg>/scrutins.zip`, type `SPO`) ; `construire.py` les écarte.

- Contenu : 277 propositions de loi, 162 projets de loi du gouvernement, 27 accords internationaux, 8 résolutions.
- Participation faible : 104 votants en médiane, moins de 100 votants pour la moitié.
- Risque : noyer les textes qui parlent aux gens, et donner une fausse impression de vote massif.

**Recommandation** : les intégrer aux données, pas en vitrine. Ils comptent dans les fiches groupe, la recherche, « Les textes » et les chiffres de « Qui décide ». Ils restent hors du jeu et des pages de sujet par défaut, avec une option « Voir aussi les votes à faible participation ». Les accords internationaux restent à part. La participation est affichée bien en vue sur chaque carte. Il faudra des résumés IA (environ 400 textes) et leur relecture.

Ne restent impossibles à montrer : les textes adoptés à main levée (aucun vote nominatif) et les textes adoptés avec l'article 49.3 (pas de vote, seulement les motions de censure).

## Points de l'audit du 30/10/2026 à reprendre

Deux audits (calculs du site, données contre l'open data) ont été faits et leurs erreurs corrigées le 30/10/2026. Restent :

**Cas à vérifier à la main** (listés à chaque construction dans `donnees/base/<leg>/rapport.md`, section « Points à vérifier ») :
- 3 votes solennels sans dossier dans l'open data : n° 103 et 107 de la 15e législature (loi ordinaire « confiance dans la vie publique », absente des zips) et n° 2759.
- 5 votes cités par un dossier mais portant sur un autre objet, donc écartés : n° 3640, 2769, 1162, 2984, 8707.
- Une vingtaine de lignes de programme de niche à égalité entre deux dossiers, toutes non votées (pas examinées ou commencées) : aucun texte publié n'est touché.
- Niche du 12/02/2026 : une ligne est désormais reliée à DLR5L11N19503 (droit de vote des étrangers, dossier de la 11e législature) : vérifier que c'est le bon.
- Deux attributions d'auteur après changement de groupe : 15N38325 (« France des accents », attribué au groupe du dépôt mais inscrit à la niche AGIR-E) et 15N37007 (maladies chroniques, attribué à UDI-I mais inscrit à la niche AGIR-E).
- 13 résumés rédigés décrivaient un autre texte que celui voté ; ils ne sont plus affichés (dossiers 36488, 36726, 36771, 36910, 36912, 37209, 38180, 38254, 39209, 40261, 40693, 40711, 50450). À supprimer ou à garder pour un usage futur.

**Questions de méthode** :
- **Le jeu et les changements de sigle** : un même courant change de sigle d'une législature à l'autre (FI, LFI-NUPES, LFI-NFP ; LAREM, RE, EPR ; GDR, GDR-NUPES ; ECOLO, ECOS). Dans une séance qui mélange les périodes, ces groupes sont rarement classés (seuil de la moitié des textes), contrairement aux sigles stables (SOC, DEM, LR). Pistes : regrouper par « famille » avec une règle écrite et neutre, ou limiter une séance à une législature, ou baisser le seuil.
- **Votes ou textes** : « 146 grands votes sur 211 portaient sur un texte du gouvernement » correspond à 109 textes sur 167 (un texte peut être voté en plusieurs lectures). Choisir l'unité la plus juste pour « Qui décide » et l'écrire partout pareil.
