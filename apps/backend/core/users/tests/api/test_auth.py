from http import HTTPStatus

import pytest
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from core.games.models import Episode
from core.games.models import Participant
from core.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db
TEST_PASSWORD = "correct-password"  # noqa: S105


@pytest.fixture
def api_client():
    return APIClient()


def test_staff_login_with_password_rotates_token(api_client):
    user = UserFactory.create(is_staff=True, password=TEST_PASSWORD)
    previous_token = Token.objects.create(user=user)

    response = api_client.post(
        reverse("api:auth-login"),
        {"username": user.username, "password": TEST_PASSWORD},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.data["token"] != previous_token.key
    assert Token.objects.get(user=user).key == response.data["token"]


def test_login_with_password_requires_staff(api_client):
    user = UserFactory.create(password=TEST_PASSWORD)

    response = api_client.post(
        reverse("api:auth-login"),
        {"username": user.username, "password": TEST_PASSWORD},
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST


def test_participant_login_without_password_rotates_token(api_client):
    user = UserFactory.create()
    Participant.objects.create(
        episode=Episode.objects.create(title="Episode 1"),
        user=user,
        role=Participant.Role.PLAYER,
    )
    previous_token = Token.objects.create(user=user)

    response = api_client.post(reverse("api:auth-login"), {"username": user.username})

    assert response.status_code == HTTPStatus.OK
    assert response.data["token"] != previous_token.key
    assert Token.objects.get(user=user).key == response.data["token"]


def test_login_without_password_requires_participant(api_client):
    user = UserFactory.create()

    response = api_client.post(reverse("api:auth-login"), {"username": user.username})

    assert response.status_code == HTTPStatus.BAD_REQUEST


def test_logout_revokes_user_token(api_client):
    user = UserFactory.create()
    token = Token.objects.create(user=user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    response = api_client.post(reverse("api:auth-logout"))

    assert response.status_code == HTTPStatus.NO_CONTENT
    assert not Token.objects.filter(user=user).exists()
