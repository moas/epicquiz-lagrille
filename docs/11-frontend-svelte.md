# EpicQuiz — Frontend Svelte : structure et composants partagés

Les 5 apps (Joueur, Animateur, Écran TV, Manager, Opérateur) partagent le même protocole (`03-protocole-websocket.md`) et une bonne partie de leur affichage (grille, question, scores, chrono). Plutôt que de dupliquer cette logique 5 fois, on structure le frontend en **monorepo** avec un package partagé.

## 1. Structure du monorepo

```
epicquiz-frontend/
  packages/
    shared/
      src/
        api/         → client HTTP (fetch + token)
        ws/           → client WebSocket (écoute seule)
        stores/        → stores Svelte (état de jeu, connexion, auth)
        components/     → composants Svelte réutilisables
        types/           → types TS partagés (miroir des payloads GameEvent)
  apps/
    player/    (Vite + Svelte, build isolé)
    presenter/ (= app Animateur)
    tv/        (= app Écran TV)
    manager/   (= app Manager)
    operator/  (= app Opérateur)
```

Chaque app dans `apps/` est un build Vite indépendant qui importe `packages/shared` — au build final (`09-deploiement-reseau-ferme.md`), ça donne 5 bundles statiques séparés, chacun servi par nginx sous son propre chemin (`/player/`, `/presenter/`, `/tv/`, `/manager/`, `/operator/`).

## 2. Package `shared` — client API

