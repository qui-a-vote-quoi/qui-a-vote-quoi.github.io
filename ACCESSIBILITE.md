# Règles d'accessibilité

Le site s'adresse à tout le monde : il doit rester accessible à chaque évolution. Référentiel visé : **RGAA 4.1**, qui reprend le WCAG 2.1 niveau AA. Ces règles sont appliquées dans la maquette et doivent être vérifiées à chaque changement.

## Navigation et structure

- **Chaque vue a son propre titre d'onglet** (« Titre de la page – Qui a voté quoi »).
- **Au changement de vue, le focus va sur le titre principal**, pour que les lecteurs d'écran annoncent la nouvelle page.
- **Un lien « Aller au contenu »** apparaît au premier appui sur Tab.
- **Une seule balise h1 par vue, sans saut de niveau** : si une liste de cartes en h3 suit directement le h1, on ajoute un h2 caché (classe `sr-only`).
- **Un élément qui reçoit le focus n'est jamais caché** par l'en-tête fixe ou le bandeau de résultat (`scroll-padding`).

## Composants

- **Les boutons à état (Pour / Contre / Je ne sais pas) exposent `aria-pressed`**, et chaque rangée a un nom (« Votre vote : … »).
- **Les résultats en direct sont annoncés par une phrase courte** dans une zone `aria-live`, jamais par la relecture d'un panneau entier.
- **Les pastilles de groupe donnent le nom complet** aux lecteurs d'écran (« LFI-NFP, La France insoumise – NFP »).
- **Les liens qui ouvrent un nouvel onglet le signalent** (↗ visible et « nouvel onglet » lu).
- **Les tableaux ont des en-têtes de colonnes.**
- **Les graphiques ont une alternative textuelle** : l'hémicycle a une description, et chaque barre est accompagnée de ses chiffres.

## Couleurs et tailles

- **Texte : contraste d'au moins 4,5:1.** **Éléments graphiques et contours de boutons : au moins 3:1.** À vérifier en mode clair et en mode sombre.
- **Une information n'est jamais portée par la seule couleur** : toujours un texte, une icône ou une forme (par exemple les députés qui n'ont pas voté sont en gris très clair, comme des sièges vides : ils se distinguent par la clarté et pas seulement par la teinte, et leur nombre est toujours écrit en toutes lettres).
- **Zones cliquables d'au moins 24 px**, 44 px pour les boutons principaux.
- **Pas de défilement horizontal à 320 px de large** (zoom 400 %).
- **Les animations respectent « réduire les animations ».**

## Avant une mise en ligne

**Le contrôle automatique**, à lancer après chaque changement visible :

```bash
cd outils/accessibilite
npm install && npx playwright install chromium   # la première fois seulement
npm run verifier
```

Il ouvre chaque vue du site (accueil, groupes, textes, un sujet, une fiche texte votée plusieurs fois, une fiche avec débat, deux fiches groupe, une niche, À vous de voter, méthode, à propos) en clair et en sombre, sur ordinateur et sur mobile. Il vérifie :

- les règles WCAG 2.1 A et AA testables automatiquement (axe-core) : contrastes, noms des liens et boutons, titres, attributs ARIA, langue… ;
- les zones cliquables d'au moins 24 px ;
- un seul h1 par vue, le titre d'onglet, le focus sur le titre au changement de vue ;
- les liens vers un nouvel onglet signalés ;
- l'absence de défilement horizontal à 320 px ;
- l'absence d'erreur JavaScript.

Il liste les problèmes et se termine en erreur s'il en trouve.

Ces vérifications automatiques ne suffisent pas : il faut un test réel avec un lecteur d'écran (VoiceOver, NVDA) et une navigation complète au clavier.
