# ruff: noqa: EM102, TRY003

from pathlib import Path

from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

from core.qa.importers import QuestionImportError
from core.qa.importers import QuestionYamlImporter


class Command(BaseCommand):
    help = "Load questions and propositions from a YAML file."

    def add_arguments(self, parser):
        parser.add_argument("path", type=Path, help="Path to the YAML file to import.")

    def handle(self, *args, **options):
        path = options["path"]
        if not path.is_file():
            raise CommandError(f"File not found: {path}")

        try:
            with path.open(encoding="utf-8") as yaml_file:
                payload = QuestionYamlImporter.load_yaml(yaml_file)
            result = QuestionYamlImporter().import_payload(payload)
        except QuestionImportError as error:
            raise CommandError(str(error)) from error

        for question_label in result.skipped_questions:
            self.stderr.write(
                self.style.WARNING(
                    f"Question already exists and was skipped: {question_label}",
                ),
            )
        self.stdout.write(
            self.style.SUCCESS(
                f"Imported {result.imported_questions} question(s); "
                f"reused {result.reused_propositions} proposition(s).",
            ),
        )
