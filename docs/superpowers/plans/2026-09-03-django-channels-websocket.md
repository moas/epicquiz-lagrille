# Django Channels WebSocket Setup — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the base Django Channels WebSocket infrastructure in `apps/backend` — dependencies, ASGI routing, Redis-backed channel layer, and a demo `PingConsumer` proving the full chain (ASGI → routing → channel layer → consumer) works.

**Architecture:** `config/asgi.py` becomes a `ProtocolTypeRouter` splitting `http` (existing Django app) from `websocket` (Channels `AuthMiddlewareStack` + `AllowedHostsOriginValidator` + `URLRouter`). A new standalone app `core/realtime` owns the WebSocket routing table and consumers, decoupled from domain apps (`games`, `challenges`, `grid`) so future business consumers plug in without circular imports. The channel layer uses Redis in dev/prod (reusing the existing `REDIS_URL` already wired for Celery) and an in-memory backend in tests.

**Tech Stack:** Django 6.0.8, channels==4.3.2, channels-redis==4.3.0, pytest-django, pytest-asyncio==1.4.0 (new dev dep), uv, existing `gunicorn`+`uvicorn_worker` ASGI server (no new server process needed).

## Global Constraints

- Repo root: `/home/lasmo/develop/halittar/epicquiz/lagrille`; all paths below are relative to `apps/backend/` unless stated otherwise.
- Pin exact versions: `channels==4.3.2`, `channels-redis==4.3.0`, `pytest-asyncio==1.4.0` (verified current on PyPI as of 2026-09-03) — match this repo's convention of exact `==` pins in `pyproject.toml`.
- No new business/domain consumer in this plan — `core/realtime` only ships the demo `PingConsumer` plus the routing skeleton. Business consumers are future work.
- No `daphne` — the existing `gunicorn --worker-class uvicorn_worker.UvicornWorker` process already serves ASGI for both HTTP and WebSocket.
- Follow existing code conventions: `ruff` rule set includes `E` (so `E402` needs an explicit `# noqa: E402`), `I` with `lint.isort.force-single-line = true` (one import per line), `INP` (every package needs `__init__.py`).
- Tests run via `uv run pytest` (settings come from `[tool.pytest]` `addopts = ["--ds=config.settings.test", ...]` in `pyproject.toml`); test file naming must match `python_files = ["tests.py", "test_*.py"]`.
- Loading `config.settings.test` (or any settings module) requires `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` env vars to be set (django-environ raises otherwise), even though the tests in this plan never touch the database. Use dummy values, e.g. `POSTGRES_DB=lagrille POSTGRES_USER=owner POSTGRES_PASSWORD=pgPASS_ORD`.

---

## File Structure

```
apps/backend/pyproject.toml              # modify: add channels/channels-redis/pytest-asyncio deps
apps/backend/config/settings/base.py     # modify: THIRD_PARTY_APPS, LOCAL_APPS, ASGI_APPLICATION, CHANNEL_LAYERS
apps/backend/config/settings/test.py     # modify: CHANNEL_LAYERS override (in-memory)
apps/backend/config/asgi.py              # modify: ProtocolTypeRouter (http + websocket)
apps/backend/core/realtime/__init__.py   # create: empty, marks package
apps/backend/core/realtime/apps.py       # create: RealtimeConfig
apps/backend/core/realtime/consumers.py  # create: PingConsumer
apps/backend/core/realtime/routing.py    # create: websocket_urlpatterns
apps/backend/core/realtime/tests.py      # create: WebsocketCommunicator test for PingConsumer
```

---

## Task 1: Add dependencies

**Files:**
- Modify: `apps/backend/pyproject.toml`

**Interfaces:**
- Produces: `channels`, `channels_redis`, `pytest_asyncio` importable in the venv for later tasks.

- [ ] **Step 1: Add runtime dependencies**

In `apps/backend/pyproject.toml`, the `dependencies` list (starts at line 16, alphabetically sorted). Insert these two lines in alphabetical order:

```toml
  "channels==4.3.2",
  "channels-redis==4.3.0",
```

They land right after `"celery==5.6.3",` and before `"crispy-bootstrap5==2026.3",` (alphabetical: celery, channels, channels-redis, crispy-bootstrap5).

- [ ] **Step 2: Add dev dependency**

In the `[dependency-groups]` `dev` list, insert alphabetically after `"psycopg[binary]==3.3.4",` and before `"pytest==9.1.1",`:

```toml
  "pytest-asyncio==1.4.0",
```

- [ ] **Step 3: Sync the environment**

Run (from `apps/backend/`):

```bash
uv sync
```

