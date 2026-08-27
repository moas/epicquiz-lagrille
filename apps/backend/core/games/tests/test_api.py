from http import HTTPStatus

import pytest
from django.db import IntegrityError
from django.urls import reverse
from rest_framework.test import APIClient

from core.challenges.models import Challenge
from core.games.models import Episode
from core.games.models import EpisodeQuestion
from core.games.models import Participant
from core.games.models import QueryConfig
from core.games.models import StealAttribute
from core.grid.models import Cell
from core.grid.models import CellAttribute
from core.grid.models import Grid
from core.helpers.functional import USERNAME_ALPHABET
from core.helpers.functional import generate_username
from core.qa.models import Answer
from core.qa.models import Proposition
from core.qa.models import Question
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
    assert Episode.objects.get(pk=episode.pk).title == "Finale"

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


def test_staff_can_list_and_filter_episodes(api_client):
    staff_user = UserFactory.create(is_staff=True)
    matching_episode = Episode.objects.create(title="Quiz de rentrée")
    inactive_episode = Episode.objects.create(
        title="Quiz de rentrée archivé",
        is_active=False,
    )
    started_episode = Episode.objects.create(title="Quiz en direct")
    Episode.objects.filter(pk=started_episode.pk).update(state=Episode.State.START)
    api_client.force_authenticate(staff_user)

    response = api_client.get(
        reverse("api:episode-list"),
        {
            "state": Episode.State.PENDING,
            "is_active": "true",
            "search": "rentrée",
        },
    )

    assert response.status_code == HTTPStatus.OK
    assert response.data["count"] == 1
    assert [episode["id"] for episode in response.data["results"]] == [
        str(matching_episode.pk),
    ]
    assert str(inactive_episode.pk) not in [
        episode["id"] for episode in response.data["results"]
    ]


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
    assert not Participant.objects.filter(pk=participant.pk).exists()


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


def test_staff_can_select_questions_matching_episode_rules(api_client):
    staff_user = UserFactory.create(is_staff=True)
    episode = Episode.objects.create(title="Épisode 1")
    matching_question = Question.objects.create(
        label="Question culture",
        slug="question-culture",
        level=Question.Level.STONE,
        tags=["culture"],
    )
    non_matching_question = Question.objects.create(
        label="Question sport",
        slug="question-sport",
        level=Question.Level.STONE,
        tags=["sport"],
    )
    QueryConfig.objects.create(
        episode=episode,
        mode=QueryConfig.Mode.SELECT,
        join=QueryConfig.Join.AND,
        tags=["culture"],
        level=[Question.Level.STONE],
    )
    api_client.force_authenticate(staff_user)
    questions_url = reverse("api:episode-questions", kwargs={"pk": episode.pk})

    list_response = api_client.get(questions_url)

    assert list_response.status_code == HTTPStatus.OK
    assert list_response.data["eligible_count"] == 1
    assert list_response.data["selected_count"] == 0
    assert list_response.data["results"][0]["id"] == str(matching_question.pk)
    assert not list_response.data["results"][0]["is_selected"]

    create_response = api_client.post(
        questions_url,
        {"question_id": str(matching_question.pk)},
    )

    assert create_response.status_code == HTTPStatus.CREATED
    assert EpisodeQuestion.objects.filter(
        episode=episode,
        question=matching_question,
    ).exists()

    invalid_response = api_client.post(
        questions_url,
        {"question_id": str(non_matching_question.pk)},
    )

    assert invalid_response.status_code == HTTPStatus.BAD_REQUEST

    selected_response = api_client.get(questions_url)
    assert selected_response.data["selected_count"] == 1
    assert selected_response.data["results"][0]["is_selected"]


def test_episode_question_pool_uses_the_library_without_rules(api_client):
    staff_user = UserFactory.create(is_staff=True)
    episode = Episode.objects.create(title="Épisode 1")
    question = Question.objects.create(
        label="Question sans règle",
        slug="question-sans-regle",
        level=Question.Level.WOOD,
    )
    api_client.force_authenticate(staff_user)

    response = api_client.get(
        reverse("api:episode-questions", kwargs={"pk": episode.pk}),
    )

    assert response.status_code == HTTPStatus.OK
    assert response.data["eligible_count"] == 1
    assert response.data["results"][0]["id"] == str(question.pk)


def test_staff_can_manage_episode_steal_attributes(api_client):
    staff_user = UserFactory.create(is_staff=True)
    episode = Episode.objects.create(title="Épisode 1")
    api_client.force_authenticate(staff_user)
    attributes_url = reverse("api:episode-steal-attributes", kwargs={"pk": episode.pk})

    create_response = api_client.post(attributes_url)

    assert create_response.status_code == HTTPStatus.CREATED
    attribute = StealAttribute.objects.get(pk=create_response.data["id"])
    assert attribute.episode == episode

    list_response = api_client.get(attributes_url)

    assert list_response.status_code == HTTPStatus.OK
    assert len(list_response.data) == 1

    attribute_url = reverse(
        "api:episode-steal-attribute",
        kwargs={"pk": episode.pk, "attribute_id": attribute.pk},
    )
    update_response = api_client.patch(attribute_url, {"is_active": False})

    assert update_response.status_code == HTTPStatus.OK
    attribute.refresh_from_db()
    assert not attribute.is_active

    delete_response = api_client.delete(attribute_url)

    assert delete_response.status_code == HTTPStatus.NO_CONTENT
    assert not StealAttribute.objects.filter(pk=attribute.pk).exists()


