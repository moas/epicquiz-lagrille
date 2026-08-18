# EpicQuiz — Protocole temps réel

## 0. Principe général : HTTP pour agir, WebSocket pour être informé

Toute action provenant d'un client (sélection de case, réponse au QCM, intervention manager, commande régie...) passe par une requête **HTTP** classique, authentifiée par le `Token` DRF. Le **WebSocket est strictement descendant** : il ne sert qu'à pousser les événements et l'état du jeu vers les clients connectés, jamais à recevoir une action.

Ce découplage a deux avantages : chaque action a une réponse HTTP synchrone immédiate (succès/erreur avec code HTTP standard), et le WebSocket reste un canal de diffusion pur, plus simple à raisonner et à déboguer (un seul type de flux : serveur → clients).

## 1. Deux canaux de diffusion distincts

| Canal | Endpoint WebSocket | Consumer | Clients (en écoute) |
| --- | --- | --- | --- |
| Jeu | `wss://<host>/ws/episode/<eid>/game/` | `GameConsumer` | Joueur 1, Joueur 2, Animateur, Manager (supervision), Écran TV (en lecture) |
| Broadcast | `wss://<host>/ws/episode/<eid>/broadcast/` | `BroadcastConsumer` | Opérateur, Écran TV |

Les Écrans TV écoutent les deux canaux : Broadcast pour les commandes de bascule d'affichage, Jeu pour le contenu (état de la grille, question en cours, scores). Aucun client n'écrit jamais sur un canal WebSocket — l'écriture se fait uniquement via HTTP.

## 2. Authentification

Identique pour HTTP et WebSocket : le même `Token` DRF.

1. À la validation de la grille, la tâche Celery `provision_episode_participants` crée les `User` de plateau (joueur ×2, animateur, écran ×N, opérateur) — `username` généré, `name` vide, aucun token — et leur `Participant` associé (rôle, tags, ordre).
2. Le Manager distribue les `username` générés aux appareils avant le direct.
3. Au démarrage de l'app : `POST /api/auth/join/ {username, name}`. Le serveur renseigne `User.name`, invalide l'éventuel token existant, en émet un nouveau.
4. Toute requête HTTP ultérieure porte l'en-tête `Authorization: Token <drf_token>` (`TokenAuthentication` standard DRF).
5. La connexion WebSocket s'ouvre avec `?token=<drf_token>` en query string. Un middleware ASGI dédié (`TokenAuthMiddleware`) résout le token en `User`, puis le Consumer résout le `Participant` correspondant à l'épisode de l'URL (ou le rôle virtuel `"manager"` via `is_staff` si aucun `Participant` n'existe).

**Le rôle n'est jamais déclaré par le client** — toujours résolu côté serveur, aussi bien pour valider une requête HTTP que pour déterminer le contenu poussé sur WebSocket.

Manager/Admin obtiennent leur token via un flux classique nom d'utilisateur + mot de passe (`ObtainAuthToken`), sans passer par `/api/auth/join/`.

## 3. Format des requêtes HTTP d'action

```
POST /api/episodes/<eid>/select-cell/
Authorization: Token <drf_token>
Content-Type: application/json

{ "cell_id": 12 }
```

Réponse synchrone :
- **200 OK** — action acceptée. Corps minimal (ex. `{"status": "ok"}`) ; l'effet complet arrive via WebSocket.
- **400 Bad Request** — action refusée (mauvais tour, mauvaise phase, condition non remplie) :

```json
{ "code": "NOT_YOUR_TURN", "message": "Ce n'est pas votre tour de jouer." }
```

- **403 Forbidden** — rôle non autorisé pour cet endpoint (ex. un joueur qui appelle `/launch-question/`).

## 4. Format des messages WebSocket (push uniquement)

Diffusion d'un événement de jeu à tout le groupe :

```json
{
  "type": "event",
  "event_type": "cell_selected",
  "sequence": 14,
  "payload": { "cell_id": 12, "position": 12, "participant_id": 4 },
  "server_ts": "2026-08-18T20:14:03.180Z"
}
```

État complet à la connexion/reconnexion :

```json
{ "type": "full_state", "snapshot": { ... }, "last_sequence": 27 }
```

## 5. Endpoints par rôle (canal Jeu)

