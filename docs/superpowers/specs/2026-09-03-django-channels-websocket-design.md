# Configuration WebSocket avec Django Channels — apps/backend

Date: 2026-09-03
Statut: Approuvé

## Contexte

`apps/backend` est un projet Django 6.0.8 servi en production via `gunicorn` +
`uvicorn_worker.UvicornWorker` sur `config.asgi:application` (déjà ASGI-first,
voir `entrypoint.sh`). Redis est déjà provisionné (`docker-compose-dev.yml`,
service `redis`) et utilisé comme broker/backend Celery via `REDIS_URL`
(`config/settings/base.py`).

Aucune configuration WebSocket n'existe actuellement dans le repo : pas de
dépendance `channels`/`channels-redis`, pas de consumer, pas de routing ASGI
au-delà de `get_asgi_application()`. Cette spec couvre la mise en place from
scratch de l'infrastructure WebSocket, avec un consumer de démonstration pour
valider que la connexion fonctionne de bout en bout.

Hors scope : tout consumer métier (jeu en direct, notifications
games/challenges/grid). Cette spec pose uniquement la fondation ; les futurs
consumers métier viendront dans des tickets séparés et brancheront leurs
`websocket_urlpatterns` sur le routing mis en place ici.

## Dépendances

Ajout à `dependencies` dans `pyproject.toml` :

- `channels==4.3.2`
- `channels-redis==4.3.0`

Ajout à `dependency-groups.dev` :

- `pytest-asyncio==1.4.0` (nécessaire pour écrire des tests `async def` sur le
  consumer avec pytest-django ; le projet n'a pas de support async de test
  aujourd'hui)

Pas de `daphne` : `gunicorn` + `UvicornWorker` gère déjà HTTP et WebSocket via
ASGI, inutile d'ajouter un second serveur ASGI.

## Settings

### `config/settings/base.py`

- Ajouter `"channels"` à `THIRD_PARTY_APPS`.
- Ajouter `"core.realtime.apps.RealtimeConfig"` à `LOCAL_APPS`.
- Ajouter `ASGI_APPLICATION = "config.asgi.application"` juste après
  `WSGI_APPLICATION` (section URLS). Les deux restent définis : `manage.py`
  et les commandes de management utilisent encore WSGI/le routeur Django
  classique en interne, seul `config.asgi:application` sert de point
  d'entrée process.
- Ajouter un bloc `CHANNEL_LAYERS`, juste après la définition de `REDIS_URL`
  (section où `REDIS_URL`/`REDIS_SSL` sont déjà définis), réutilisant la même
  variable :

  ```python
  CHANNEL_LAYERS = {
      "default": {
          "BACKEND": "channels_redis.core.RedisChannelLayer",
          "CONFIG": {
              "hosts": [REDIS_URL],
          },
      },
  }
  ```

### `config/settings/test.py`

Override en fin de fichier pour éviter toute dépendance Redis dans les tests
unitaires :

```python
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}
```

## Nouvelle app `core/realtime/`

Nouvelle app Django dédiée à l'infrastructure temps réel, indépendante des
apps métier (`games`, `challenges`, `grid`) pour éviter tout couplage/import
circulaire futur.

```
core/realtime/
  __init__.py
  apps.py
  consumers.py
  routing.py
  tests.py
```

- `apps.py` :

  ```python
  from django.apps import AppConfig


  class RealtimeConfig(AppConfig):
      name = "core.realtime"
  ```

- `consumers.py` : un `PingConsumer(AsyncWebsocketConsumer)` minimal qui
  accepte la connexion et renvoie `f"pong: {message}"` pour tout message
  texte reçu. Sert uniquement à valider la chaîne ASGI → routing →
  channel layer → consumer.

- `routing.py` :

  ```python
  from django.urls import path

  from core.realtime.consumers import PingConsumer

  websocket_urlpatterns = [
      path("ws/ping/", PingConsumer.as_asgi()),
  ]
  ```

## ASGI (`config/asgi.py`)

Remplacer l'appel direct à `get_asgi_application()` par un
`ProtocolTypeRouter` qui distingue HTTP et WebSocket :

```python
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

django_asgi_app = get_asgi_application()

from core.realtime.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(
            AuthMiddlewareStack(URLRouter(websocket_urlpatterns))
        ),
    }
)
```

`get_asgi_application()` doit être appelé avant tout import importable de
modèles/consumers (contrainte Channels/Django standard), d'où l'ordre des
imports ci-dessus.

`AllowedHostsOriginValidator` réutilise `ALLOWED_HOSTS` déjà défini dans les
settings — pas de nouvelle variable à introduire.

## Tests

`core/realtime/tests.py` : test `pytest-django` + `pytest-asyncio` utilisant
`channels.testing.WebsocketCommunicator` directement sur
`PingConsumer.as_asgi()` (pas besoin de passer par tout le
`ProtocolTypeRouter` pour ce test unitaire) :

- connexion acceptée (`connected is True`)
- envoi d'un message texte → réception de `pong: <message>`
- déconnexion propre

## Erreurs / cas limites

- Si `REDIS_URL` n'est pas joignable en dev/prod, `channels_redis` lèvera une
  erreur de connexion au premier `group_send`/`group_add` — comportement
  attendu, identique à celui déjà en place pour Celery/cache avec le même
  Redis.
- `AllowedHostsOriginValidator` rejette les connexions dont l'en-tête
  `Origin` ne correspond pas à `ALLOWED_HOSTS` — comportement de sécurité
  standard, pas de configuration additionnelle nécessaire pour cette spec.

## Validation

- `uv sync` pour installer les nouvelles dépendances.
- `pytest core/realtime/tests.py` doit passer.
- `python manage.py check` doit passer (valide le chargement de
  `INSTALLED_APPS`/settings).
- Vérification manuelle optionnelle en local avec un client WebSocket sur
  `ws://localhost:8000/ws/ping/` une fois le serveur de dev lancé.
