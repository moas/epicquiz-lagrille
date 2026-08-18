# EpicQuiz — Architecture backend

## 1. Stack technique

| Composant | Choix | Justification |
| --- | --- | --- |
| Langage | Python 3.12+ | Requis par Django 6.0 (support 3.12/3.13/3.14) |
| Framework | Django 6.0 | Async natif (vues `async def` sans `sync_to_async`), Tasks framework intégré, `BigAutoField` par défaut |
| Serveur ASGI | Daphne ou Uvicorn | Django reste WSGI-natif pour le HTTP classique ; le WebSocket nécessite un serveur ASGI — Django ne gère pas le protocole WebSocket nativement même en 6.0 |
| Temps réel | Django Channels 4.x | Compatible Django 6.0, apporte les Consumers WebSocket + Channel Layers |
| Channel layer | Redis (instance locale, sans accès internet requis) | Nécessaire dès qu'il y a plus d'un worker ASGI ; permet le `group_send` vers tous les clients d'un épisode |
| Base de données | PostgreSQL 16+ | Transactions, `JSONField`, contraintes fortes sur l'event log |
| Tâches différées | Celery | Génération de rapport d'audit, exports, provisionnement des comptes d'épisode. Redis (déjà présent pour le channel layer) sert aussi de broker Celery, sur un index logique distinct pour ne pas mélanger les deux usages |
| API HTTP | Django REST Framework | Endpoints de configuration (import questions, création d'épisode, export) |
| Authentification (tous rôles) | `djangorestframework-authtoken` (`DRF Token`) | Un seul modèle Django (`User`, `AUTH_USER_MODEL`) pour tous les rôles ; le `Token` DRF standard fonctionne donc de façon uniforme, Manager compris — pas de modèle de token custom. Manager/Admin (`is_staff=True`) s'authentifient classiquement par mot de passe. Les comptes de plateau (joueur, animateur, écran, opérateur), provisionnés par épisode via l'entité `Participant` (rôle + contexte d'épisode, cf. `02-modele-donnees.md` §6), utilisent un flux simplifié sans mot de passe : saisie du seul `username`, le serveur émet un nouveau token en invalidant l'ancien (empêche toute double connexion simultanée sur le même compte) — détail du flux en `03-protocole-websocket.md` |
| Frontend (5 apps) | Svelte (+ Vite, sans SvelteKit SSR) | Composants légers et réutilisables entre les apps (grille, question, scores, chrono) ; réactivité adaptée à un state poussé par WebSocket ; bundle compilé sans runtime framework — important pour la fluidité d'un rendu utilisé en habillage broadcast |
| Build & service du frontend | `adapter-static` → build statique servi par nginx en conteneur | Aucune dépendance Node.js à l'exécution ; s'intègre à la stratégie de build hors-ligne (build en environnement connecté, transfert, `docker load` sur site — voir `09-deploiement-reseau-ferme.md`) |

## 2. Composants du système

Chaque appareil de plateau suit un flux en deux étapes bien distinctes :

1. **Chargement de page** (une fois, au démarrage de l'app) : nginx sert le bundle Svelte statique correspondant au rôle.
2. **Authentification + WebSocket** (ensuite, pour toute la durée de la session) : l'app dispose déjà d'un `username` (distribué par le Manager) ; elle l'envoie au serveur qui émet un token (en invalidant l'ancien, cf. §1) et ouvre la connexion WebSocket vers Django Channels. Le serveur résout alors le `User` via le token, puis le `Participant` correspondant à cet épisode (rôle, tags, ordre — cf. `02-modele-donnees.md` §6-8). nginx n'intervient plus après cette étape.

```
                    1. Chargement page (une fois)
┌──────────┐  ────────────────────────────►  ┌────────────────────┐
│ Tablette │                                  │  nginx              │
│ (rôle X) │                                  │  bundle Svelte      │
└────┬─────┘                                  └────────────────────┘
     │
     │ 2. username → token → WebSocket (toute la session)
     ▼
┌──────────────────┐        ┌───────────────┐
│ Django Channels   │◄──────►│ Redis (layer)│
│ GameConsumer /     │        └───────────────┘
│ BroadcastConsumer  │
└─────────┬──────────┘
          │ écrit / lit
┌─────────▼──────────┐
│   PostgreSQL        │
│ (event log +        │
│  projections)        │
└──────────────────────┘

┌──────────┐   HTTP authentifié mot de passe (config, export)
│ Manager  │──────────────► Django REST Framework
└──────────┘
```

- Le **GameConsumer** gère le protocole de jeu (joueurs, animateur) et diffuse aussi vers les TV en lecture.
- Un **BroadcastConsumer** séparé gère les commandes de l'Opérateur (bascule d'écran, déclenchement d'effets) — groupe WebSocket distinct, jamais mélangé au flux de jeu, même s'il écoute certains événements de jeu en lecture pour synchroniser les effets automatiques (ex. son sur case vide).
- Le **Manager** utilise l'interface HTTP classique de Django REST Framework pour la configuration amont (upload de questions, création d'épisode) avec son authentification classique par mot de passe, et une connexion WebSocket au `GameConsumer` pour la supervision live, avec un rôle qui débloque des commandes supplémentaires.

## 3. Pourquoi l'event sourcing plutôt qu'un état mutable simple

Le déroulé de partie (case → question → réponse → résolution, avec effet potentiel sur le score adverse) a trois propriétés qui rendent l'event sourcing préférable à un simple modèle d'état mis à jour en place :

1. **Audit obligatoire** — le rapport de fin de partie exige la reconstitution complète et chronologique de chaque action.
2. **Résilience** — en cas de crash du process applicatif en plein direct, l'état repart de zéro sauf si chaque étape a déjà été persistée de façon durable.
3. **Le vol de points** modifie le score d'un joueur qui n'a pas agi sur cette case — un modèle d'état mutable classique (score += X sur l'enregistrement du joueur actif) complique ce cas ; un log d'événements explicites (`points_gagnes`, `points_retires_adversaire`) le rend trivial à rejouer et à vérifier.