Expected: resolves and installs `channels`, `channels-redis`, `pytest-asyncio` (and their transitive deps, e.g. `asgiref`, `msgpack`) with no errors. `uv.lock` gets updated.

- [ ] **Step 4: Verify imports**

```bash
uv run python -c "import channels, channels_redis, pytest_asyncio; print('ok')"
```

Expected output: `ok`

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "build: add django-channels, channels-redis, pytest-asyncio deps"
```

---

## Task 2: Wire settings (channel layer, ASGI_APPLICATION, installed apps)

**Files:**
- Modify: `apps/backend/config/settings/base.py:74` (WSGI_APPLICATION line), `:90-100` (THIRD_PARTY_APPS), `:102-109` (LOCAL_APPS), `:277-278` (REDIS_URL block)
- Modify: `apps/backend/config/settings/test.py`

**Interfaces:**
- Consumes: `REDIS_URL` (already defined in `base.py:277`).
- Produces: `ASGI_APPLICATION = "config.asgi.application"`, `CHANNEL_LAYERS["default"]` — consumed by `config/asgi.py` (Task 4) and by Channels' `get_channel_layer()` calls in future business code.

- [ ] **Step 1: Add `"channels"` to THIRD_PARTY_APPS**

In `apps/backend/config/settings/base.py`, `THIRD_PARTY_APPS` (line 90):

```python
THIRD_PARTY_APPS = [
    "channels",
    "polymorphic",
    "crispy_forms",
    "crispy_bootstrap5",
    "django_celery_beat",
    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
]
```

- [ ] **Step 2: Add `core.realtime` to LOCAL_APPS**

```python
LOCAL_APPS = [
    "core.users",
    "core.audit.apps.AuditConfig",
    "core.qa.apps.QaConfig",
    "core.games.apps.GamesConfig",
    "core.grid.apps.GridConfig",
    "core.challenges.apps.ChallengesConfig",
    "core.realtime.apps.RealtimeConfig",
]
```

(This app doesn't exist yet — created in Task 3. `python manage.py check` in Task 3 Step 5 is what actually proves this wiring works, since Task 2 alone can't import an app that doesn't exist yet.)

- [ ] **Step 3: Add ASGI_APPLICATION next to WSGI_APPLICATION**

At line 74, directly below `WSGI_APPLICATION`:

```python
WSGI_APPLICATION = "config.wsgi.application"
# https://channels.readthedocs.io/en/stable/topics/routing.html
ASGI_APPLICATION = "config.asgi.application"
```

- [ ] **Step 4: Add CHANNEL_LAYERS next to REDIS_URL**

At line 278, right after `REDIS_SSL = REDIS_URL.startswith("rediss://")` and before the `# Celery` comment block:

```python
REDIS_URL = env("REDIS_URL", default="redis://localhost:6379/0")
REDIS_SSL = REDIS_URL.startswith("rediss://")

# Channels
# ------------------------------------------------------------------------------
# https://channels.readthedocs.io/en/stable/topics/channel_layers.html
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [REDIS_URL],
        },
    },
}
```

- [ ] **Step 5: Override CHANNEL_LAYERS in test settings**

At the end of `apps/backend/config/settings/test.py` (after the existing `MEDIA_URL` block, replacing the `# Your stuff...` trailer comment):

```python
# Channels
# ------------------------------------------------------------------------------
# In-memory layer avoids a Redis dependency for unit tests.
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}
```

- [ ] **Step 6: Commit**

```bash
git add config/settings/base.py config/settings/test.py
git commit -m "feat: configure django-channels settings (channel layer, ASGI app)"
```

(This commit intentionally leaves `manage.py check` failing until Task 3 creates `core.realtime` — Task 3 Step 5 is the first point both changes are verified together. Do not run `manage.py check` as a gate here.)

---

## Task 3: Create `core.realtime` app with `PingConsumer` (TDD)

**Files:**
- Create: `apps/backend/core/realtime/__init__.py`
- Create: `apps/backend/core/realtime/apps.py`
- Create: `apps/backend/core/realtime/consumers.py`
- Create: `apps/backend/core/realtime/routing.py`
- Test: `apps/backend/core/realtime/tests.py`

**Interfaces:**
- Consumes: `CHANNEL_LAYERS` (Task 2) — implicitly, via Channels' consumer base classes.
- Produces: `core.realtime.consumers.PingConsumer` (class, `AsyncWebsocketConsumer` subclass, `as_asgi()` classmethod inherited) and `core.realtime.routing.websocket_urlpatterns` (list of `django.urls.path`) — both consumed by `config/asgi.py` in Task 4.