def test_staff_creates_grid_cells_from_configured_coordinates(api_client):
    staff_user = UserFactory.create(is_staff=True)
    episode = Episode.objects.create(
        title="Épisode 1",
        metadata={
            "grid_config": {
                "rows": 2,
                "columns": 3,
                "empty_cell_count": 1,
                "point_distribution": {"100": 5},
                "coordinate_format": {
                    "x": "A,B",
                    "y": "0,1,2",
                },
            },
        },
    )
    api_client.force_authenticate(staff_user)

    response = api_client.post(reverse("api:episode-grid", kwargs={"pk": episode.pk}))

    assert response.status_code == HTTPStatus.CREATED
    grid = Grid.objects.get(episode=episode)
    assert list(
        grid.cells.order_by("x", "y").values_list("x", "y", "name"),
    ) == [
        (0, 0, "A0"),
        (0, 1, "A1"),
        (0, 2, "A2"),
        (1, 0, "B0"),
        (1, 1, "B1"),
        (1, 2, "B2"),
    ]

    with pytest.raises(IntegrityError):
        Cell.objects.create(grid=grid, x=1, y=0, name="A0")


def test_grid_configuration_requires_one_label_per_coordinate(api_client):
    staff_user = UserFactory.create(is_staff=True)
    api_client.force_authenticate(staff_user)

    response = api_client.post(
        reverse("api:episode-list"),
        {
            "title": "Épisode 1",
            "metadata": {
                "grid_config": {
                    "rows": 2,
                    "columns": 2,
                    "empty_cell_count": 0,
                    "point_distribution": {"100": 4},
                    "coordinate_format": {"x": "A", "y": "0,1"},
                },
            },
        },
        format="json",
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert "coordinate_format" in response.data["metadata"]["grid_config"]


def test_staff_can_confirm_challenge_and_attribute_dispatches(api_client):
    staff_user = UserFactory.create(is_staff=True)
    episode = Episode.objects.create(
        title="Épisode 1",
        metadata={
            "grid_config": {
                "rows": 1,
                "columns": 2,
                "empty_cell_count": 0,
                "point_distribution": {"1": 1, "2": 1, "3": 0, "4": 0, "5": 0},
                "coordinate_format": {"x": "A", "y": "1,2"},
            },
        },
    )
    questions = [
        Question.objects.create(
            label=f"Question {level}",
            slug=f"question-{level}",
            level=level,
            tags=["dispatch"],
        )
        for level in (Question.Level.WOOD, Question.Level.STONE)
    ]
    for question in questions:
        proposition = Proposition.objects.create(
            answer=f"Réponse {question.level}",
            slug=f"reponse-{question.level}",
        )
        Answer.objects.create(
            question=question,
            proposition=proposition,
            is_correct=True,
        )
        EpisodeQuestion.objects.create(episode=episode, question=question)
    extra_question = Question.objects.create(
        label="Question en réserve",
        slug="question-en-reserve",
        level=Question.Level.WOOD,
        tags=["dispatch"],
    )
    extra_proposition = Proposition.objects.create(
        answer="Réponse en réserve",
        slug="reponse-en-reserve",
    )
    Answer.objects.create(
        question=extra_question,
        proposition=extra_proposition,
        is_correct=True,
    )
    EpisodeQuestion.objects.create(episode=episode, question=extra_question)
    QueryConfig.objects.create(
        episode=episode,
        mode=QueryConfig.Mode.SELECT,
        level=[Question.Level.WOOD, Question.Level.STONE],
    )
    StealAttribute.objects.create(episode=episode)
    api_client.force_authenticate(staff_user)

    challenge_response = api_client.post(
        reverse("api:episode-challenge-dispatch", kwargs={"pk": episode.pk}),
        {
            "assignments": [
                {"position": 0, "question_id": str(questions[0].pk)},
                {"position": 1, "question_id": str(questions[1].pk)},
            ],
        },
        format="json",
    )

    assert challenge_response.status_code == HTTPStatus.CREATED
    grid = Grid.objects.get(episode=episode)
    assert grid.state == Grid.GridState.POSITIONS_DRAWN
    challenges = Challenge.objects.filter(episode=episode).order_by("gain")
    assert challenges.count() == len(questions)
    assert list(challenges.values_list("gain", flat=True)) == [1, 2]
    assert not challenges.filter(question=extra_question).exists()

    attribute = StealAttribute.objects.get(episode=episode)
    challenge_cell = grid.cells.filter(challenge__isnull=False).first()
    attribute_response = api_client.post(
        reverse("api:episode-attribute-dispatch", kwargs={"pk": episode.pk}),
        {
            "assignments": [
                {
                    "cell_id": str(challenge_cell.pk),
                    "attribute_id": str(attribute.pk),
                },
            ],
        },
        format="json",
    )

    assert attribute_response.status_code == HTTPStatus.OK
    assert (
        Grid.objects.get(pk=grid.pk).state == Grid.GridState.ATTRIBUTES_DRAWN
    )
    assert CellAttribute.objects.filter(attribut=attribute).exists()
