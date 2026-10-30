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

## Vivre le débat

Pour comprendre un vote, on peut revivre un résumé du vrai débat en séance, réplique après réplique.

- **Des citations exactes du compte rendu officiel**, jamais reformulées. Un script (`pipeline/verifier_debats.py`) écarte toute citation qui ne figure pas mot pour mot dans l'intervention d'origine.
- **L'orateur, sa qualité et son groupe viennent du compte rendu** (`pipeline/debats.py`), jamais de l'IA.
- **Une stricte symétrie** : la présentation du texte, l'avis du gouvernement, puis autant de répliques favorables que défavorables, en alternance. Si une citation est écartée d'un côté, une réplique de l'autre côté est retirée.
- **Sur le fond** : pas d'attaques personnelles, de querelles de procédure ni d'ironie.
- **Anonymat avant le vote** (« une députée opposée au texte ») : une citation qui nomme une personne, un parti ou un groupe est écartée automatiquement. Les noms et les groupes sont révélés après le vote, et sur la fiche du texte.
- **Même couleur pour les deux camps** ; seul le côté change.
- **Texte consensuel** : quand aucun orateur ne s'y oppose sur le fond, on ne fabrique pas de camp opposé. Le débat n'est pas affiché (à terme : la présentation et la mention du consensus).
- Le choix des répliques est fait par IA, puis relu par un humain ; le niveau est affiché.

### En mots simples

Les citations exactes sont parfois difficiles à comprendre sans connaître le vocabulaire de l'Assemblée. Un interrupteur au-dessus de chaque débat (« Citations exactes » / « En mots simples ») affiche à la place une version simple de chaque réplique. Les citations exactes restent l'affichage par défaut ; le choix du lecteur est gardé sur son appareil.

- **Une reformulation, pas une citation** : elle est présentée comme telle, la citation exacte reste à un clic et fait foi.
- **Fidèle avant d'être simple** : rien d'ajouté (fait, chiffre, personne, mesure), même degré de certitude, mêmes exemples et conditions, même ordre de cause à effet, aucun mot de jugement. Un mot chargé employé par l'orateur reste entre guillemets, comme étant le sien.
- **Mêmes règles qu'aux citations** : aucun nom de personne ni de groupe, même soin pour les deux camps.
- **Écrite par IA en trois passes**, méthode choisie après des tests à l'aveugle : un agent rédige, un deuxième lit comme un élève de 4e sans voir la citation et note ce qui le bloque, un troisième corrige ces points en repartant de la citation. Un glossaire fixe donne une seule explication neutre pour chaque mot difficile. Consignes : `pipeline/consignes/`.
- **Contrôlée par script** (`pipeline/vulgariser.py`) : une version qui nomme quelqu'un, reprend le rôle déjà affiché, ajoute « je pense que » ou dépasse 80 mots est écartée, et la réplique reste en citation exacte.
- **Pas relue par un humain** : c'est écrit sous chaque débat en mots simples.
