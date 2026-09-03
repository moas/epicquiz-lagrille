from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework.authtoken.models import Token

DRF_TOKEN_SUBPROTOCOL = "drf-token"  # noqa: S105
TOKEN_SUBPROTOCOL_COUNT = 2


@database_sync_to_async
def get_user_from_token(token_key: str):
    """Return the user owning a valid DRF token, if any."""

    try:
        return Token.objects.select_related("user").get(key=token_key).user
    except Token.DoesNotExist:
        return AnonymousUser()


class DRFTokenAuthMiddleware:
    """Authenticate WebSocket scopes from the ``drf-token`` subprotocol."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        user = AnonymousUser()
        subprotocols = scope.get("subprotocols", [])

        if (
            len(subprotocols) == TOKEN_SUBPROTOCOL_COUNT
            and subprotocols[0] == DRF_TOKEN_SUBPROTOCOL
        ):
            user = await get_user_from_token(subprotocols[1])

        scope = {**scope, "user": user}
        return await self.app(scope, receive, send)
