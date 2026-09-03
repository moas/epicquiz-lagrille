from unittest.mock import patch

import pytest
from channels.testing import WebsocketCommunicator

from core.realtime.consumers import PingConsumer


@pytest.fixture(autouse=True)
def skip_database_connection_cleanup():
    """Keep focused consumer tests independent from PostgreSQL."""

    async def no_op():
        return None

    with patch("channels.consumer.aclose_old_connections", new=no_op):
        yield


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
