"""Build audit exports exclusively from the immutable game-event sequence."""

from __future__ import annotations

import csv
import io
import json
from dataclasses import asdict
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING
from typing import Any

if TYPE_CHECKING:
    from collections.abc import Iterable

INCIDENT_TYPES = frozenset(
    {
        "manager_intervention",
        "player_locked",
        "player_unlocked",
        "ad_break_started",
        "ad_break_ended",
    },
)


@dataclass(frozen=True)
class AuditReport:
    """Portable representation used by JSON, CSV, and PDF export renderers."""

    header: dict[str, Any]
    turns: list[dict[str, Any]]
    incidents: list[dict[str, Any]]
    raw_events: list[dict[str, Any]]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_report(episode: Any, events: Iterable[Any]) -> AuditReport:
    """Reconstruct an audit report from ordered events, never from a snapshot.

    ``events`` may be a Django queryset or an iterable exposing ``sequence``,
    ``type``, ``payload``, ``emitted_by`` and ``created``/``created_at``.
    """
    raw_events = [_serialize_event(event) for event in events]
    raw_events.sort(key=lambda event: event["sequence"])
    turns: list[dict[str, Any]] = []
    incidents: list[dict[str, Any]] = []
    current_turn: dict[str, Any] | None = None

    for event in raw_events:
        event_type = event["type"]
        payload = event["payload"]
        if event_type == "cell_selected":
            if current_turn is not None:
                current_turn["interrupted"] = True
                turns.append(current_turn)
            current_turn = {
                "cell_id": payload.get("cell_id"),
                "position": payload.get("position"),
                "participant_id": payload.get("participant_id"),
                "selected_at": event["timestamp"],
            }
        elif event_type == "question_revealed" and current_turn is not None:
            current_turn["question"] = payload
        elif event_type == "answer_submitted" and current_turn is not None:
            current_turn["answer"] = payload
        elif event_type == "cell_resolved" and current_turn is not None:
            current_turn["resolution"] = payload
            current_turn["resolved_at"] = event["timestamp"]
            turns.append(current_turn)
            current_turn = None
        elif event_type == "empty_cell_played":
            turns.append(
                {
                    "cell_id": payload.get("cell_id"),
                    "position": payload.get("position"),
                    "empty": True,
                    "played_at": event["timestamp"],
                },
            )
            current_turn = None
        elif event_type in INCIDENT_TYPES:
            incidents.append(event)

    if current_turn is not None:
        current_turn["interrupted"] = True
        turns.append(current_turn)

    return AuditReport(
        header=_build_header(episode, raw_events, turns),
        turns=turns,
        incidents=incidents,
        raw_events=raw_events,
    )


def render_json(report: AuditReport) -> bytes:
    """Render the complete, independently auditable JSON export."""
    return json.dumps(
        report.as_dict(),
        ensure_ascii=False,
        indent=2,
        default=str,
    ).encode()


def render_csv(report: AuditReport) -> bytes:
    """Render one raw-event row per line, as required for external verification."""
    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output,
        fieldnames=("sequence", "type", "timestamp", "emitted_by", "payload_json"),
    )
    writer.writeheader()
    for event in report.raw_events:
        writer.writerow(
            {
                "sequence": event["sequence"],
                "type": event["type"],
                "timestamp": event["timestamp"] or "",
                "emitted_by": event["emitted_by"],
                "payload_json": json.dumps(event["payload"], ensure_ascii=False),
            },
        )
    return output.getvalue().encode()


def render_pdf(report: AuditReport) -> bytes:
    """Render a small dependency-free, archival PDF summary."""
    lines = ["EpicQuiz - Rapport d'audit"]
    lines.extend(
        f"{key.replace('_', ' ').title()} : {value}"
        for key, value in report.header.items()
    )
    lines.extend(["", "Tours"])
    lines.extend(_turn_text(turn) for turn in report.turns)
    lines.extend(["", "Incidents"])
    lines.extend(_incident_text(event) for event in report.incidents)
    return _minimal_pdf(lines)