**`api/http.ts`** — wrapper `fetch` unique :
- Ajoute `Authorization: Token <token>` automatiquement (token lu depuis le store `auth`).
- Centralise la gestion des réponses `400`/`403` (cf. `03-protocole-websocket.md` §3) en erreurs typées, exploitables uniformément par chaque app (affichage du `message` d'erreur).
- Un module `endpoints.ts` liste tous les endpoints définis dans `03-protocole-websocket.md` §5-8 (`selectCell(cellId)`, `submitAnswer(index)`, `lockPlayers(target, participantId?)`, `changeTvView(screenId, view)`, etc.) — chaque app n'importe que les fonctions dont elle a besoin.

## 3. Client WebSocket — connexion et reconnexion

**`ws/socket.ts`**, **strictement en écoute** (cf. `03-protocole-websocket.md` §0) : sa seule responsabilité est le cycle de vie de la connexion. Il ne connaît ni `gameState`, ni aucune logique métier — à chaque message reçu, il le publie sur le bus d'événements (§4) et rien d'autre.

**Reconnexion** : backoff exponentiel avec jitter (délai de base ~500ms, doublement jusqu'à un plafond ~10s, plus une variation aléatoire pour éviter que tous les appareils retentent en même temps après une coupure réseau commune).

**Distinction critique à la fermeture de connexion** — deux cas très différents à traiter séparément :
- **Coupure réseau** (perte WiFi, timeout) → reconnexion automatique en boucle selon le backoff ci-dessus, sans action utilisateur. Le serveur renverra `full_state` à la reconnexion (cf. `03-protocole-websocket.md` §9), donc aucune perte d'information.
- **Token invalidé** (le serveur ferme la connexion avec un code dédié, ex. `4001`, parce qu'une nouvelle connexion s'est authentifiée avec le même compte — cf. règle "un seul token actif" en `01-architecture-backend.md` §5) → **ne pas retenter**. L'app efface le token local et **bascule immédiatement sur `JoinScreen`**, avec un message explicite ("Session ouverte sur un autre appareil") — jamais de boucle de reconnexion sur un token qui échouera systématiquement.

Le store `connectionStatus` (`connected` / `reconnecting` / `disconnected` / `session_invalidated`) reflète cette distinction et est consommé par le composant `ConnectionBadge` commun.

## 4. Bus d'événements — `EventTarget` natif du navigateur

Plutôt que de coupler directement le client WebSocket au store `gameState`, ou de dépendre d'une librairie de pub/sub externe, on utilise l'API native `EventTarget`/`CustomEvent` du navigateur comme bus d'événements — disponible nativement, sans dépendance, et parfaitement compatible avec Svelte 5 :

```ts
// ws/eventBus.ts
export const eventBus = new EventTarget();
```

`ws/socket.ts` publie chaque message reçu (format clé-valeur du protocole, cf. `03-protocole-websocket.md` §4) sous forme de `CustomEvent`, sans aucune connaissance de qui écoute :

```ts
// ws/socket.ts
socket.onmessage = (raw) => {
  const msg = JSON.parse(raw.data);
  const eventName = msg.type === "event" ? msg.event_type : msg.type; // "full_state", "cell_selected", ...
  eventBus.dispatchEvent(new CustomEvent(eventName, { detail: msg }));
};
```

Chaque composant Svelte s'abonne uniquement à ce qui le concerne, via `$effect` avec nettoyage automatique (Svelte 5, runes) :

```svelte
<!-- LockOverlay.svelte -->
<script>
  import { eventBus } from "../ws/eventBus";

  let locked = $state(false);

  $effect(() => {
    const onLocked = (e) => { if (concernsThisParticipant(e.detail)) locked = true; };
    const onUnlocked = (e) => { if (concernsThisParticipant(e.detail)) locked = false; };
    eventBus.addEventListener("player_locked", onLocked);
    eventBus.addEventListener("player_unlocked", onUnlocked);
    return () => {
      eventBus.removeEventListener("player_locked", onLocked);
      eventBus.removeEventListener("player_unlocked", onUnlocked);
    };
  });
</script>
```

Ce découplage permet à **plusieurs consommateurs indépendants** de réagir au même flux sans que le transport ait à les connaître :
- Le store `gameState` (§5) s'abonne pour maintenir l'état de jeu affiché.
- `EventLogViewer.svelte` (Manager) s'abonne directement aux événements bruts pour son propre défilement, sans dépendre de la forme de `gameState`.
- Un futur système de notification sonore (ex. un signal discret côté Écran TV sur `empty_cell_played`) pourrait s'abonner sans toucher au reste — pas besoin de modifier `socket.ts` ni `gameState` pour ajouter un nouveau comportement réactif à un événement existant.

Chaque app choisit ce à quoi elle s'abonne ; aucune n'est obligée de passer par `gameState` pour consommer les événements bruts.

## 5. Store `gameState` — reducer, abonné au bus

```ts
// stores/gameState.ts
eventBus.addEventListener("cell_selected", (e) => {
  const event = e.detail;
  gameState.update((state) => ({
    ...state,
    cells: updateCell(state.cells, event.payload.cell_id, { state: "selected" }),
  }));
});

eventBus.addEventListener("cell_resolved", (e) => {
  const event = e.detail;
  gameState.update((state) => ({
    ...state,
    scores: applyResolution(state.scores, event.payload),
    activeQuestion: null,
  }));
});

eventBus.addEventListener("player_locked", (e) => {
  gameState.update((state) => ({
    ...state,
    lockedParticipantIds: addLocked(state.lockedParticipantIds, e.detail.payload),
  }));
});

eventBus.addEventListener("full_state", (e) => {
  gameState.set(e.detail.snapshot);  // remplacement intégral, jamais de fusion partielle
});
// ... un abonnement par event_type consommé par le store
```

C'est un miroir en lecture de la logique serveur, jamais une source de décision : le serveur a déjà tranché avant de diffuser, le store ne fait que refléter. Chaque composant consomme `gameState` déjà à jour, jamais les messages bruts directement — ça évite que 5 apps réimplémentent chacune leur propre logique d'interprétation, avec le risque de divergence que ça comporte.

## 6. Composants partagés (`packages/shared/components`)

| Composant | Rôle | Apps qui l'utilisent |
| --- | --- | --- |
| `JoinScreen.svelte` | Écran `username` + nom → appel `/api/auth/join/` | Joueur, Animateur, Écran TV, Opérateur |
| `GridView.svelte` | Rendu de la grille 48 cases, avec prop `viewMode: "player" \| "presenter" \| "tv" \| "reveal"` qui contrôle ce qui est visible (cases neutres vs types révélés) | Joueur, Animateur, Écran TV, Manager (supervision) |
| `Cell.svelte` | Une case individuelle (couleur selon type/état), utilisé par `GridView` | (interne à GridView) |
| `QuestionCard.svelte` | Affichage question + propositions, avec `readonly` (Écran TV) ou interactif (Joueur) | Joueur, Écran TV |
| `ScoreBoard.svelte` | Scores des deux participants, avec prop `size: "compact" \| "broadcast"` | Joueur, Animateur, Écran TV, Manager |
| `Timer.svelte` | Chrono synchronisé sur `server_ts` (recalage continu, jamais autoritaire côté client — cf. `04-app-joueur.md` §3) | Joueur, Écran TV |
| `LockOverlay.svelte` | Superposition d'état verrouillé (cf. `03-protocole-websocket.md` §6) | Joueur |
| `ConnectionBadge.svelte` | Indicateur discret d'état de connexion WebSocket (cf. §3) | Toutes |
| `EventLogViewer.svelte` | Défilement des derniers `GameEvent` bruts, abonné directement au bus (§4) | Manager (supervision) |

## 7. Ce qui n'est PAS partagé

- **Manager (config amont)** : écrans d'upload de questions, configuration de grille, gestion des lots — spécifiques, pas de logique de jeu live à ce stade, pas de composants réutilisés depuis `shared`.
- **Opérateur** : multivision des écrans TV, pupitre d'effets — spécifiques à ce rôle, aucun autre app n'en a besoin.
- **Animateur** : boutons de contrôle (démarrer, révéler question, verrouiller, pause pub) — la logique métier reste locale à l'app `presenter`, seuls les composants d'affichage (`GridView`, `ScoreBoard`) sont partagés.

## 8. Style et design tokens

Vu que l'Écran TV sert potentiellement d'habillage broadcast (injection régie via navigateur, cf. discussion stack frontend), `packages/shared` inclut un fichier de design tokens (couleurs, tailles de police, espacements) cohérent entre toutes les apps, mais avec une variante `broadcast` (fonds transparents pour le keying, tailles de police plus grandes pour la lecture caméra) activée uniquement dans l'app `tv` via une classe CSS ou un thème Svelte dédié — les tablettes de plateau (Joueur, Animateur) restent sur le thème standard, optimisé pour un usage tactile rapproché plutôt que pour une lecture à distance.
