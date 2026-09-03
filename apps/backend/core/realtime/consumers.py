from channels.generic.websocket import AsyncWebsocketConsumer

from core.realtime.middleware import DRF_TOKEN_SUBPROTOCOL

UNAUTHORIZED_CLOSE_CODE = 4401


class PingConsumer(AsyncWebsocketConsumer):
    """Minimal echo consumer used to validate the WebSocket wiring end to end."""

    async def connect(self):
        if not self.scope["user"].is_authenticated:
            await self.close(code=UNAUTHORIZED_CLOSE_CODE)
            return

        await self.accept(subprotocol=DRF_TOKEN_SUBPROTOCOL)

    async def receive(self, text_data=None, bytes_data=None):
        await self.send(text_data=f"pong: {text_data}")