- [ ] **Step 1: Create the package skeleton**

```bash
mkdir -p apps/backend/core/realtime
touch apps/backend/core/realtime/__init__.py
```

`apps/backend/core/realtime/apps.py`:

```python
from django.apps import AppConfig


class RealtimeConfig(AppConfig):
    name = "core.realtime"
```

- [ ] **Step 2: Write the failing test**

`apps/backend/core/realtime/tests.py`:

```python
import pytest
from channels.testing import WebsocketCommunicator

from core.realtime.consumers import PingConsumer


@pytest.mark.asyncio
async def test_ping_consumer_echoes_pong():
    communicator = WebsocketCommunicator(PingConsumer.as_asgi(), "/ws/ping/")

    connected, _ = await communicator.connect()
    assert connected is True

    await communicator.send_to(text_data="hello")
    response = await communicator.receive_from()
    assert response == "pong: hello"

    await communicator.disconnect()


@pytest.mark.asyncio
async def test_ping_consumer_connects_without_sending():
    communicator = WebsocketCommunicator(PingConsumer.as_asgi(), "/ws/ping/")

    connected, _ = await communicator.connect()
    assert connected is True

    await communicator.disconnect()
```

- [ ] **Step 3: Run the test to confirm it fails**

From `apps/backend/`:

```bash
POSTGRES_DB=lagrille POSTGRES_USER=owner POSTGRES_PASSWORD=pgPASS_ORD \
  uv run pytest core/realtime/tests.py -v
```

Expected: collection error / `ModuleNotFoundError: No module named 'core.realtime.consumers'` (consumer doesn't exist yet).

- [ ] **Step 4: Implement the minimal consumer**

`apps/backend/core/realtime/consumers.py`:

```python
from channels.generic.websocket import AsyncWebsocketConsumer


class PingConsumer(AsyncWebsocketConsumer):
    """Minimal echo consumer used to validate the WebSocket wiring end to end."""

    async def connect(self):
        await self.accept()

    async def receive(self, text_data=None, bytes_data=None):
        await self.send(text_data=f"pong: {text_data}")
```

`apps/backend/core/realtime/routing.py`:

```python
from django.urls import path

from core.realtime.consumers import PingConsumer

websocket_urlpatterns = [
    path("ws/ping/", PingConsumer.as_asgi()),
]
```

- [ ] **Step 5: Verify Django can load the app (settings wiring from Task 2)**

```bash
POSTGRES_DB=lagrille POSTGRES_USER=owner POSTGRES_PASSWORD=pgPASS_ORD \
  uv run python manage.py check
```

Expected: `System check identified no issues (0 silenced).` This is the first point that proves Task 2's `LOCAL_APPS` entry (`core.realtime.apps.RealtimeConfig`) resolves correctly now that the app exists.

- [ ] **Step 6: Run the test to confirm it passes**

```bash
POSTGRES_DB=lagrille POSTGRES_USER=owner POSTGRES_PASSWORD=pgPASS_ORD \
  uv run pytest core/realtime/tests.py -v
```

Expected: both tests `PASS`. If pytest reports `async def functions are not natively supported`, it means the `pytest.mark.asyncio` marker isn't being picked up — confirm `pytest-asyncio` installed in Task 1 Step 4, and if still failing, add `asyncio_mode = "auto"` under `[tool.pytest]` in `pyproject.toml` and rerun (only add this if the explicit marker doesn't work — check the marker first).

- [ ] **Step 7: Commit**

```bash
git add core/realtime
git commit -m "feat: add core.realtime app with PingConsumer and routing"
```

---

## Task 4: Wire `config/asgi.py` to route HTTP and WebSocket

**Files:**
- Modify: `apps/backend/config/asgi.py`

**Interfaces:**
- Consumes: `core.realtime.routing.websocket_urlpatterns` (Task 3), `ASGI_APPLICATION`/`CHANNEL_LAYERS`/`ALLOWED_HOSTS` (Task 2 + existing settings).
- Produces: `application` (ASGI callable) — this is what `entrypoint.sh`'s `gunicorn config.asgi:application ... --worker-class uvicorn_worker.UvicornWorker` already serves; no change needed to `entrypoint.sh` or `Dockerfile`.

- [ ] **Step 1: Rewrite `config/asgi.py`**

Full replacement of `apps/backend/config/asgi.py`:

