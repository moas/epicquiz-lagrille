"""ASGI configuration for the EpicQuiz project."""

import os
import sys
from pathlib import Path

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

from core.realtime.middleware import DRFTokenAuthMiddleware  # noqa: E402
from core.realtime.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(
            DRFTokenAuthMiddleware(URLRouter(websocket_urlpatterns)),
        ),
    },
)
