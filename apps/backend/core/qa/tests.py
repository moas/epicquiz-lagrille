from io import StringIO

import pytest
from django.core.management import call_command

from core.qa.models import Answer
from core.qa.models import AnswerReason
from core.qa.models import Proposition
from core.qa.models import Question

pytestmark = pytest.mark.django_db
QUESTION_COUNT = 2
PROPOSITION_COUNT = 3


def test_loadquery_imports_questions_and_reuses_propositions(tmp_path):
    questions_file = tmp_path / "questions.yaml"
    questions_file.write_text(
        """
questions:
  - question: Quelle est la capitale de l'Afrique du Sud ?
    level: '1'
    reason: Pretoria est la capitale administrative du pays.
    tags: domain:geography; meta:city; domain:geography
    answers:
      - answer: Pretoria
        is_correct: true
      - answer: Rabat
        is_correct: false
  - question: Quelle est la capitale du Maroc ?
    level: 1
    tags: domain:geography
    answers:
      - answer: Rabat
        is_correct: true
      - answer: Alger
        is_correct: false
""".strip(),
        encoding="utf-8",
    )

    call_command("loadquery", questions_file)

    assert Question.objects.count() == QUESTION_COUNT
    assert Proposition.objects.count() == PROPOSITION_COUNT
    question = Question.objects.get(
        label="Quelle est la capitale de l'Afrique du Sud ?",
    )
    assert question.tags == ["domain:geography", "meta:city"]
    assert AnswerReason.objects.get(question=question).content == (
        "Pretoria est la capitale administrative du pays."
    )
    assert Answer.objects.filter(question=question, is_correct=True).count() == 1


def test_loadquery_warns_and_skips_existing_questions(tmp_path):
    Question.objects.create(
        label="Question existante",
        slug="question-existante",
        level=Question.Level.WOOD,
    )
    questions_file = tmp_path / "questions.yaml"
    questions_file.write_text(
        """
questions:
  - question: Question existante
    level: 1
    tags: ''
    answers:
      - answer: Réponse
        is_correct: true
""".strip(),
        encoding="utf-8",
    )
    stderr = StringIO()

    call_command("loadquery", questions_file, stderr=stderr)

    assert "Question already exists and was skipped" in stderr.getvalue()
    assert Answer.objects.count() == 0