```python
"""ASGI configuration for the EpicQuiz project."""

import os
import sys
from pathlib import Path

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter
from channels.routing import URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

BASE_DIR = Path(__file__).resolve(strict=True).parent.parent
sys.path.append(str(BASE_DIR / "core"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

# Must run before importing anything that touches Django models/apps
# (Channels consumers, routing) — this populates the app registry.
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

Note: imports are one-per-line (`from channels.routing import ProtocolTypeRouter` / `from channels.routing import URLRouter` as separate lines) to match this repo's `lint.isort.force-single-line = true` ruff setting.

- [ ] **Step 2: Verify the ASGI app loads**

```bash
POSTGRES_DB=lagrille POSTGRES_USER=owner POSTGRES_PASSWORD=pgPASS_ORD \
  uv run python -c "
import django
django.setup()
from config.asgi import application
print(type(application).__name__)
"
```

Run from `apps/backend/` with `DJANGO_SETTINGS_MODULE=config.settings.test` also exported (since `production` settings need extra env vars like `DJANGO_SECRET_KEY`):

```bash
DJANGO_SETTINGS_MODULE=config.settings.test \
POSTGRES_DB=lagrille POSTGRES_USER=owner POSTGRES_PASSWORD=pgPASS_ORD \
  uv run python -c "
import django
django.setup()
from config.asgi import application
print(type(application).__name__)
"
```

Expected output: `ProtocolTypeRouter`

- [ ] **Step 3: Run ruff to confirm lint passes**

```bash
uv run ruff check config/asgi.py core/realtime
```

Expected: `All checks passed!`

- [ ] **Step 4: Re-run the full test suite for this feature**

```bash
POSTGRES_DB=lagrille POSTGRES_USER=owner POSTGRES_PASSWORD=pgPASS_ORD \
  uv run pytest core/realtime/tests.py -v
```

Expected: both tests still `PASS` (this task didn't touch the consumer, just confirms nothing broke).

- [ ] **Step 5: Commit**

```bash
git add config/asgi.py
git commit -m "feat: route HTTP and WebSocket protocols in config/asgi.py"
```

---

## Task 5: End-to-end manual verification (local dev)

**Files:** none (verification only)

**Interfaces:** none

- [ ] **Step 1: Start Postgres + Redis**

From the repo root (`/home/lasmo/develop/halittar/epicquiz/lagrille`):

```bash
docker compose -f docker-compose-dev.yml up -d
```

- [ ] **Step 2: Run migrations and start the dev server**

`manage.py runserver` does not serve ASGI/WebSocket, so use the same
`gunicorn`+`uvicorn_worker` command `entrypoint.sh` uses in production —
no new tooling needed. From `apps/backend/`:

```bash
DJANGO_SETTINGS_MODULE=config.settings.local \
POSTGRES_DB=lagrille POSTGRES_USER=owner POSTGRES_PASSWORD=pgPASS_ORD \
POSTGRES_HOST=localhost POSTGRES_PORT=5040 \
REDIS_URL=redis://localhost:6381/0 \
  uv run python manage.py migrate

DJANGO_SETTINGS_MODULE=config.settings.local \
POSTGRES_DB=lagrille POSTGRES_USER=owner POSTGRES_PASSWORD=pgPASS_ORD \
POSTGRES_HOST=localhost POSTGRES_PORT=5040 \
REDIS_URL=redis://localhost:6381/0 \
  uv run gunicorn config.asgi:application --bind 0.0.0.0:8000 --worker-class uvicorn_worker.UvicornWorker
```

- [ ] **Step 3: Connect a WebSocket client**

```bash
uv run python -c "
import asyncio
import websockets

async def main():
    async with websockets.connect('ws://localhost:8000/ws/ping/') as ws:
        await ws.send('hello')
        print(await ws.recv())

asyncio.run(main())
"
```

If `websockets` isn't installed, use any WebSocket CLI available (e.g. `wscat -c ws://localhost:8000/ws/ping/` then type `hello`).

Expected: connection succeeds, server replies `pong: hello`.

- [ ] **Step 4: Tear down**

```bash
docker compose -f docker-compose-dev.yml down
```

- [ ] **Step 5: No commit** — this task is manual verification only, nothing to commit.

---

## Self-Review Notes

- **Spec coverage:** dependencies (Task 1) → settings/channel layer/ASGI_APPLICATION (Task 2) → `core.realtime` app + `PingConsumer` + routing + tests (Task 3) → `config/asgi.py` ProtocolTypeRouter (Task 4) → manual end-to-end check (Task 5). All spec sections covered.
- **Type/name consistency checked:** `PingConsumer` (Task 3) matches `core.realtime.consumers.PingConsumer` imported in `routing.py` (Task 3) and referenced only indirectly via `websocket_urlpatterns` in `asgi.py` (Task 4) — names match throughout.
- **No placeholders:** all steps contain literal code/commands and expected output.
