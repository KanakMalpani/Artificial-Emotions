"""Opt-in preference / ranking feedback JSONL (F11 flywheel prep).

No database required. Callers append PreferenceEvent records when a human
or agent expresses preference among ranked unknowns.

Beyond thin per-question re-rank, ``learn_profile_weight_hints`` suggests
*small* ValueProfile weight deltas **within** a named profile from labeled
prefer/reject events that carry score axes — never a universal rank oracle.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from artificial_curiosity.models import ValueProfile, resolve_value_profile

SCHEMA_VERSION = "preference_event.v1"

_AXIS_TO_WEIGHT = {
    "impact": "weight_impact",
    "neglectedness": "weight_neglectedness",
    "tractability": "weight_tractability",
    "surprise": "weight_surprise",
}

_HINT_HONESTY = (
    "Weight hints are tiny profile-scoped deltas from labeled prefer/reject "
    "events with score axes — not calibrated learning, not universal ranking, "
    "and not proof the profile is 'correct'."
)


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


def _axes_from_event(ev: PreferenceEvent) -> dict[str, float] | None:
    if ev.score_axes:
        out = {
            k: float(ev.score_axes[k])
            for k in _AXIS_TO_WEIGHT
            if k in ev.score_axes and ev.score_axes[k] is not None
        }
        if len(out) >= 2:
            return out
    meta = ev.metadata or {}
    raw = meta.get("score_axes") or meta.get("scores")
    if isinstance(raw, dict):
        out = {
            k: float(raw[k])
            for k in _AXIS_TO_WEIGHT
            if k in raw and raw[k] is not None
        }
        if len(out) >= 2:
            return out
    return None


def _mean_axes(rows: list[dict[str, float]]) -> dict[str, float]:
    if not rows:
        return {}
    keys: set[str] = set()
    for r in rows:
        keys.update(r.keys())
    means: dict[str, float] = {}
    for k in keys:
        vals = [r[k] for r in rows if k in r]
        if vals:
            means[k] = sum(vals) / len(vals)
    return means


def learn_profile_weight_hints(
    events: Iterable[PreferenceEvent | dict[str, Any]] | str | Path,
    *,
    profile_name: str | None = None,
    base_profile: ValueProfile | None = None,
    max_delta: float = 0.08,
    min_labeled: int = 2,
) -> dict[str, Any]:
    """
    Suggest small ValueProfile weight deltas from labeled events with axes.

    Prefer/keep vs reject/already_answered: axes that are higher on preferred
    items get a tiny positive weight nudge (and vice versa). Caps keep this a
    *hint*, not calibrated learning. Profile-scoped only.
    """
    if isinstance(events, (str, Path)):
        evs = load_preference_events(events)
    else:
        evs = []
        for e in events:
            if isinstance(e, PreferenceEvent):
                evs.append(e)
            else:
                try:
                    evs.append(PreferenceEvent.model_validate(e))
                except Exception:  # noqa: BLE001
                    continue

    prefer_axes: list[dict[str, float]] = []
    reject_axes: list[dict[str, float]] = []
    for ev in evs:
        if profile_name and ev.profile_name and ev.profile_name != profile_name:
            continue
        axes = _axes_from_event(ev)
        if not axes:
            continue
        et = (ev.event_type or "").lower()
        if et in ("prefer", "keep"):
            prefer_axes.append(axes)
        elif et in ("reject", "already_answered"):
            reject_axes.append(axes)

    base = base_profile or resolve_value_profile(profile_name=profile_name or "humanity_default")
    n_pref = len(prefer_axes)
    n_rej = len(reject_axes)
    labeled = n_pref + n_rej
    if labeled < min_labeled or n_pref < 1:
        return {
            "ok": False,
            "reason": "need_more_labeled_events_with_score_axes",
            "n_prefer": n_pref,
            "n_reject": n_rej,
            "deltas": {},
            "suggested_profile": base.model_dump(mode="json"),
            "honesty": _HINT_HONESTY,
        }

    mean_p = _mean_axes(prefer_axes)
    mean_r = _mean_axes(reject_axes) if reject_axes else {k: 0.5 for k in mean_p}
    deltas: dict[str, float] = {}
    for axis, weight_key in _AXIS_TO_WEIGHT.items():
        diff = float(mean_p.get(axis, 0.5) - mean_r.get(axis, 0.5))
        # Scale: full 1.0 axis gap → max_delta weight nudge.
        nudge = max(-max_delta, min(max_delta, diff * max_delta * 2.0))
        if abs(nudge) < 0.005:
            continue
        deltas[weight_key] = round(nudge, 4)

    suggested = base.model_copy(deep=True)
    for weight_key, nudge in deltas.items():
        cur = float(getattr(suggested, weight_key))
        setattr(suggested, weight_key, float(max(0.0, min(3.0, cur + nudge))))
    if profile_name or base.name:
        suggested.name = f"{base.name}+pref_hints"
        suggested.description = (
            f"{base.description} [preference weight hints applied — see honesty]"
        )

    return {
        "ok": bool(deltas),
        "reason": "ok" if deltas else "axes_too_similar",
        "n_prefer": n_pref,
        "n_reject": n_rej,
        "deltas": deltas,
        "mean_prefer_axes": mean_p,
        "mean_reject_axes": mean_r if reject_axes else {},
        "suggested_profile": suggested.model_dump(mode="json"),
        "honesty": _HINT_HONESTY,
    }


def apply_weight_hints_to_profile(
    profile: ValueProfile,
    hints: dict[str, Any],
) -> ValueProfile:
    """Apply ``learn_profile_weight_hints`` deltas onto a profile copy."""
    if not hints or not hints.get("ok"):
        return profile
    suggested = hints.get("suggested_profile")
    if isinstance(suggested, dict):
        return ValueProfile.model_validate(suggested)
    return profile
