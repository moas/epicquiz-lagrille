from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import patch

import pytest
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import AnonymousUser
from django.urls import path

from core.realtime.consumers import UNAUTHORIZED_CLOSE_CODE
from core.realtime.consumers import PingConsumer
from core.realtime.middleware import DRF_TOKEN_SUBPROTOCOL
from core.realtime.middleware import DRFTokenAuthMiddleware


@pytest.fixture(autouse=True)
def skip_database_connection_cleanup():
    """Keep focused consumer tests independent from PostgreSQL."""

    async def no_op():
        return None

    with patch("channels.consumer.aclose_old_connections", new=no_op):
        yield


def token_authenticated_application():
    return DRFTokenAuthMiddleware(
        URLRouter(
            [
                path("ws/ping/", PingConsumer.as_asgi()),
            ],
        ),
    )


@pytest.mark.asyncio
async def test_ping_consumer_echoes_pong_for_authenticated_token():
    token = "a" * 40
    application = token_authenticated_application()
    user = SimpleNamespace(is_authenticated=True)

    with patch(
        "core.realtime.middleware.get_user_from_token",
        new=AsyncMock(return_value=user),
    ) as get_user:
        communicator = WebsocketCommunicator(
            application,
            "/ws/ping/",
            subprotocols=[DRF_TOKEN_SUBPROTOCOL, token],
        )

        connected, subprotocol = await communicator.connect()
        assert connected is True
        assert subprotocol == DRF_TOKEN_SUBPROTOCOL

        await communicator.send_to(text_data="hello")
        response = await communicator.receive_from()
        assert response == "pong: hello"

        await communicator.disconnect()

    get_user.assert_awaited_once_with(token)


@pytest.mark.asyncio
async def test_ping_consumer_rejects_connection_without_token():
    application = token_authenticated_application()
    communicator = WebsocketCommunicator(application, "/ws/ping/")

    connected, close_code = await communicator.connect()
    assert connected is False
    assert close_code == UNAUTHORIZED_CLOSE_CODE


@pytest.mark.asyncio
async def test_ping_consumer_rejects_invalid_token():
    application = token_authenticated_application()
    get_user = AsyncMock(return_value=AnonymousUser())

    with patch("core.realtime.middleware.get_user_from_token", new=get_user):
        communicator = WebsocketCommunicator(
            application,
            "/ws/ping/",
            subprotocols=[DRF_TOKEN_SUBPROTOCOL, "invalid"],
        )

        connected, close_code = await communicator.connect()

    assert connected is False
    assert close_code == UNAUTHORIZED_CLOSE_CODE
    get_user.assert_awaited_once_with("invalid")
