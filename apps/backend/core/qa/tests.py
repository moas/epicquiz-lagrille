from http import HTTPStatus
from io import StringIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.urls import reverse
from rest_framework.test import APIClient

from core.qa.models import Answer
from core.qa.models import AnswerReason
from core.qa.models import Proposition
from core.qa.models import Question
from core.users.tests.factories import UserFactory

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


def test_staff_can_import_questions_from_yaml():
    api_client = APIClient()
    api_client.force_authenticate(UserFactory.create(is_staff=True))
    questions_file = SimpleUploadedFile(
        "questions.yaml",
        b"""
questions:
  - question: Quelle est la capitale de l'Afrique du Sud ?
    level: 1
    reason: Pretoria est la capitale administrative du pays.
    tags: domain:geography; meta:city
    answers:
      - answer: Pretoria
        is_correct: true
      - answer: Rabat
        is_correct: false
""".strip(),
        content_type="application/yaml",
    )

    response = api_client.post(
        reverse("api:qa-question-import"),
        {"file": questions_file},
        format="multipart",
    )

    assert response.status_code == HTTPStatus.CREATED
    assert response.data == {
        "imported_questions": 1,
        "reused_propositions": 0,
        "skipped_questions": [],
    }
    assert AnswerReason.objects.get().content == (
        "Pretoria est la capitale administrative du pays."
    )


def test_staff_can_manage_questions_and_propositions():
    api_client = APIClient()
    api_client.force_authenticate(UserFactory.create(is_staff=True))

    create_response = api_client.post(
        reverse("api:qa-question-list"),
        {
            "question": "Quelle est la capitale de l'Afrique du Sud ?",
            "level": Question.Level.WOOD,
            "tags": ["domain:geography"],
            "answers": [{"answer": "Pretoria", "is_correct": True}],
        },
        format="json",
    )

    assert create_response.status_code == HTTPStatus.CREATED
    question = Question.objects.get(pk=create_response.data["id"])
    pretoria_answer_id = create_response.data["answers"][0]["id"]
    propositions_url = reverse(
        "api:qa-question-propositions",
        kwargs={"pk": question.pk},
    )
    add_response = api_client.post(
        propositions_url,
        {"answer": "Rabat", "is_correct": False},
        format="json",
    )

    assert add_response.status_code == HTTPStatus.CREATED
    assert api_client.get(propositions_url).data == [
        {"id": pretoria_answer_id, "answer": "Pretoria", "is_correct": True},
        {"id": str(add_response.data["id"]), "answer": "Rabat", "is_correct": False},
    ]
    assert len(api_client.get(reverse("api:qa-proposition-list")).data) == QUESTION_COUNT

    delete_response = api_client.delete(
        reverse("api:qa-question-detail", kwargs={"pk": question.pk}),
    )

    assert delete_response.status_code == HTTPStatus.NO_CONTENT
    assert not Question.objects.filter(pk=question.pk).exists()


def test_staff_cannot_delete_a_proposition_used_by_a_question():
    question = Question.objects.create(
        label="Question",
        slug="question",
        level=Question.Level.WOOD,
    )
    proposition = Proposition.objects.create(answer="Réponse", slug="reponse")
    Answer.objects.create(question=question, proposition=proposition)
    api_client = APIClient()
    api_client.force_authenticate(UserFactory.create(is_staff=True))

    response = api_client.delete(
        reverse("api:qa-proposition-detail", kwargs={"pk": proposition.pk}),
    )

    assert response.status_code == HTTPStatus.CONFLICT
    assert Proposition.objects.filter(pk=proposition.pk).exists()
