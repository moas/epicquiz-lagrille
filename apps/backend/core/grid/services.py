"""Transactional commands for preparing a grid from confirmed client previews."""

from __future__ import annotations

import random
from collections import Counter
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction

from core.challenges.models import Challenge
from core.games.models import Episode
from core.games.models import EpisodeQuestion
from core.games.models import SpecialAttribute
from core.games.selectors import eligible_questions_for_episode

from .models import Cell
from .models import CellAttribute
from .models import Grid

EPISODE_NOT_PENDING = "This episode is no longer pending."
GRID_ALREADY_EXISTS = "This episode already has a grid."
CHALLENGES_REQUIRED = "Challenges must be dispatched before attributes."
GRID_REQUIRED = "A grid is required before attributes can be dispatched."


def _configuration_error(message: str) -> None:
    raise ValidationError({"assignments": message})


def _validate_challenge_assignments(
    *,
    assignments: list[dict[str, Any]],
    cell_count: int,
    playable_count: int,
) -> tuple[list[int], list[Any]]:
    positions = [assignment["position"] for assignment in assignments]
    question_ids = [assignment["question_id"] for assignment in assignments]
    if len(assignments) != playable_count:
        _configuration_error("Every playable cell must receive exactly one question.")
    if len(set(positions)) != len(positions):
        _configuration_error("A cell cannot receive more than one question.")
    if any(position >= cell_count for position in positions):
        _configuration_error("One of the selected cells is outside the grid.")
    if len(set(question_ids)) != len(question_ids):
        _configuration_error("A question cannot be used more than once.")
    return positions, question_ids


def _selected_questions_for_dispatch(*, episode: Episode, question_ids: list[Any]):
    eligible_questions = eligible_questions_for_episode(episode)
    selected_questions = list(
        eligible_questions.filter(
            episode_selections__episode=episode,
            pk__in=question_ids,
        )
        .prefetch_related("answers")
        .distinct(),
    )
    if len(selected_questions) != len(question_ids):
        _configuration_error(
            "Every dispatched question must still be selected for this episode.",
        )
    selected_ids = set(
        EpisodeQuestion.objects.filter(
            episode=episode,
            question__in=eligible_questions,
        ).values_list("question_id", flat=True),
    )
    if selected_ids != set(question_ids):
        _configuration_error(
            "The dispatch must contain all selected questions, exactly once.",
        )
    return selected_questions


def _validate_question_levels(*, config: dict[str, Any], questions: list[Any]) -> None:
    expected_levels = {
        int(level): count for level, count in config["point_distribution"].items()
    }
    dispatched_levels = Counter(question.level for question in questions)
    matches = all(
        dispatched_levels[level] == expected_levels.get(level, 0)
        for level in range(1, 6)
    )
    if not matches:
        _configuration_error(
            "The question levels no longer match the grid distribution.",
        )


@transaction.atomic
def save_challenge_dispatch(
    *,
    episode_id: Any,
    config: dict[str, Any],
    assignments: list[dict[str, Any]],
) -> Grid:
    """Create the grid and its challenges from a confirmed random preview."""
    episode = Episode.objects.select_for_update().get(pk=episode_id)
    if episode.state != Episode.State.PENDING:
        raise ValidationError(EPISODE_NOT_PENDING)
    if Grid.objects.filter(episode=episode).exists():
        raise ValidationError(GRID_ALREADY_EXISTS)

    cell_count = config["rows"] * config["columns"]
    playable_count = cell_count - config["empty_cell_count"]
    _, question_ids = _validate_challenge_assignments(
        assignments=assignments,
        cell_count=cell_count,
        playable_count=playable_count,
    )
    selected_questions = _selected_questions_for_dispatch(
        episode=episode,
        question_ids=question_ids,
    )
    _validate_question_levels(config=config, questions=selected_questions)

    x_labels = [label.strip() for label in config["coordinate_format"]["x"].split(",")]
    y_labels = [label.strip() for label in config["coordinate_format"]["y"].split(",")]
    grid = Grid.objects.create(
        episode=episode,
        rows=config["rows"],
        columns=config["columns"],
        empty_cell_count=config["empty_cell_count"],
        point_distribution=config["point_distribution"],
    )
    questions_by_id = {question.pk: question for question in selected_questions}
    challenges_by_position: dict[int, Challenge] = {}
    for assignment in assignments:
        question = questions_by_id[assignment["question_id"]]
        answers = list(question.answers.filter(is_active=True))
        challenges_by_position[assignment["position"]] = Challenge.objects.create(
            episode=episode,
            question=question,
            proposals=[answer.proposition_id for answer in answers],
            ok_answers=[
                answer.proposition_id for answer in answers if answer.is_correct
            ],
            timespan=episode.time_slot,
            gain=question.level,
        )

    Cell.objects.bulk_create(
        [
            Cell(
                grid=grid,
                x=position // config["columns"],
                y=position % config["columns"],
                name=(
                    f"{x_labels[position // config['columns']]}"
                    f"{y_labels[position % config['columns']]}"
                ),
                challenge=challenges_by_position.get(position),
            )
            for position in range(cell_count)
        ],
    )
    grid.positions_draw()
    grid.save(update_fields=["state", "modified"])
    return grid


