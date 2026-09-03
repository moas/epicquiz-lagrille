from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from core.users.models import User


def user_with_game_participant(**kwargs):
    user = User(**kwargs)
    user._state.fields_cache["game_participant"] = object()  # noqa: SLF001
    return user


def add_drf_token(user):
    user._state.fields_cache["auth_token"] = object()  # noqa: SLF001
    return user


def test_user_name():
    user = User(name="Ada Lovelace")

    assert user.name == "Ada Lovelace"


def test_user_last_ping_defaults_to_none():
    user = User()

    assert user.last_ping is None


@pytest.mark.parametrize(
    ("seconds_since_last_ping", "expected_status"),
    [
        (0, User.PresenceStatus.OK),
        (29, User.PresenceStatus.OK),
        (30, User.PresenceStatus.WARNING),
        (60, User.PresenceStatus.WARNING),
        (61, User.PresenceStatus.CRITICAL),
    ],
)
def test_user_presence_status_from_last_ping(
    seconds_since_last_ping,
    expected_status,
):
    now = timezone.now()
    user = user_with_game_participant(
        last_ping=now - timedelta(seconds=seconds_since_last_ping),
    )

    with patch("core.users.models.timezone.now", return_value=now):
        assert user.presence_status == expected_status


def test_game_participant_without_ping_and_token_has_critical_presence_status():
    user = user_with_game_participant()
    add_drf_token(user)

    assert user.presence_status == User.PresenceStatus.CRITICAL


def test_game_participant_without_ping_or_token_has_ok_presence_status():
    user = user_with_game_participant()

    assert user.presence_status == User.PresenceStatus.OK


def test_user_without_game_participant_has_no_presence_status():
    user = User(last_ping=timezone.now())

    assert user.presence_status is None
