"""Commands for the episode question pool."""

from django.core.exceptions import ValidationError

from core.games.models import EpisodeQuestion
from core.qa.models import Question

from .selectors import eligible_questions_for_episode


def select_episode_question(*, episode, question_id):
    try:
        question = eligible_questions_for_episode(episode).get(pk=question_id)
    except Question.DoesNotExist as error:
        raise ValidationError(
            {"question_id": "This question does not match the episode rules."},
        ) from error

    selection, _ = EpisodeQuestion.objects.get_or_create(
        episode=episode,
        question=question,
    )
    return selection