def _build_header(
    episode: Any,
    events: list[dict[str, Any]],
    turns: list[dict[str, Any]],
) -> dict[str, Any]:
    participants = _participants_by_id(episode)
    scores = dict.fromkeys(participants, 0)
    for turn in turns:
        resolution = turn.get("resolution", {})
        participant_id = turn.get("participant_id")
        if participant_id is not None:
            scores[participant_id] = scores.get(participant_id, 0) + int(
                resolution.get("points_earned", 0),
            )
        opponent_id = resolution.get("opponent_participant_id")
        if opponent_id is not None:
            scores[opponent_id] = scores.get(opponent_id, 0) - int(
                resolution.get("points_removed_from_opponent", 0),
            )

    started_at = _event_time(events, "game_started")
    finished_at = _event_time(events, "game_finished")
    winner_id = max(scores, key=scores.get) if scores else None
    return {
        "episode": _value(episode, "title", str(episode)),
        "recording_date": _format_time(_value(episode, "recording_date")),
        "participants": [
            participants[identifier] for identifier in sorted(participants)
        ],
        "final_scores": {
            str(identifier): score for identifier, score in scores.items()
        },
        "winner": participants.get(winner_id),
        "duration": _format_duration(started_at, finished_at),
    }


def _participants_by_id(episode: Any) -> dict[int, str]:
    participants = _value(episode, "participants", ())
    if hasattr(participants, "all"):
        participants = participants.all()
    return {
        _value(participant, "id"): _participant_name(participant)
        for participant in participants
        if _value(participant, "id") is not None
    }


def _participant_name(participant: Any) -> str:
    user = _value(participant, "user")
    return _value(user, "name") or _value(user, "username") or str(participant)


def _serialize_event(event: Any) -> dict[str, Any]:
    return {
        "sequence": _value(event, "sequence", 0),
        "type": _value(event, "type"),
        "timestamp": _format_time(
            _value(event, "created_at") or _value(event, "created"),
        ),
        "emitted_by": _value(event, "emitted_by", "system"),
        "payload": _value(event, "payload", {}) or {},
    }


def _value(value: Any, attribute: str, default: Any = None) -> Any:
    return (
        value.get(attribute, default)
        if isinstance(value, dict)
        else getattr(value, attribute, default)
    )


def _event_time(events: list[dict[str, Any]], event_type: str) -> str | None:
    return next(
        (event["timestamp"] for event in events if event["type"] == event_type),
        None,
    )


def _format_time(value: datetime | str | None) -> str | None:
    return value if value is None or isinstance(value, str) else value.isoformat()


def _format_duration(started_at: str | None, finished_at: str | None) -> str | None:
    if not started_at or not finished_at:
        return None
    return str(datetime.fromisoformat(finished_at) - datetime.fromisoformat(started_at))


def _turn_text(turn: dict[str, Any]) -> str:
    position = turn.get("position", "?")
    if turn.get("empty"):
        return f"Case {position} : case vide, tour passe a l'adversaire."
    if turn.get("interrupted"):
        return f"Case {position} : tour interrompu - aucune résolution enregistrée."
    return f"Case {position} : résolution enregistrée."


def _incident_text(event: dict[str, Any]) -> str:
    return f"[{event['timestamp'] or '?'}] {event['type'].upper()}"


def _minimal_pdf(lines: list[str]) -> bytes:
    safe_lines = [
        line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        for line in lines
    ]
    text = " T* ".join(f"({line}) Tj" for line in safe_lines)
    stream = f"BT /F1 11 Tf 50 780 Td 0 -15 Td {text} ET".encode("latin-1", "replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length "
        + str(len(stream)).encode()
        + b" >>\nstream\n"
        + stream
        + b"\nendstream",
    ]
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode())
        output.extend(obj)
        output.extend(b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    output.extend(
        b"".join(f"{offset:010} 00000 n \n".encode() for offset in offsets[1:]),
    )
    trailer = f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>"
    output.extend(f"{trailer}\nstartxref\n{xref}\n%%EOF\n".encode())
    return bytes(output)