Le détail du modèle est dans `02-modele-donnees.md`.

## 4. Processus applicatifs (workers)

| Process | Rôle | Nombre en studio |
| --- | --- | --- |
| nginx | Sert les bundles Svelte statiques (5 apps) | 1 |
| ASGI worker (Daphne/Uvicorn) | Sert HTTP + WebSocket | 1 à 2 (un seul suffit pour un plateau ; un deuxième en warm-standby recommandé) |
| Celery worker | Traite les tâches différées : provisionnement des comptes d'épisode, génération d'export/rapport, import volumineux de questions | 1 |
| PostgreSQL | Persistance | 1 instance locale |
| Redis | Channel layer **et** broker Celery (deux usages sur la même instance, index logiques distincts) | 1 instance locale |

Aucun de ces composants ne nécessite d'accès internet — tous tournent sur le réseau local du studio (voir `09-deploiement-reseau-ferme.md` pour l'empaquetage). Le broker Celery n'a pas besoin de persistance particulière : en cas de perte du worker en plein direct, les tâches concernées (export, provisionnement) ne sont jamais sur le chemin critique du jeu — elles peuvent être relancées après coup sans impact sur le déroulé de la partie.

## 5. Sécurité en réseau fermé

Même sans accès internet, le réseau du studio n'est pas un environnement de confiance absolue (matériel Wi-Fi, tablettes grand public) :

- **Comptes de plateau sans mot de passe, sécurisés par distribution physique contrôlée.** Puisque joueur/animateur/écran/opérateur s'authentifient par simple saisie du `username` (pas de mot de passe), la sécurité ne repose plus sur un secret porté par le compte lui-même mais sur le fait que ces `username` générés aléatoirement ne sont communiqués qu'au Manager, qui les distribue physiquement aux appareils juste avant le direct. Un `username` deviné ou intercepté hors de ce canal reste théoriquement utilisable — c'est un compromis assumé pour la simplicité d'usage en studio, acceptable car le réseau est fermé et les comptes n'existent que le temps d'un épisode.
- **Un seul token actif par compte de plateau à la fois.** Toute nouvelle saisie du `username` invalide le token précédemment émis pour ce compte — empêche qu'un même compte (donc un même rôle) soit utilisé simultanément par deux appareils, par erreur ou intentionnellement.
- **Rôles vérifiés côté serveur à chaque commande**, résolus via `Participant` (jamais déduits du seul canal WebSocket ni d'une déclaration du client) — un joueur ne peut pas envoyer une commande d'animateur même s'il devine le protocole.
- **Toute commande Manager de type override est journalisée avec l'identité de l'utilisateur Django authentifié**, jamais anonyme.
