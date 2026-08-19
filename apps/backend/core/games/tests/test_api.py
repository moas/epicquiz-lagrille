from http import HTTPStatus

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from core.games.models import Episode
from core.games.models import Participant
from core.games.models import QueryConfig
from core.helpers.functional import USERNAME_ALPHABET
from core.helpers.functional import generate_username
from core.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db
USERNAME_SIZE = 6


@pytest.fixture
def api_client():
    return APIClient()


def test_staff_can_create_update_and_delete_episode(api_client):
    staff_user = UserFactory.create(is_staff=True)
    api_client.force_authenticate(staff_user)

    create_response = api_client.post(
        reverse("api:episode-list"),
        {"title": "Épisode 1", "time_slot": 20},
    )

    assert create_response.status_code == HTTPStatus.CREATED
    episode = Episode.objects.get(pk=create_response.data["id"])

    update_response = api_client.patch(
        reverse("api:episode-detail", kwargs={"pk": episode.pk}),
        {"title": "Finale"},
    )

    assert update_response.status_code == HTTPStatus.OK
    episode.refresh_from_db()
    assert episode.title == "Finale"

    delete_response = api_client.delete(
        reverse("api:episode-detail", kwargs={"pk": episode.pk}),
    )

    assert delete_response.status_code == HTTPStatus.NO_CONTENT
    assert not Episode.objects.filter(pk=episode.pk).exists()


def test_non_staff_cannot_manage_episodes(api_client):
    user = UserFactory.create()
    episode = Episode.objects.create(title="Épisode 1")
    api_client.force_authenticate(user)

    response = api_client.post(reverse("api:episode-list"), {"title": "Épisode 2"})

    assert response.status_code == HTTPStatus.FORBIDDEN

    response = api_client.patch(
        reverse("api:episode-detail", kwargs={"pk": episode.pk}),
        {"title": "Finale"},
    )

    assert response.status_code == HTTPStatus.FORBIDDEN

    url = reverse("api:episode-detail", kwargs={"pk": episode.pk})
    response = api_client.delete(url)

    assert response.status_code == HTTPStatus.FORBIDDEN


def test_generate_username_uses_readable_characters():
    username = generate_username(USERNAME_SIZE)

    assert len(username) == USERNAME_SIZE
    assert set(username) <= set(USERNAME_ALPHABET)
    assert not set(username) & {"0", "O", "I", "L", "o", "i", "l"}


def test_staff_can_manage_episode_participants(api_client):
    staff_user = UserFactory.create(is_staff=True)
    episode = Episode.objects.create(title="Épisode 1")
    api_client.force_authenticate(staff_user)
    participants_url = reverse("api:episode-participants", kwargs={"pk": episode.pk})

    create_response = api_client.post(
        participants_url,
        {"name": "Léon Kali", "role": Participant.Role.PLAYER, "tags": ["red"]},
    )

    assert create_response.status_code == HTTPStatus.CREATED
    participant = episode.participants.get(pk=create_response.data["id"])
    assert participant.user.name == "Léon Kali"
    assert len(participant.user.username) == USERNAME_SIZE

    participant_url = reverse(
        "api:episode-participant",
        kwargs={"pk": episode.pk, "participant_id": participant.pk},
    )
    update_response = api_client.patch(participant_url, {"name": "Léon K."})

    assert update_response.status_code == HTTPStatus.OK
    participant.user.refresh_from_db()
    assert participant.user.name == "Léon K."

    delete_response = api_client.delete(participant_url)

    assert delete_response.status_code == HTTPStatus.NO_CONTENT
    participant.refresh_from_db()
    assert not participant.is_active


def test_staff_can_manage_episode_query_configs(api_client):
    staff_user = UserFactory.create(is_staff=True)
    episode = Episode.objects.create(title="Épisode 1")
    api_client.force_authenticate(staff_user)
    query_configs_url = reverse("api:episode-query-configs", kwargs={"pk": episode.pk})

    create_response = api_client.post(
        query_configs_url,
        {
            "mode": QueryConfig.Mode.SELECT,
            "join": QueryConfig.Join.AND,
            "tags": ["culture"],
            "level": [1, 2],
        },
    )

    assert create_response.status_code == HTTPStatus.CREATED
    query_config = episode.queries_config.get(pk=create_response.data["id"])
    assert query_config.tags == ["culture"]

    list_response = api_client.get(query_configs_url)

    assert list_response.status_code == HTTPStatus.OK
    assert len(list_response.data) == 1

    query_config_url = reverse(
        "api:episode-query-config",
        kwargs={"pk": episode.pk, "query_config_id": query_config.pk},
    )
    update_response = api_client.patch(
        query_config_url,
        {"join": QueryConfig.Join.OR},
    )

    assert update_response.status_code == HTTPStatus.OK
    query_config.refresh_from_db()
    assert query_config.join == QueryConfig.Join.OR

    delete_response = api_client.delete(query_config_url)

    assert delete_response.status_code == HTTPStatus.NO_CONTENT
    assert not QueryConfig.objects.filter(pk=query_config.pk).exists()
