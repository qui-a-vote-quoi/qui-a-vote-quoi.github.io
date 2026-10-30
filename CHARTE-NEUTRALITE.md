# Charte de neutralité

Le site montre des faits et laisse chacun juger. Il ne dit jamais si un texte, un vote ou un parti est bon ou mauvais. Ces règles s'appliquent à tout le contenu.

## Les arguments des deux camps

Chaque texte présente les arguments de ceux qui l'ont soutenu et de ceux qui s'y sont opposés.

1. **Des arguments toujours attribués.** On écrit « Selon ses défenseurs » et « Selon ses opposants », jamais une affirmation à la voix du site.
2. **Une stricte symétrie** : autant d'arguments de chaque côté (2, au maximum 3), de longueur comparable, avec des formulations aussi neutres d'un côté que de l'autre.
3. **Uniquement des arguments réellement avancés**, tirés de sources officielles : le texte de la proposition de loi pour le camp « pour », et les débats en séance, le rapport de commission et les modifications de suppression pour le camp « contre ». Chaque argument renvoie à sa source.
4. **Pas de nom de groupe ni de parti dans les arguments.** On parle de « défenseurs » et d'« opposants ».
5. **Aucune note, aucun « vrai ou faux » sur les arguments.**

Production : les arguments sont extraits des sources officielles avec l'aide d'une IA, puis chaque fiche est relue par un humain avant publication.

Affichage : toujours visibles sur la fiche texte, sous « En clair ». Dans Mon bilan, derrière un lien « Voir les arguments », fermé par défaut.

## Règles déjà appliquées dans la maquette

- **L'utilisateur juge, pas le site.** Dans Mon bilan, il vote comme un député (Pour, Contre ou Je ne sais pas), et le site calcule seulement quels groupes ont voté comme lui.
- **Mon bilan est à l'aveugle** : l'auteur et le sort d'un texte restent cachés jusqu'au résultat.
- **Les égalités sont affichées.** Quand plusieurs groupes sont ex aequo, on les cite tous, sans en choisir un.
- **Pas de classement sur trop peu de votes.** Chaque pourcentage indique sur combien de textes il est calculé. Un groupe qui a voté sur moins de la moitié des textes votés par l'utilisateur est grisé et n'est pas classé.
- **Des faits, pas les accusations d'un camp.** Quand un texte n'est pas voté, on écrit « faute de temps avant minuit », pas « à cause de l'obstruction ». Le nombre de votes de la journée et le statut de chaque texte suffisent à le montrer.
- **L'ordre des groupes est celui de l'hémicycle**, de la gauche vers la droite. Pas de classement par taille ni par « réussite ».
- **Pas de classement de « performance » entre groupes.** Un texte passe d'abord parce que son groupe a la majorité. Les chiffres d'un groupe (textes proposés, adoptés, rejetés) ne s'affichent que sur sa fiche, avec leur contexte : opposition ou majorité, nombre de députés, période.
- **Le même gabarit pour tous les groupes** : mêmes blocs, mêmes chiffres, même mise en forme.
- **Les positions des groupes sont recalculées à partir du décompte des voix**, parce que le champ `positionMajoritaire` de l'open data est parfois faux.
- **Les résumés « En clair » sont rédigés à partir des articles officiels** du texte, pas de son seul titre. Quand ce n'est pas possible, la fiche le signale.

## Rédaction par IA et vérification humaine

Pour publier le plus de contenu possible, une partie du travail est faite par IA puis relue. Le niveau est toujours affiché au lecteur :

| Contenu | Niveaux | Où c'est enregistré |
|---|---|---|
| Résumé, titre court, « qui est concerné » | **à venir** (titre officiel et lien vers l'Assemblée), **rédigé par IA, non vérifié**, **relu par un humain** | `donnees/redaction/<législature>.json`, champ `niveau` (`a_venir`, `ia`, `relu`) |
| Sujet du texte | **attribué par IA**, **relu** | même fichier, champ `sujetNiveau` |
| Journée réservée (niche) | **vérifiée par IA dans les comptes rendus**, **vérifiée par un humain** ; non publiée tant qu'elle n'est pas vérifiée | `donnees/validation/niches-<législature>.json`, champ `statut` (`verifie_ia`, `valide`, `a_valider`, `rejete`) |

Règles pour l'IA :
- elle résume à partir de l'extrait du texte officiel déposé (`pipeline/extraits.py`), jamais de mémoire. Quand l'extrait ne suffit pas (texte coupé, articles absents), elle le signale dans le champ `remarque`, à regarder en priorité à la relecture ; un résumé qui ne pourrait s'appuyer que sur le titre n'est pas publié ;
- elle décrit ce que le texte fait, pas ce que ses auteurs en disent : pas de qualificatifs repris de l'exposé des motifs, aucun nom de groupe, de parti ni de personne ;
- pour vérifier une niche, elle cite le compte rendu (champ `preuve`) ; sans preuve, la niche reste « à valider ».

Les votes eux-mêmes ne sont jamais rédigés : ils viennent des décomptes officiels.
