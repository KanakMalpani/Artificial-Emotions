"""Preference JSONL I/O and event normalize seam.

Callers import from ``artificial_emotions.preferences`` (stable). This module
holds the ``PreferenceEvent`` schema, append/read/load, and
``normalize_preference_events`` / ``coerce_preference_event``. Corrupt rows
still skip and log at WARNING; only ``ValidationError`` and ``JSONDecodeError``
are swallowed. Logger namespace stays ``preferences`` so skip telemetry does
not churn.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from artificial_emotions.logutil import get_logger, soft_fail
from artificial_emotions.timeutil import utc_now_iso

SCHEMA_VERSION = "preference_event.v1"

logger = get_logger("preferences")

__all__ = [
    "SCHEMA_VERSION",
    "PreferenceEvent",
    "append_preference_event",
    "coerce_preference_event",
    "events_from_ranked",
    "load_preference_events",
    "normalize_preference_events",
    "outcome_for_appraisal",
    "read_preference_events",
]

_AXIS_TO_WEIGHT = {
    "impact": "weight_impact",
    "neglectedness": "weight_neglectedness",
    "tractability": "weight_tractability",
    "surprise": "weight_surprise",
}


class PreferenceEvent(BaseModel):
    """One preference / spot-check / outcome breadcrumb."""

    schema_version: str = SCHEMA_VERSION
    ts: str = Field(
        default_factory=utc_now_iso,
        description="ISO-8601 UTC timestamp",
    )
    event_type: str = Field(
        ...,
        description="prefer | reject | already_answered | keep | tie | both_keep | outcome | note",
    )
    profile_name: str = "humanity_default"
    domain: str | None = None
    question_id: str | None = None
    question_text: str | None = None
    rank: int | None = None
    curiosity_score: float | None = None
    # Optional axis snapshot at feedback time (enables weight hints).
    score_axes: dict[str, float] = Field(default_factory=dict)
    preferred_over_ids: list[str] = Field(default_factory=list)
    labels: dict[str, str] = Field(default_factory=dict)
    notes: str = ""
    run_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def append_preference_event(
    path: str | Path,
    event: PreferenceEvent | dict[str, Any],
) -> PreferenceEvent:
    """Append one JSONL line. Creates parent dirs as needed."""
    if isinstance(event, dict):
        event = PreferenceEvent.model_validate(event)
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(event.model_dump_json() + "\n")
    return event


def read_preference_events(path: str | Path) -> Iterator[PreferenceEvent]:
    """Yield PreferenceEvent rows from a JSONL file (skips blank/corrupt lines)."""
    p = Path(path)
    if not p.exists():
        return
        yield  # pragma: no cover — makes this a generator
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                loaded = json.loads(line)
            except json.JSONDecodeError as exc:
                soft_fail(logger, "Skipping corrupt preference JSONL line", exc=exc)
                continue
            parsed = coerce_preference_event(loaded)
            if parsed is None:
                continue
            yield parsed


def load_preference_events(path: str | Path) -> list[PreferenceEvent]:
    return list(read_preference_events(path))


def coerce_preference_event(raw: Any) -> PreferenceEvent | None:
    """Return a PreferenceEvent, or None when ``raw`` cannot be parsed.

    Expected parse failures (Pydantic ``ValidationError``, ``JSONDecodeError``)
    are skipped and logged. Other exceptions propagate — they are bugs.
    """
    if isinstance(raw, PreferenceEvent):
        return raw
    try:
        if isinstance(raw, str):
            raw = json.loads(raw)
        return PreferenceEvent.model_validate(raw)
    except (ValidationError, json.JSONDecodeError) as exc:
        soft_fail(logger, "Skipping unreadable preference event", exc=exc)
        return None


def normalize_preference_events(
    events: Iterable[Any] | str | Path,
) -> list[PreferenceEvent]:
    """Load preference events from a JSONL path or an in-memory iterable.

    Corrupt JSONL lines and unreadable iterable items are skipped (logged at
    WARNING). Missing files yield an empty list — callers that need a distinct
    missing-path reason (outcome-loop dry-run) must check the path themselves.
    A single ``PreferenceEvent`` is wrapped, not iterated as field names.
    """
    if isinstance(events, PreferenceEvent):
        return [events]
    if isinstance(events, (str, Path)):
        return load_preference_events(events)
    out: list[PreferenceEvent] = []
    for raw in events:
        parsed = coerce_preference_event(raw)
        if parsed is not None:
            out.append(parsed)
    return out


def outcome_for_appraisal(
    path: str | Path | None,
    *,
    question_ids: Iterable[str] | None = None,
) -> tuple[str, str]:
    """Latest matching outcome event as ``(result, question_id)``.

    Returns ``("", "")`` when ``path`` is missing, empty, or has no ``outcome``
    event with a question id. Does not invent results. When ``question_ids`` is
    given, only events whose ``question_id`` is in that set match — pride/shame
    stay silent without a matching logged outcome.
    """
    if not path:
        return "", ""
    allowed: set[str] | None = None
    if question_ids is not None:
        allowed = {str(q).strip() for q in question_ids if str(q).strip()}
    latest: PreferenceEvent | None = None
    for ev in load_preference_events(path):
        if (ev.event_type or "").lower() != "outcome":
            continue
        qid = (ev.question_id or "").strip()
        if not qid:
            continue
        if allowed is not None and qid not in allowed:
            continue
        latest = ev
    if latest is None:
        return "", ""
    result = str((latest.labels or {}).get("result") or "").strip().lower()
    return result, (latest.question_id or "").strip()


def events_from_ranked(
    ranked: Iterable[Any],
    *,
    event_type: str = "note",
    profile_name: str = "humanity_default",
    run_id: str | None = None,
    notes: str = "",
) -> list[PreferenceEvent]:
    """Helper: snapshot ranked questions into PreferenceEvent shells (caller labels later)."""
    out: list[PreferenceEvent] = []
    for item in ranked:
        q = getattr(item, "question", None)
        axes_obj = getattr(item, "scores", None)
        axes: dict[str, float] = {}
        if axes_obj is not None:
            if hasattr(axes_obj, "model_dump"):
                dumped = axes_obj.model_dump(mode="json")
                axes = {
                    k: float(dumped[k])
                    for k in _AXIS_TO_WEIGHT
                    if k in dumped and dumped[k] is not None
                }
            elif isinstance(axes_obj, dict):
                axes = {
                    k: float(axes_obj[k])
                    for k in _AXIS_TO_WEIGHT
                    if k in axes_obj and axes_obj[k] is not None
                }
        out.append(
            PreferenceEvent(
                event_type=event_type,
                profile_name=profile_name,
                domain=str(getattr(q, "domain", None) or ""),
                question_id=getattr(q, "id", None),
                question_text=getattr(q, "question", None),
                rank=getattr(item, "rank", None),
                curiosity_score=getattr(item, "curiosity_score", None),
                score_axes=axes,
                run_id=run_id,
                notes=notes,
            )
        )
    return out
