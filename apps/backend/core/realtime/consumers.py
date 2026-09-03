from channels.generic.websocket import AsyncWebsocketConsumer


class PingConsumer(AsyncWebsocketConsumer):
    """Minimal echo consumer used to validate the WebSocket wiring end to end."""

    async def connect(self):
        await self.accept()

    async def receive(self, text_data=None, bytes_data=None):
        await self.send(text_data=f"pong: {text_data}")
