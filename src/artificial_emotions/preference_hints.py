"""Profile-scoped preference weight-hint math.

Callers import from ``artificial_emotions.preferences`` (stable). This module
suggests tiny ``ValueProfile`` deltas via ``learn_profile_weight_hints`` and
applies them only through ``apply_weight_hints_to_profile`` /
``preview_or_apply_weight_hints``. Preview is the default. Named presets are
never overwritten. Not calibrated learning.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from artificial_emotions.models import ValueProfile, resolve_value_profile
from artificial_emotions.preference_events import (
    _AXIS_TO_WEIGHT,
    PreferenceEvent,
    normalize_preference_events,
)

__all__ = [
    "apply_weight_hints_to_profile",
    "learn_profile_weight_hints",
    "preview_or_apply_weight_hints",
]

_HINT_HONESTY = (
    "Weight hints are tiny profile-scoped deltas from labeled prefer/reject "
    "events with score axes, and from outcome events that carry score_axes "
    "plus labels.result — not calibrated learning, not universal ranking, "
    "and not proof the profile is 'correct'."
)

# Outcome labels.result → prefer-like vs reject-like for axis means.
# Progress outcomes nudge toward those axes; misses / dead-ends /
# false-unknowns / logged nulls nudge away. Unknown tokens are skipped.
_OUTCOME_PREFER_RESULTS = frozenset({"partial_progress", "answered"})
_OUTCOME_REJECT_RESULTS = frozenset(
    {
        "contradicted",
        "already_answered",
        "answered_elsewhere",
        "abandoned",
        "null",
    }
)
_WEIGHT_FLOOR = 0.15


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
        out = {k: float(raw[k]) for k in _AXIS_TO_WEIGHT if k in raw and raw[k] is not None}
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


def _event_result_label(ev: PreferenceEvent) -> str:
    return str((ev.labels or {}).get("result") or "").strip().lower()


def _outcome_result_bucket(result: str) -> str | None:
    """Map labels.result to prefer-like / reject-like, or None if unknown."""
    r = (result or "").strip().lower()
    if r in _OUTCOME_PREFER_RESULTS:
        return "prefer"
    if r in _OUTCOME_REJECT_RESULTS:
        return "reject"
    return None


def learn_profile_weight_hints(
    events: Iterable[Any] | str | Path,
    *,
    profile_name: str | None = None,
    base_profile: ValueProfile | None = None,
    max_delta: float = 0.08,
    min_labeled: int = 2,
) -> dict[str, Any]:
    """
    Suggest small ValueProfile weight deltas from labeled events with axes.

    Prefer/keep vs reject/already_answered: axes that are higher on preferred
    items get a tiny positive weight nudge (and vice versa). ``event_type=outcome``
    rows with ``score_axes`` and a known ``labels.result`` join the same buckets
    (progress → prefer-like; contradicted / already_answered / answered_elsewhere
    / abandoned / null → reject-like). Caps keep this a *hint*, not calibrated
    learning. Profile-scoped only. Does not mutate ``base_profile`` — callers
    apply via ``apply_weight_hints_to_profile``.
    """
    evs = normalize_preference_events(events)

    prefer_axes: list[dict[str, float]] = []
    reject_axes: list[dict[str, float]] = []
    n_outcome = 0
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
        elif et == "outcome":
            bucket = _outcome_result_bucket(_event_result_label(ev))
            if bucket == "prefer":
                prefer_axes.append(axes)
                n_outcome += 1
            elif bucket == "reject":
                reject_axes.append(axes)
                n_outcome += 1

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
            "n_outcome": n_outcome,
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
    clamped: list[str] = []
    for weight_key, nudge in list(deltas.items()):
        cur = float(getattr(suggested, weight_key))
        # Guardrail: never drive a weight to 0 or below a floor (profile intent).
        floor = _WEIGHT_FLOOR
        new = float(max(floor, min(3.0, cur + nudge)))
        if new == floor and cur + nudge < floor:
            clamped.append(weight_key)
            # Shrink delta to what was actually applied.
            deltas[weight_key] = round(new - cur, 4)
        setattr(suggested, weight_key, new)
    # Drop zero deltas after clamp.
    deltas = {k: v for k, v in deltas.items() if abs(v) >= 0.005}
    if profile_name or base.name:
        suggested.name = f"{base.name}+pref_hints"
        suggested.description = (
            f"{base.description} [preference weight hints applied — see honesty]"
        )

    return {
        "ok": bool(deltas),
        "reason": "ok" if deltas else ("clamped_to_empty" if clamped else "axes_too_similar"),
        "n_prefer": n_pref,
        "n_reject": n_rej,
        "n_outcome": n_outcome,
        "deltas": deltas,
        "clamped_weights": clamped,
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


def preview_or_apply_weight_hints(
    events: Iterable[PreferenceEvent | dict[str, Any]] | str | Path,
    *,
    profile_name: str | None = None,
    base_profile: ValueProfile | None = None,
    max_delta: float = 0.08,
    min_labeled: int = 2,
    apply: bool = False,
) -> dict[str, Any]:
    """Preview (default) or apply tiny weight hints onto a profile copy.

    Uses ``learn_profile_weight_hints`` then, only when ``apply=True``,
    ``apply_weight_hints_to_profile``. Named presets are never overwritten
    in place. Not calibrated learning.
    """
    hints = learn_profile_weight_hints(
        events,
        profile_name=profile_name,
        base_profile=base_profile,
        max_delta=max_delta,
        min_labeled=min_labeled,
    )
    payload = dict(hints)
    payload["mode"] = "apply" if apply else "preview"
    payload["applied"] = False
    if apply:
        base = base_profile or resolve_value_profile(
            profile_name=profile_name or "humanity_default"
        )
        applied_profile = apply_weight_hints_to_profile(base, hints)
        payload["applied"] = bool(hints.get("ok"))
        payload["applied_profile"] = applied_profile.model_dump(mode="json")
    return payload
