# Consignes : « En mots simples »

Pour chaque réplique de « Vivre le débat », une version en mots simples, affichée à la place de la citation exacte quand le lecteur choisit « En mots simples ». Lecteur visé : un ado de 14 ans, en 4e, qui ne connaît pas le fonctionnement de l'Assemblée.

La méthode a été choisie après trois tours de tests à l'aveugle (30/10/2026) : **trois passes**, faites par trois agents différents.

1. **Rédiger** : une première version, à partir de la citation.
2. **Lire** : un lecteur de 14 ans, qui ne voit que la version simple, note ce qui le bloque.
3. **Corriger** : le rédacteur ne corrige que ces points, en repartant de la citation.

Puis `python3 pipeline/vulgariser.py verifier <législature> <fichier>` contrôle chaque version et l'enregistre. Une version qui échoue n'est pas publiée : la réplique reste en citation exacte.

Fichiers d'un lot (préparés par `python3 pipeline/vulgariser.py preparer`) : `{"<dossier>": {"titre", "enClair", "repliques": [{"n", "role", "qualite", "citation"}]}}`. Ce que le site affiche avant la réplique : le titre, le résumé « en clair », puis le rôle de l'orateur (« Présentation du texte », « Gouvernement », « + Pour », « − Contre »).

Sortie des passes 1 et 3 : `{"<dossier>": [{"n": 0, "simple": "..."}]}`.

## Règles communes (fidélité et neutralité)

1. Tu ne t'appuies QUE sur la citation, le titre et le résumé « en clair ». Tu n'ajoutes aucun fait, chiffre, cause, conséquence, personne, groupe, organisme ou mesure qui ne soit pas dans la citation.
2. Tu gardes l'idée et la position de l'orateur, sans renforcer ni affaiblir son argument. Même degré de certitude : « je propose » n'est pas « j'interdis », « pourrait » n'est pas « va ». Une affirmation reste une affirmation : n'ajoute pas « je pense que », « selon moi » s'ils ne sont pas dans la citation.
3. Les nuances et conditions (« mais », « si », « sauf », « à condition que ») restent. Les exemples concrets et les chiffres restent. Si tu dois raccourcir, retire les formules et les répétitions, jamais un exemple ni une condition.
4. L'ordre de cause à effet reste celui de la citation.
5. Aucun mot de jugement ajouté (« clairement », « juste », « dangereux », « malheureusement »…). Un mot chargé employé par l'orateur (« austérité », « laxisme »…) reste entre guillemets, comme étant le sien.
6. Pas de métaphore ajoutée, d'humour, d'ironie, de langage familier. Simple ne veut pas dire « jeune » : ton sobre.
7. Aucun nom de personne, de parti ou de groupe (anonymat avant le vote).
8. Même soin pour le « pour » et le « contre » : longueur et ton comparables.
9. Le rôle est déjà affiché par le site : ne commence pas par « Pour : », « Contre : », « Le rapporteur explique… ». Écris directement ce que dit l'orateur, avec sa voix (« je », « nous »). Pour le gouvernement, ne lui prête une position que si la citation la dit en toutes lettres.
10. Mots difficiles : reprends l'explication de `pipeline/consignes/glossaire.json`, intégrée dans la phrase plutôt qu'entre parenthèses. Pour tout autre mot qu'un élève de 4e ne connaîtrait pas, même courant chez les adultes (crédits, actionnaires, densifier, urbanisme, repentis…), remplace-le par des mots simples ou explique-le en quelques mots. Pas de sigle sans explication.
11. 50 mots maximum, phrases de 15 mots en moyenne et de 25 au maximum. Pas de parenthèses en cascade.
12. Si une partie de la citation est impossible à comprendre sans un contexte absent, n'invente pas : reste au plus près de ce qui est dit.

## Passe 1 : rédiger

Applique les règles communes à chaque réplique du lot.

## Passe 2 : lire (agent séparé, qui ne voit PAS les citations)

Tu joues un lecteur de 14 ans, curieux, qui ne connaît rien à la politique. Tu lis le titre, le résumé « en clair », le rôle de l'orateur et la version simple (pas la citation). Pour chaque version, note honnêtement : `mots` (mots ou expressions que tu ne comprends pas), `flou` (pronom dont tu ne sais pas à quoi il renvoie, étape de raisonnement qui manque, phrase trop longue, idée abstraite), `question` (la question que tu poserais, ou null). Tout est clair : listes vides et null. Ne réécris rien.

Sortie : `{"<dossier>": [{"n": 0, "mots": [], "flou": [], "question": null}]}`.

## Passe 3 : corriger

Pour chaque réplique :
1. Relis d'abord la citation : c'est elle la référence, pas la version simple.
2. Corrige UNIQUEMENT ce qui bloque le lecteur : remplace ou explique les mots signalés, donne leur référent aux pronoms flous, ajoute l'étape de raisonnement manquante SI elle est dans la citation. Si la réponse à sa question n'est pas dans la citation, n'invente rien : simplifie plutôt la phrase pour qu'elle ne pose plus la question.
3. Vérifie à nouveau toutes les règles communes, en particulier la fidélité (rien d'ajouté, même certitude, mêmes exemples, même ordre de cause à effet).
