# ruff: noqa: EM101, EM102, TRY003

from pathlib import Path

import yaml
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.db import transaction
from django.utils.text import slugify

from core.qa.models import Answer
from core.qa.models import AnswerReason
from core.qa.models import Proposition
from core.qa.models import Question


class Command(BaseCommand):
    help = "Load questions and propositions from a YAML file."

    def add_arguments(self, parser):
        parser.add_argument("path", type=Path, help="Path to the YAML file to import.")

    def handle(self, *args, **options):
        path = options["path"]
        payload = self._load_yaml(path)
        questions = payload.get("questions") if isinstance(payload, dict) else None
        if not isinstance(questions, list):
            raise CommandError("The YAML file must contain a 'questions' list.")

        imported_questions = 0
        reused_propositions = 0
        with transaction.atomic():
            for index, question_data in enumerate(questions, start=1):
                question, created, reused_count = self._load_question(
                    question_data,
                    index,
                )
                reused_propositions += reused_count
                if not created:
                    self.stderr.write(
                        self.style.WARNING(
                            "Question already exists and was skipped: "
                            f"{question.label}",
                        ),
                    )
                    continue
                imported_questions += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Imported {imported_questions} question(s); "
                f"reused {reused_propositions} proposition(s).",
            ),
        )

    @staticmethod
    def _load_yaml(path):
        if not path.is_file():
            raise CommandError(f"File not found: {path}")

        try:
            with path.open(encoding="utf-8") as yaml_file:
                return yaml.safe_load(yaml_file) or {}
        except yaml.YAMLError as error:
            raise CommandError(f"Invalid YAML: {error}") from error

    def _load_question(self, question_data, index):
        if not isinstance(question_data, dict):
            raise CommandError(f"Question #{index} must be an object.")

        label = self._required_string(question_data, "question", index)
        question_slug = slugify(label)
        if not question_slug:
            raise CommandError(f"Question #{index} has an invalid question value.")

        existing_question = Question.objects.filter(slug=question_slug).first()
        if existing_question:
            return existing_question, False, 0

        level = self._level(question_data, index)
        answers = question_data.get("answers")
        if not isinstance(answers, list) or not answers:
            raise CommandError(
                f"Question #{index} must contain a non-empty answers list.",
            )

        question = Question.objects.create(
            label=label,
            slug=question_slug,
            level=level,
            tags=self._tags(question_data.get("tags", ""), index),
        )
        reason = self._reason(question_data, index)
        if reason is not None:
            AnswerReason.objects.create(question=question, content=reason)

        reused_propositions = 0
        for answer_index, answer_data in enumerate(answers, start=1):
            proposition, reused = self._proposition(answer_data, index, answer_index)
            reused_propositions += reused
            Answer.objects.get_or_create(
                question=question,
                proposition=proposition,
                defaults={"is_correct": answer_data["is_correct"]},
            )

        return question, True, reused_propositions

    @staticmethod
    def _required_string(data, key, question_index):
        value = data.get(key)
        if not isinstance(value, str) or not (value := value.strip()):
            raise CommandError(
                f"Question #{question_index} requires a non-empty '{key}'.",
            )
        return value

    @staticmethod
    def _level(data, question_index):
        try:
            level = int(data["level"])
        except (KeyError, TypeError, ValueError) as error:
            raise CommandError(
                f"Question #{question_index} has an invalid level.",
            ) from error

        if level not in Question.Level.values:
            raise CommandError(f"Question #{question_index} has an invalid level.")
        return level

    @staticmethod
    def _tags(value, question_index):
        if not isinstance(value, str):
            raise CommandError(f"Question #{question_index} has invalid tags.")
        tags = (tag.strip() for tag in value.split(";") if tag.strip())
        return list(dict.fromkeys(tags))

    @staticmethod
    def _reason(data, question_index):
        if "reason" not in data:
            return None

        reason = data["reason"]
        if not isinstance(reason, str):
            raise CommandError(f"Question #{question_index} has an invalid reason.")
        return reason.strip()

    @staticmethod
    def _proposition(answer_data, question_index, answer_index):
        if not isinstance(answer_data, dict):
            raise CommandError(
                f"Answer #{answer_index} of question #{question_index} must be "
                "an object.",
            )
        answer = Command._required_string(answer_data, "answer", question_index)
        if not isinstance(answer_data.get("is_correct"), bool):
            raise CommandError(
                f"Answer #{answer_index} of question #{question_index} requires "
                "a boolean 'is_correct'.",
            )

        proposition, created = Proposition.objects.get_or_create(
            slug=slugify(answer),
            defaults={"answer": answer},
        )
        return proposition, not created