| Endpoint | Joueur | Animateur | Manager |
| --- | --- | --- | --- |
| `POST /episodes/<eid>/select-cell/` | ✅ (si son tour) | ✅ (relais oral) | ❌ |
| `POST /episodes/<eid>/launch-question/` | ❌ | ✅ | ❌ |
| `POST /episodes/<eid>/submit-answer/` | ✅ (si concerné) | ❌ | ❌ |
| `POST /episodes/<eid>/lock-players/` | ❌ | ✅ | ❌ |
| `POST /episodes/<eid>/unlock-players/` | ❌ | ✅ | ❌ |
| `POST /episodes/<eid>/start-game/` | ❌ | ✅ | ✅ |
| `POST /episodes/<eid>/start-ad-break/` / `resume-game/` | ❌ | ✅ | ✅ |
| `POST /episodes/<eid>/end-game/` | ❌ | ✅ | ✅ |
| `POST /episodes/<eid>/manager-intervention/` | ❌ | ❌ | ✅ uniquement |

Chaque endpoint accepté écrit un `GameEvent`, met à jour la projection (`GameStateSnapshot`), puis diffuse un message `event` sur le canal Jeu.

## 6. Verrouillage joueur (`lock-players` / `unlock-players`)

L'animateur peut verrouiller l'interaction d'un joueur précis ou de tous les joueurs — utile pour geler le jeu le temps de régler un problème plateau sans passer par une intervention Manager.

```
POST /api/episodes/<eid>/lock-players/
{ "target": "all" }
```

ou

```
POST /api/episodes/<eid>/lock-players/
{ "target": "participant", "participant_id": 4 }
```

Traitement serveur : écrit `GameEvent(type=PLAYER_LOCKED, payload={"target": ...})`, met à jour `GameStateSnapshot.locked_participant_ids`, diffuse l'événement sur le canal Jeu. `POST .../unlock-players/` suit la même forme et écrit `PLAYER_UNLOCKED`.

Côté app Joueur : à réception d'un événement `player_locked` concernant son `participant_id` (ou `target: "all"`), l'app désactive immédiatement toute interaction (sélection de case, réponse au QCM) et affiche un état verrouillé visible, jusqu'à réception de l'événement `player_unlocked` correspondant. Le verrouillage est **purement une désactivation d'interaction côté client, doublée d'un rejet serveur** : toute requête `select-cell`/`submit-answer` d'un participant verrouillé est refusée en 400 même si l'app cliente a été contournée.

## 7. `manager-intervention` — l'endpoint d'exception

```
POST /api/episodes/<eid>/manager-intervention/
{
  "action": "force_cell_resolution",
  "cell_id": 12,
  "forced_result": "success",
  "reason": "tablette joueur 2 déconnectée pendant le temps de réponse"
}
```

Le serveur exige un champ `reason` non vide, et écrit systématiquement un `GameEvent` de type `MANAGER_INTERVENTION` en plus de l'événement métier qu'elle déclenche (ex. `CELL_RESOLVED`), avec l'identité de l'utilisateur Django authentifié.

Actions supportées à minima : `force_cell_resolution`, `reopen_cell`, `adjust_score`, `skip_ad_break`, `pause_game`.

## 8. Endpoints broadcast (canal Broadcast, opérateur uniquement)

| Endpoint | Effet |
| --- | --- |
| `POST /episodes/<eid>/change-tv-view/` | Bascule l'affichage TV entre `grid`, `active_question`, `scores`, `cell_replay` |
| `POST /episodes/<eid>/trigger-effect/` | Joue un effet sonore/visuel manuel — n'affecte jamais l'état de jeu |
| `POST /episodes/<eid>/tally/` | Contrôle des voyants tally caméra (hors scope jeu) |

Ces endpoints ne produisent **aucun** `GameEvent` — hors du domaine de jeu par construction. Leur effet est diffusé uniquement sur le groupe `episode_<eid>_broadcast`.

Certains effets sont déclenchés automatiquement par le serveur en réaction à un `GameEvent` (ex. son dédié sur `EMPTY_CELL_PLAYED`) et relayés sur le canal Broadcast pour que l'opérateur ait une trace visuelle de ce qui vient de se jouer automatiquement — sans qu'il ait besoin d'agir.

## 9. Reconnexion

Le WebSocket étant purement descendant, la reconnexion ne fait que réafficher l'état — aucune action en attente à rejouer côté client. À l'ouverture de toute connexion WebSocket réussie, le serveur envoie immédiatement `full_state` (§4). Le client remplace intégralement son état local par ce snapshot avant de traiter tout nouvel `event` reçu ensuite. Si une action HTTP était en cours au moment de la coupure, son résultat (succès ou échec) a de toute façon déjà été déterminé côté serveur de façon synchrone — la reconnexion WebSocket ne fait que rattraper l'affichage.
