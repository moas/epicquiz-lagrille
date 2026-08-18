# Revue des spécifications EpicQuiz

## Synthèse

Le découpage par rôles, le serveur autoritaire et la séparation Jeu/Broadcast sont de bonnes fondations. Les spécifications ne verrouillent toutefois pas encore les invariants nécessaires au direct : resynchronisation, authentification des appareils, transitions de jeu et rejouabilité des corrections Manager.

## Bloquants

### 1. `full_state` ne permet pas de reconstruire l'écran

Le protocole promet une resynchronisation complète, mais `GameStateSnapshot` ne contient ni la grille et ses cellules, ni la question active (propositions et échéance), ni les participants, ni l'état Broadcast. Un joueur reconnecté au milieu d'un QCM ou une TV reconnectée ne peuvent pas redessiner leur écran à partir du seul snapshot.

Définir un schéma versionné de `full_state`, éventuellement filtré par rôle, contenant toutes les données d'affichage : tour, cellule, question, échéance serveur, grille, participants, scores et vue TV.

### 2. Course entre snapshot et événements WebSocket

`last_sequence` est transmis, mais aucun mécanisme ne garantit qu'un événement produit entre la lecture du snapshot et l'inscription du consumer au groupe n'est pas perdu. Il n'existe pas non plus de rattrapage de séquence ni de détection d'un trou.

Définir un point de coupure atomique : sous verrou de l'épisode, lire le snapshot et sa séquence, inscrire le consumer, transmettre les événements supérieurs à cette séquence, puis les nouveaux événements. Le client doit détecter une séquence non contiguë et demander une resynchronisation.

### 3. Le `username` seul n'est pas une authentification suffisante

Toute personne qui connaît le `username` d'un compte plateau peut ouvrir une session et invalider celle du véritable appareil. Le réseau fermé réduit l'exposition mais ne protège ni une erreur de distribution, ni un appareil compromis, ni l'écoute du Wi-Fi. Le document annonce huit caractères mais illustre `XYBNN`, qui n'en a que cinq.

Utiliser un secret à usage unique de forte entropie, expirant et lié à l'épisode et au rôle (par exemple QR code). Définir TLS et le cycle de vie d'un certificat local. Éviter le token dans la query string WebSocket, ou spécifier les protections de journalisation.

### 4. Les interventions Manager ne sont pas rejouables sans compensation

`reopen_cell`, `adjust_score`, `pause_game` et `skip_ad_break` sont proposés, mais aucun événement métier ni règle de projection ne dit comment annuler ou conserver les effets précédents. Rouvrir une case après attribution de points ou d'un lot est donc ambigu. Un simple `MANAGER_INTERVENTION` ne permet pas de recalculer un score final déterministe.

Pour chaque override, définir préconditions, payload, événements de compensation et effet sur la projection et le rapport. Ajouter les types manquants : pause/reprise hors publicité, correction de score, réouverture et annulation/attribution de lot.

## Risques élevés

### 5. Contraintes de données insuffisantes

`Challenge.cell` est une `ForeignKey` avec un `related_name` singulier : plusieurs cellules peuvent référencer le même challenge. Les règles sur les deux joueurs, leurs ordres, le nombre de cellules et la réutilisation des lots ne sont pas protégées en base. « Exactement une proposition correcte » n'est qu'une validation applicative.

Exprimer les invariants critiques en contraintes SQL lorsque possible, notamment l'unicité Challenge–Cell, puis compléter par des validations transactionnelles. Définir la politique de réutilisation d'un `Prize`.

### 6. Concurrence et idempotence des commandes non définies

Un double-tap, une sélection simultanée par joueur et animateur, ou une réponse reçue à l'échéance peuvent produire plusieurs événements. La contrainte `(episode, sequence)` ne suffit pas à rendre l'attribution de séquence sûre.

Spécifier un command handler transactionnel par épisode avec verrouillage de ligne et clé d'idempotence. Pour chaque endpoint, documenter le résultat d'un retry et les erreurs (`CELL_ALREADY_PLAYED`, `ANSWER_WINDOW_CLOSED`, etc.).

### 7. Déroulé de tour incomplet

Les événements sont listés, mais le prochain joueur et la prochaine phase ne sont pas définis explicitement pour une mauvaise réponse, une expiration, une case vide, un vol, une pause ou une correction. Les payloads ne contiennent pas toujours l'information nécessaire au recalcul.

Ajouter une table de transition complète : phase, acteur autorisé, commande, événements, prochaine phase, prochain joueur et effet de score. Elle doit servir directement aux tests du moteur.

## Incohérences et lacunes de contrat

- Les URL alternent entre `/episodes/...` et `/api/episodes/...`. Choisir un préfixe et publier requêtes, réponses et erreurs pour tous les endpoints.
- `GameEvent.emitted_by` est une chaîne libre. Un identifiant stable d'acteur (`User`, et si pertinent `Participant`) est nécessaire pour l'audit après renommage.
- Le passage à `ready` déclenche un provisionnement Celery asynchrone, sans condition empêchant le direct tant que les comptes ne sont pas créés. Il doit être idempotent, observable et bloquant pour le démarrage.
- La sélection de questions ne définit ni stratégie anti-répétition, ni concurrence sur `usage_count`, ni comportement si la banque est insuffisante.
- Le chronomètre exige une horloge serveur mais son échéance n'est pas explicitement persistée dans un événement. Conserver `deadline_at` dans `QUESTION_REVEALED` et définir la résolution d'expiration.
- Les payloads ne sont ni versionnés ni validés. Définir un schéma par type d'événement et une politique de compatibilité pour les rapports.

## Ordre recommandé

1. Définir la machine à états et les compensations Manager.
2. Définir `full_state`, le rattrapage WebSocket et les schémas d'événements.
3. Sécuriser le provisionnement et l'authentification des appareils.
4. Poser les contraintes transactionnelles et contrats HTTP idempotents.
5. Finaliser les écrans par rôle à partir de ces contrats stabilisés.
