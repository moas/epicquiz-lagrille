from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import timezone

from core.realtime.middleware import DRF_TOKEN_SUBPROTOCOL

UNAUTHORIZED_CLOSE_CODE = 4401


@database_sync_to_async
def update_last_ping(user):
    """Persist the time at which an authenticated user sent a heartbeat."""

    user.last_ping = timezone.now()
    user.save(update_fields=["last_ping"])


class AuthenticatedWebsocketConsumer(AsyncWebsocketConsumer):
    """Base consumer that only accepts authenticated DRF token clients."""

    async def connect(self):
        if not self.scope["user"].is_authenticated:
            await self.close(code=UNAUTHORIZED_CLOSE_CODE)
            return

        await self.accept(subprotocol=DRF_TOKEN_SUBPROTOCOL)


class PingConsumer(AuthenticatedWebsocketConsumer):
    """Heartbeat consumer used to track authenticated participant presence."""

    async def receive(self, text_data=None, bytes_data=None):
        await update_last_ping(self.scope["user"])
        await self.send(text_data="pong")