@transaction.atomic
def save_attribute_dispatch(
    *,
    episode_id: Any,
    assignments: list[dict[str, Any]],
) -> Grid:
    """Persist a confirmed attribute preview on challenge cells only."""
    episode = Episode.objects.select_for_update().get(pk=episode_id)
    if episode.state != Episode.State.PENDING:
        raise ValidationError(EPISODE_NOT_PENDING)
    try:
        grid = Grid.objects.select_for_update().get(episode=episode)
    except Grid.DoesNotExist as error:
        raise ValidationError(GRID_REQUIRED) from error
    if grid.state != Grid.GridState.POSITIONS_DRAWN:
        raise ValidationError(CHALLENGES_REQUIRED)

    attribute_ids = [assignment["attribute_id"] for assignment in assignments]
    cell_ids = [assignment["cell_id"] for assignment in assignments]
    if (
        len(set(attribute_ids)) != len(attribute_ids)
        or len(set(cell_ids)) != len(cell_ids)
    ):
        _configuration_error("Each attribute and each cell can only be used once.")

    active_attribute_ids = set(
        SpecialAttribute.objects.select_for_update()
        .filter(episode=episode, is_active=True)
        .values_list("pk", flat=True),
    )
    if active_attribute_ids != set(attribute_ids):
        _configuration_error(
            "The dispatch must contain all active attributes, exactly once.",
        )

    candidate_cell_ids = set(
        grid.cells.select_for_update()
        .filter(challenge__isnull=False)
        .values_list("pk", flat=True),
    )
    if not set(cell_ids).issubset(candidate_cell_ids):
        _configuration_error("Attributes can only be assigned to challenge cells.")

    CellAttribute.objects.bulk_create(
        [
            CellAttribute(
                cell_id=assignment["cell_id"],
                attribut_id=assignment["attribute_id"],
            )
            for assignment in assignments
        ],
    )
    grid.attributes_drawn()
    grid.save(update_fields=["state", "modified"])
    return grid


def draw_attributes(grid_id: Any) -> Grid:
    """Legacy server-side draw retained for callers outside the manager UI."""
    grid = Grid.objects.get(pk=grid_id)
    attributes = list(
        SpecialAttribute.objects.filter(
            episode=grid.episode,
            is_active=True,
        ).values_list("pk", flat=True),
    )
    cells = list(
        grid.cells.filter(challenge__isnull=False).values_list("pk", flat=True),
    )
    if len(attributes) > len(cells):
        message = "More active attributes than challenge cells."
        raise ValidationError(message)
    selected_cells = random.SystemRandom().sample(cells, k=len(attributes))
    return save_attribute_dispatch(
        episode_id=grid.episode_id,
        assignments=[
            {"cell_id": cell_id, "attribute_id": attribute_id}
            for cell_id, attribute_id in zip(selected_cells, attributes, strict=True)
        ],
    )
