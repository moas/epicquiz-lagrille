# ruff: noqa: EM101, EM102, TRY003

from dataclasses import dataclass

import yaml
from django.db import transaction
from django.utils.text import slugify

from core.qa.models import Answer
from core.qa.models import AnswerReason
from core.qa.models import Proposition
from core.qa.models import Question


class QuestionImportError(ValueError):
    pass


@dataclass(frozen=True)
class QuestionImportResult:
    imported_questions: int
    reused_propositions: int
    skipped_questions: list[str]


class QuestionYamlImporter:
    @staticmethod
    def load_yaml(yaml_file):
        try:
            return yaml.safe_load(yaml_file) or {}
        except yaml.YAMLError as error:
            message = f"Invalid YAML: {error}"
            raise QuestionImportError(message) from error

    def import_payload(self, payload):
        questions = payload.get("questions") if isinstance(payload, dict) else None
        if not isinstance(questions, list):
            raise QuestionImportError("The YAML file must contain a 'questions' list.")

        imported_questions = 0
        reused_propositions = 0
        skipped_questions = []
        with transaction.atomic():
            for index, question_data in enumerate(questions, start=1):
                question, created, reused_count = self._import_question(
                    question_data,
                    index,
                )
                reused_propositions += reused_count
                if not created:
                    skipped_questions.append(question.label)
                    continue
                imported_questions += 1

        return QuestionImportResult(
            imported_questions=imported_questions,
            reused_propositions=reused_propositions,
            skipped_questions=skipped_questions,
        )

    def _import_question(self, question_data, index):
        if not isinstance(question_data, dict):
            raise QuestionImportError(f"Question #{index} must be an object.")

        label = self._required_string(question_data, "question", index)
        question_slug = slugify(label)
        if not question_slug:
            raise QuestionImportError(
                f"Question #{index} has an invalid question value.",
            )

        existing_question = Question.objects.filter(slug=question_slug).first()
        if existing_question:
            return existing_question, False, 0

        level = self._level(question_data, index)
        answers = question_data.get("answers")
        if not isinstance(answers, list) or not answers:
            message = f"Question #{index} must contain a non-empty answers list."
            raise QuestionImportError(message)

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
            message = f"Question #{question_index} requires a non-empty '{key}'."
            raise QuestionImportError(message)
        return value

    @staticmethod
    def _level(data, question_index):
        try:
            level = int(data["level"])
        except (KeyError, TypeError, ValueError) as error:
            message = f"Question #{question_index} has an invalid level."
            raise QuestionImportError(message) from error

        if level not in Question.Level.values:
            message = f"Question #{question_index} has an invalid level."
            raise QuestionImportError(message)
        return level

    @staticmethod
    def _tags(value, question_index):
        if not isinstance(value, str):
            message = f"Question #{question_index} has invalid tags."
            raise QuestionImportError(message)
        tags = (tag.strip() for tag in value.split(";") if tag.strip())
        return list(dict.fromkeys(tags))

    @staticmethod
    def _reason(data, question_index):
        if "reason" not in data:
            return None

        reason = data["reason"]
        if not isinstance(reason, str):
            message = f"Question #{question_index} has an invalid reason."
            raise QuestionImportError(message)
        return reason.strip()

    @staticmethod
    def _proposition(answer_data, question_index, answer_index):
        if not isinstance(answer_data, dict):
            message = (
                f"Answer #{answer_index} of question #{question_index} must be "
                "an object."
            )
            raise QuestionImportError(message)

        answer = QuestionYamlImporter._required_string(
            answer_data,
            "answer",
            question_index,
        )
        if not isinstance(answer_data.get("is_correct"), bool):
            message = (
                f"Answer #{answer_index} of question #{question_index} requires a "
                "boolean 'is_correct'."
            )
            raise QuestionImportError(message)

        proposition, created = Proposition.objects.get_or_create(
            slug=slugify(answer),
            defaults={"answer": answer},
        )
        return proposition, not created
