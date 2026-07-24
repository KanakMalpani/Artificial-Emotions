"""Opt-in preference / ranking feedback JSONL (F11 flywheel prep).

No database required. Callers append PreferenceEvent records when a human
or agent expresses preference among ranked unknowns.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

SCHEMA_VERSION = "preference_event.v1"


class PreferenceEvent(BaseModel):
    """One preference / spot-check / outcome breadcrumb."""

    schema_version: str = SCHEMA_VERSION
    ts: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
        description="ISO-8601 UTC timestamp",
    )
    event_type: str = Field(
        ...,
        description="prefer | reject | already_answered | keep | outcome | note",
    )
    profile_name: str = "humanity_default"
    domain: str | None = None
    question_id: str | None = None
    question_text: str | None = None
    rank: int | None = None
    curiosity_score: float | None = None
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
                yield PreferenceEvent.model_validate(json.loads(line))
            except Exception:  # noqa: BLE001
                continue


def load_preference_events(path: str | Path) -> list[PreferenceEvent]:
    return list(read_preference_events(path))


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
        out.append(
            PreferenceEvent(
                event_type=event_type,
                profile_name=profile_name,
                domain=str(getattr(q, "domain", None) or ""),
                question_id=getattr(q, "id", None),
                question_text=getattr(q, "question", None),
                rank=getattr(item, "rank", None),
                curiosity_score=getattr(item, "curiosity_score", None),
                run_id=run_id,
                notes=notes,
            )
        )
    return out


def preference_score_adjustments(
    path: str | Path,
    *,
    profile_name: str | None = None,
    boost: float = 0.06,
    penalty: float = 0.05,
) -> dict[str, float]:
    """
    Thin preference → score delta map (F11 flywheel prep).

    Uses prefer / keep / reject / already_answered events only.
    Adjustments are *within* a profile when profile_name is set — never a
    universal re-rank oracle. Caps keep deltas small and honest.
    """
    adj: dict[str, float] = {}
    for ev in load_preference_events(path):
        if profile_name and ev.profile_name and ev.profile_name != profile_name:
            continue
        qid = (ev.question_id or "").strip()
        if not qid:
            continue
        et = (ev.event_type or "").lower()
        if et in ("prefer", "keep"):
            adj[qid] = adj.get(qid, 0.0) + boost
        elif et in ("reject", "already_answered"):
            adj[qid] = adj.get(qid, 0.0) - penalty
        for other in ev.preferred_over_ids or []:
            oid = str(other).strip()
            if oid:
                adj[oid] = adj.get(oid, 0.0) - (penalty * 0.5)
    # Soft cap so preference never dominates geometric scores.
    return {k: float(max(-0.15, min(0.15, v))) for k, v in adj.items()}


def apply_preference_rerank(
    ranked: list[Any],
    adjustments: dict[str, float],
) -> list[Any]:
    """
    Re-sort ranked items by curiosity_score + preference delta.

    Mutates curiosity_score lightly and sets metadata flags; caller should
    re-assign ranks. Empty adjustments → identity.
    """
    if not adjustments:
        return ranked
    for item in ranked:
        q = getattr(item, "question", None)
        qid = getattr(q, "id", None) if q is not None else None
        delta = adjustments.get(str(qid or ""), 0.0)
        if not delta:
            continue
        base = float(getattr(item, "curiosity_score", 0.0) or 0.0)
        item.curiosity_score = float(max(0.0, min(1.5, base + delta)))
        meta = getattr(item, "metadata", None)
        if isinstance(meta, dict):
            meta["preference_delta"] = delta
        flags = list(getattr(item, "flags", None) or [])
        if "preference_rerank" not in flags:
            flags.append("preference_rerank")
        item.flags = flags
    ranked.sort(key=lambda r: float(getattr(r, "curiosity_score", 0.0) or 0.0), reverse=True)
    for i, item in enumerate(ranked, start=1):
        if hasattr(item, "rank"):
            item.rank = i
    return ranked
