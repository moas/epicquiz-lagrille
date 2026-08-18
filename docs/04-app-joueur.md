# EpicQuiz — App tablette Joueur

Une instance par participant (2 au total). Application minimaliste — le joueur n'a besoin de voir que ce qui le concerne directement.

## 1. Écrans

1. **Connexion** — saisie du `username` (distribué par le Manager) et du nom de la personne. Envoi `POST /api/auth/join/ {username, name}`, obtention du token, ouverture de la connexion WebSocket (écoute seule, cf. `03-protocole-websocket.md` §0). Reste affiché jusqu'à connexion confirmée.
2. **Attente** — affiché hors de son tour ou avant le début de partie. Montre le score courant des deux joueurs et le statut de la partie (ex. "Au tour de [adversaire]").
3. **Révélation de grille** — pendant les 30 secondes initiales (et au retour de pause pub) : grille complète avec les cases à attribut spécial visibles. Décompte visuel du temps restant.
4. **Sélection de case** — actif uniquement quand c'est le tour du joueur. Grille en mode jeu (cases jouées visibles, non jouées neutres). Tap sur une case → `POST /episodes/<eid>/select-cell/ {cell_id}`, désactive immédiatement l'interaction jusqu'à réponse HTTP (éviter double-tap) ; l'affichage se met ensuite à jour via l'événement `cell_selected` reçu sur WebSocket.
5. **Question active** — QCM avec chronomètre serveur affiché (le compte à rebours local est purement visuel, jamais autoritaire — voir §3). Tap sur une proposition → `POST /episodes/<eid>/submit-answer/ {chosen_index}`, désactivation immédiate.
6. **Résultat de case** — bref écran de confirmation (bonne/mauvaise réponse, points gagnés/retirés) avant retour à l'écran Attente ou Sélection selon le nouveau tour.
7. **Verrouillé** — affiché en superposition dès réception d'un événement `player_locked` concernant ce joueur (ciblé ou `target: "all"`). Toute interaction (sélection, réponse) est désactivée tant que l'événement `player_unlocked` correspondant n'est pas reçu, quel que soit l'écran sous-jacent (cf. `03-protocole-websocket.md` §6).
8. **Fin de partie** — score final, vainqueur.

## 2. Ce que le joueur ne voit jamais

- Les cases non jouées de l'adversaire au-delà de ce que la règle de mémorisation autorise (aucune info privilégiée par rapport à ce qui est diffusé sur l'écran TV).
- Aucun contrôle sur le déroulé (pas de bouton "suivant", "valider" au nom de l'animateur).

## 3. Gestion du temps de réponse

Le chronomètre du QCM est **calculé côté serveur** au moment de l'événement `question_revealed` (horodatage + `time_limit_sec` du `Challenge`). L'app affiche un décompte local recalé en continu sur `server_ts` reçu dans les messages WebSocket, pour éviter toute dérive perceptible sans dépendre de l'horloge locale de la tablette. Si le temps expire côté serveur avant réception d'une requête `submit-answer`, le serveur émet directement l'événement `cell_resolved` avec `result: "time_expired"` — l'app doit gérer ce cas comme une résolution normale, pas comme une erreur.

## 4. Reconnexion

- À la reconnexion, l'app doit se resynchroniser sur `full_state` et déterminer l'écran courant uniquement à partir de la `phase` et de `current_turn_participant_id` du snapshot — jamais à partir de son état local avant coupure.
- Si la coupure survient pendant une question active et que le temps restant côté serveur est encore positif à la reconnexion, l'app doit reprendre l'affichage du QCM avec le temps restant réel (pas remis à zéro).
- Toute coupure de connexion n'est pas traitée de la même façon : une coupure réseau déclenche une reconnexion automatique, un token invalidé (session ouverte ailleurs) fait basculer directement vers l'écran de Connexion sans retenter — voir `11-frontend-svelte.md` §3 pour le détail de cette distinction.

## 5. Contraintes matérielles

- Fonctionnement exclusif sur le réseau local du studio — aucune requête vers un domaine externe (voir `09-deploiement-reseau-ferme.md`).
- Application pensée pour rester toujours en mode portrait/paysage fixe selon le mobilier du plateau (à valider avec la régie), sans réorientation en cours de partie.
- Pas de notification, pas de son propre à la tablette joueur — tout l'aspect sonore du plateau est géré par l'Opérateur.
