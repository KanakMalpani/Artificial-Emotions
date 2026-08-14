"""Outcome JSONL → suggested re-rank / next explore (dry-run only).

Reads ``event_type=outcome`` rows from a preference JSONL log and proposes
what a lab closed-loop *would* do next: deprioritize resolved or dead-end
unknowns, keep partial progress in view, and name a next ``explore`` step.

What it is not: experiment execution. It never calls ``explore()``, never
runs the ranking engine, and must not be described as a lab closed-loop.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from artificial_emotions.preferences import PreferenceEvent, load_preference_events
from artificial_emotions.resources import find_data_file

__all__ = [
    "DEFAULT_OUTCOME_LOOP_FIXTURE",
    "default_outcome_loop_fixture",
    "dry_run_outcome_loop",
]

DEFAULT_OUTCOME_LOOP_FIXTURE = "evals/fixtures/outcome_loop_smoke_v1.jsonl"

_CONTINUE_RESULTS = frozenset({"partial_progress"})
_RESOLVED_RESULTS = frozenset({"answered", "already_answered", "answered_elsewhere"})
_DEAD_END_RESULTS = frozenset({"contradicted", "abandoned", "null"})

_CONTINUE_DELTA = 0.05
_RESOLVED_DELTA = -0.10
_DEAD_END_DELTA = -0.08
_DELTA_CAP = 0.15

_HONESTY = (
    "Dry-run only. Reads event_type=outcome rows from preference JSONL and "
    "suggests a re-rank plus a next explore step. Does not run experiments, "
    "does not call explore, and is not a lab closed-loop. Prefer/reject "
    "events are ignored here (use preferences hints / --preference-rerank). "
    "Not EVSI. Scores remain decision aids with an explicit ValueProfile."
)


def default_outcome_loop_fixture() -> Path:
    return find_data_file(DEFAULT_OUTCOME_LOOP_FIXTURE)


def _normalize_events(
    events: Iterable[Any] | str | Path,
) -> tuple[list[PreferenceEvent], str | None, str]:
    """Return (events, path_str_or_none, reason_if_unreadable)."""
    if isinstance(events, (str, Path)):
        path = Path(events)
        if not path.exists():
            return [], str(path), "missing_outcomes_jsonl"
        if not path.is_file():
            return [], str(path), "not_a_file"
        return load_preference_events(path), str(path), "ok"
    out: list[PreferenceEvent] = []
    for raw in events:
        if isinstance(raw, PreferenceEvent):
            out.append(raw)
            continue
        try:
            out.append(PreferenceEvent.model_validate(raw))
        except Exception:  # noqa: BLE001
            continue
    return out, None, "ok"


def _result_of(ev: PreferenceEvent) -> str:
    raw = str((ev.labels or {}).get("result") or "").strip().lower()
    return raw or "unspecified"


def _bucket_and_delta(result: str) -> tuple[str, float]:
    if result in _CONTINUE_RESULTS:
        return "continue", _CONTINUE_DELTA
    if result in _RESOLVED_RESULTS:
        return "resolved", _RESOLVED_DELTA
    if result in _DEAD_END_RESULTS:
        return "dead_end", _DEAD_END_DELTA
    return "unknown", 0.0


def _cap(delta: float) -> float:
    return float(max(-_DELTA_CAP, min(_DELTA_CAP, delta)))


def _next_explore(
    ranked: list[dict[str, Any]],
) -> dict[str, Any] | None:
    continues = [row for row in ranked if row["bucket"] == "continue"]
    if continues:
        pick = continues[0]
        domain = pick.get("domain") or ""
        suggested = (
            f"emotions explore --domain {domain} --steps 1"
            if domain
            else "emotions explore --steps 1"
        )
        return {
            "action": "continue",
            "question_id": pick["question_id"],
            "domain": pick.get("domain"),
            "rationale": (
                "Logged partial_progress — suggested next step is another "
                "explore pass (or decompose) on this unknown. Not executed."
            ),
            "suggested_command": suggested,
            "executed": False,
        }

    if not ranked:
        return None

    if any(row["bucket"] == "unknown" for row in ranked):
        pick = next(row for row in ranked if row["bucket"] == "unknown")
        return {
            "action": "inspect",
            "question_id": pick["question_id"],
            "domain": pick.get("domain"),
            "rationale": (
                "Outcome labels.result is unrecognized — inspect the log "
                "before exploring further. Not executed."
            ),
            "suggested_command": None,
            "executed": False,
        }

    return {
        "action": "shift",
        "question_id": None,
        "domain": None,
        "rationale": (
            "Logged outcomes are resolved or dead-end — suggested next "
            "step is a different unknown or domain. Not executed."
        ),
        "suggested_command": "emotions explore --steps 1",
        "executed": False,
    }


def dry_run_outcome_loop(
    events: Iterable[Any] | str | Path,
    *,
    profile_name: str | None = None,
) -> dict[str, Any]:
    """Suggest a re-rank and next explore step from outcome JSONL.

    Never runs experiments. ``experiments_run`` is always 0.
    """
    from artificial_emotions import __version__

    evs, path_str, io_reason = _normalize_events(events)
    n_events = len(evs)
    if profile_name:
        evs = [ev for ev in evs if not ev.profile_name or ev.profile_name == profile_name]

    by_result: dict[str, int] = {}
    n_outcome = 0
    n_non_outcome = 0
    latest: dict[str, PreferenceEvent] = {}
    for ev in evs:
        et = (ev.event_type or "").lower()
        if et != "outcome":
            n_non_outcome += 1
            continue
        n_outcome += 1
        result = _result_of(ev)
        by_result[result] = by_result.get(result, 0) + 1
        qid = (ev.question_id or "").strip()
        if qid:
            latest[qid] = ev

    suggested: list[dict[str, Any]] = []
    for qid, ev in latest.items():
        result = _result_of(ev)
        bucket, delta = _bucket_and_delta(result)
        suggested.append(
            {
                "question_id": qid,
                "delta": _cap(delta),
                "reason": result,
                "bucket": bucket,
                "domain": ev.domain,
                "profile_name": ev.profile_name,
            }
        )
    suggested.sort(key=lambda row: (-float(row["delta"]), str(row["question_id"])))
    for i, row in enumerate(suggested, start=1):
        row["suggested_rank"] = i

    if io_reason != "ok":
        reason = io_reason
        ok = False
    elif n_outcome == 0:
        reason = "no_outcomes"
        ok = True
    else:
        reason = "ok"
        ok = True

    next_step = _next_explore(suggested) if n_outcome else None

    return {
        "mode": "dry_run",
        "report": "outcome_loop_dry_run",
        "package_version": __version__,
        "ok": ok,
        "reason": reason,
        "outcomes_path": path_str,
        "profile_name": profile_name,
        "n_events": n_events,
        "n_outcome": n_outcome,
        "n_non_outcome_ignored": n_non_outcome,
        "by_result": dict(sorted(by_result.items())),
        "suggested_rerank": suggested,
        "next_explore": next_step,
        "experiments_run": 0,
        "executed": False,
        "ran_explore": False,
        "honesty": _HONESTY,
        "docs": "docs/LIMITS.md",
    }
