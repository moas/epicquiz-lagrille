from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime

from core.audit.services import build_report
from core.audit.services import render_csv
from core.audit.services import render_json
from core.audit.services import render_pdf


@dataclass
class User:
    name: str


@dataclass
class Participant:
    id: int
    user: User


@dataclass
class Episode:
    title: str
    recording_date: datetime
    participants: list[Participant]


def event(sequence: int, event_type: str, payload: dict, minute: int = 0) -> dict:
    return {
        "sequence": sequence,
        "type": event_type,
        "payload": payload,
        "emitted_by": "system",
        "created_at": datetime(2026, 8, 19, 20, minute, tzinfo=UTC),
    }


def test_build_report_keeps_raw_events_and_marks_unresolved_turn() -> None:
    episode = Episode(
        title="Finale",
        recording_date=datetime(2026, 8, 19, tzinfo=UTC),
        participants=[Participant(1, User("Léon")), Participant(2, User("Adama"))],
    )
    report = build_report(
        episode,
        [
            event(4, "manager_intervention", {"reason": "tablette hors ligne"}, 4),
            event(1, "game_started", {}, 0),
            event(
                2,
                "cell_selected",
                {"cell_id": 19, "position": 19, "participant_id": 1},
                2,
            ),
            event(3, "question_revealed", {"text": "Question"}, 3),
            event(5, "game_finished", {}, 5),
        ],
    )

    assert [item["sequence"] for item in report.raw_events] == [1, 2, 3, 4, 5]
    assert report.turns == [
        {
            "cell_id": 19,
            "position": 19,
            "participant_id": 1,
            "selected_at": "2026-08-19T20:02:00+00:00",
            "question": {"text": "Question"},
            "interrupted": True,
        },
    ]
    assert report.incidents[0]["type"] == "manager_intervention"
    assert report.header["duration"] == "0:05:00"


def test_exports_include_the_required_raw_event_data() -> None:
    cell_id = 3
    report = build_report(
        Episode("Épisode 1", datetime(2026, 8, 19, tzinfo=UTC), []),
        [event(1, "empty_cell_played", {"cell_id": cell_id, "position": cell_id})],
    )

    document = json.loads(render_json(report))
    csv_rows = list(csv.DictReader(io.StringIO(render_csv(report).decode())))

    assert document["raw_events"][0]["payload"]["cell_id"] == cell_id
    assert csv_rows == [
        {
            "sequence": "1",
            "type": "empty_cell_played",
            "timestamp": "2026-08-19T20:00:00+00:00",
            "emitted_by": "system",
            "payload_json": '{"cell_id": 3, "position": 3}',
        },
    ]
    assert render_pdf(report).startswith(b"%PDF-1.4")
