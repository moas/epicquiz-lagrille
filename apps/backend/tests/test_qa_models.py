import pytest

from core.qa.models import Answer
from core.qa.models import Proposition
from core.qa.models import Question


@pytest.mark.django_db
def test_eligible_for_challenge_requires_an_active_correct_answer() -> None:
    eligible_question = Question.objects.create(
        label="Question éligible",
        slug="question-eligible",
    )
    inactive_proposition_question = Question.objects.create(
        label="Question avec proposition inactive",
        slug="question-proposition-inactive",
    )
    no_correct_answer_question = Question.objects.create(
        label="Question sans bonne réponse",
        slug="question-sans-bonne-reponse",
    )

    correct_proposition = Proposition.objects.create(
        answer="Bonne réponse",
        slug="bonne-reponse",
    )
    inactive_proposition = Proposition.objects.create(
        answer="Proposition inactive",
        slug="proposition-inactive",
        is_active=False,
    )
    Answer.objects.create(
        question=eligible_question,
        proposition=correct_proposition,
        is_correct=True,
    )
    Answer.objects.create(
        question=inactive_proposition_question,
        proposition=inactive_proposition,
        is_correct=True,
    )
    Answer.objects.create(
        question=no_correct_answer_question,
        proposition=correct_proposition,
        is_correct=False,
    )

    assert list(Question.objects.eligible_for_challenge()) == [eligible_question]
