"""Opt-in preference / ranking feedback JSONL (F11 flywheel prep).

No database required. Callers append PreferenceEvent records when a human
or agent expresses preference among ranked unknowns.

Beyond thin per-question re-rank, ``learn_profile_weight_hints`` suggests
*small* ValueProfile weight deltas **within** a named profile from labeled
prefer/reject events that carry score axes, and from ``event_type=outcome``
rows that carry ``score_axes`` plus ``labels.result`` — never a universal
rank oracle. Hints are not applied until ``apply_weight_hints_to_profile``.

JSONL I/O and event normalize live in ``preference_events``; weight-hint math
lives in ``preference_hints``. This module is the stable import path
(CLI / HTTP / MCP / tests). Preview remains the default; ``--apply`` /
``apply=true`` returns a profile copy and never overwrites named presets.
Not calibrated.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from artificial_emotions.preference_events import (
    SCHEMA_VERSION,
    PreferenceEvent,
    append_preference_event,
    coerce_preference_event,
    events_from_ranked,
    load_preference_events,
    normalize_preference_events,
    outcome_for_appraisal,
    read_preference_events,
)
from artificial_emotions.preference_hints import (
    _HINT_HONESTY,
    apply_weight_hints_to_profile,
    learn_profile_weight_hints,
    preview_or_apply_weight_hints,
)

__all__ = [
    "SCHEMA_VERSION",
    "PreferenceEvent",
    "append_preference_event",
    "apply_preference_rerank",
    "apply_weight_hints_to_profile",
    "coerce_preference_event",
    "events_from_ranked",
    "fit_bt_offline",
    "learn_profile_weight_hints",
    "load_preference_events",
    "normalize_preference_events",
    "outcome_for_appraisal",
    "preference_score_adjustments",
    "preview_or_apply_weight_hints",
    "read_preference_events",
    "suggest_next_pair",
    "summarize_preferences",
]


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


def summarize_preferences(
    events: Iterable[PreferenceEvent | dict[str, Any]] | str | Path,
    *,
    profile_name: str | None = None,
    top_k: int = 10,
) -> dict[str, Any]:
    """
    Stage-1 preference flywheel summary (research/PREFERENCE_CALIBRATION.md).

    Counts by event_type, pairwise win rates from preferred_over_ids, top ids
    by Borda-ish score, plus weight hints. Profile-scoped when profile_name set.
    """
    evs = normalize_preference_events(events)
    if profile_name:
        evs = [e for e in evs if (e.profile_name or "") == profile_name or not e.profile_name]

    counts: dict[str, int] = {}
    wins: dict[str, int] = {}
    losses: dict[str, int] = {}
    prefer_ids: dict[str, int] = {}
    reject_ids: dict[str, int] = {}
    pairwise_n = 0
    domains: dict[str, int] = {}

    for ev in evs:
        et = (ev.event_type or "unknown").lower()
        counts[et] = counts.get(et, 0) + 1
        if ev.domain:
            domains[str(ev.domain)] = domains.get(str(ev.domain), 0) + 1
        qid = (ev.question_id or "").strip()
        if et in ("prefer", "keep", "both_keep") and qid:
            prefer_ids[qid] = prefer_ids.get(qid, 0) + 1
            wins[qid] = wins.get(qid, 0) + 1
        elif et in ("reject", "already_answered") and qid:
            reject_ids[qid] = reject_ids.get(qid, 0) + 1
            losses[qid] = losses.get(qid, 0) + 1
        elif et == "tie" and qid:
            # Ties: count both sides as soft keep without win/loss (BTT honesty).
            prefer_ids[qid] = prefer_ids.get(qid, 0) + 1
            for other in ev.preferred_over_ids or []:
                oid = str(other).strip()
                if oid:
                    prefer_ids[oid] = prefer_ids.get(oid, 0) + 1
        for other in ev.preferred_over_ids or []:
            oid = str(other).strip()
            if not oid:
                continue
            if et == "tie":
                continue  # already handled; do not invent a win
            pairwise_n += 1
            if qid:
                wins[qid] = wins.get(qid, 0) + 1
            losses[oid] = losses.get(oid, 0) + 1

    # Borda-ish: +2 prefer, +1 pairwise win, -2 reject, -1 pairwise loss
    scores: dict[str, float] = {}
    for qid, n in prefer_ids.items():
        scores[qid] = scores.get(qid, 0.0) + 2.0 * n
    for qid, n in reject_ids.items():
        scores[qid] = scores.get(qid, 0.0) - 2.0 * n
    for qid, n in wins.items():
        scores[qid] = scores.get(qid, 0.0) + 1.0 * n
    for qid, n in losses.items():
        scores[qid] = scores.get(qid, 0.0) - 1.0 * n

    ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))[: max(1, top_k)]
    win_rates = []
    for qid, _ in ranked:
        n_wins = wins.get(qid, 0)
        n_losses = losses.get(qid, 0)
        denom = n_wins + n_losses
        win_rates.append(
            {
                "question_id": qid,
                "score": round(scores.get(qid, 0.0), 3),
                "wins": n_wins,
                "losses": n_losses,
                "win_rate": round(n_wins / denom, 3) if denom else None,
            }
        )

    hints = learn_profile_weight_hints(evs, profile_name=profile_name)

    # Sparse outcome flywheel (research/OUTCOME_FLYWHEEL.md) — counts only.
    outcome_results: dict[str, int] = {}
    n_outcome = 0
    for ev in evs:
        if (ev.event_type or "").lower() != "outcome":
            continue
        n_outcome += 1
        result = str((ev.labels or {}).get("result") or "unspecified").strip().lower()
        outcome_results[result] = outcome_results.get(result, 0) + 1

    return {
        "n_events": len(evs),
        "profile_name": profile_name,
        "counts_by_type": dict(sorted(counts.items())),
        "domains": dict(sorted(domains.items())),
        "n_pairwise": pairwise_n,
        "top_question_ids": win_rates,
        "outcomes": {
            "n_outcome": n_outcome,
            "by_result": dict(sorted(outcome_results.items())),
            "note": (
                "Sparse flywheel breadcrumbs — not a calibration certificate. "
                "Do not auto-retrain ranks from outcomes without human review."
            ),
        },
        "weight_hints": {
            "ok": hints.get("ok"),
            "reason": hints.get("reason"),
            "deltas": hints.get("deltas"),
            "clamped_weights": hints.get("clamped_weights"),
            "suggested_profile": hints.get("suggested_profile"),
            "n_outcome": hints.get("n_outcome"),
        },
        "honesty": (
            "Preference summary is profile-scoped decision-aid telemetry — "
            "not calibrated ranking, not Bradley–Terry until n is larger, "
            "not a performance certificate when outcome n is small, "
            "and not a universal science priority. " + _HINT_HONESTY
        ),
        "docs": "docs/LIMITS.md",
    }


def suggest_next_pair(
    candidates: list[dict[str, Any]] | list[str],
    events: Iterable[PreferenceEvent | dict[str, Any]] | str | Path | None = None,
    *,
    profile_name: str | None = None,
) -> dict[str, Any]:
    """
    Propose the next pairwise duel among top-k candidates (Swiss InfoGain–inspired).

    Heuristic: prefer pairs with fewest prior comparisons, then closest curiosity
    scores / adjacent ranks. Does **not** fit BT or rewrite weights.
    """
    rows: list[dict[str, Any]] = []
    for i, c in enumerate(candidates):
        if isinstance(c, str):
            rows.append({"question_id": c, "rank": i + 1, "curiosity_score": None})
        elif isinstance(c, dict):
            qid = str(c.get("question_id") or c.get("id") or f"cand-{i}")
            rows.append(
                {
                    "question_id": qid,
                    "rank": int(c.get("rank") or i + 1),
                    "curiosity_score": c.get("curiosity_score"),
                    "question": c.get("question"),
                }
            )
    if len(rows) < 2:
        return {
            "ok": False,
            "reason": "need_at_least_two_candidates",
            "pair": None,
            "honesty": "Active pair picker needs ≥2 candidates.",
        }

    compared: dict[tuple[str, str], int] = {}
    if events is not None:
        for ev in normalize_preference_events(events):
            if profile_name and (ev.profile_name or "") not in (profile_name, ""):
                continue
            qid = (ev.question_id or "").strip()
            et = (ev.event_type or "").lower()
            others = list(ev.preferred_over_ids or [])
            if et in ("tie", "both_keep") and len(others) >= 1:
                others = others[:1]
            for oid in others:
                a, b = sorted([qid, str(oid).strip()])
                if not a or not b or a == b:
                    continue
                compared[(a, b)] = compared.get((a, b), 0) + 1

    best: tuple[float, dict[str, Any]] | None = None
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            a, b = rows[i], rows[j]
            key = tuple(sorted([a["question_id"], b["question_id"]]))
            n_comp = compared.get(key, 0)
            # Prefer uncompared; then adjacent ranks; then close scores
            rank_gap = abs(int(a["rank"]) - int(b["rank"]))
            sa, sb = a.get("curiosity_score"), b.get("curiosity_score")
            score_gap = abs(float(sa) - float(sb)) if sa is not None and sb is not None else 0.5
            # Lower is better for selection score
            sel = (n_comp * 10.0) + (rank_gap * 0.5) + score_gap
            pair = {
                "a": a,
                "b": b,
                "prior_comparisons": n_comp,
                "selection_score": round(sel, 4),
            }
            if best is None or sel < best[0]:
                best = (sel, pair)

    assert best is not None
    return {
        "ok": True,
        "pair": best[1],
        "n_candidates": len(rows),
        "n_prior_pair_edges": len(compared),
        "honesty": (
            "Heuristic next duel for annotation budget — not full Swiss InfoGain, "
            "not BT MLE, and never auto-overwrites ValueProfile weights. "
            "See research/PREFERENCE_BT_STAGE2.md."
        ),
        "docs": "docs/LIMITS.md",
    }


def fit_bt_offline(
    events: Iterable[PreferenceEvent | dict[str, Any]] | str | Path,
    *,
    profile_name: str | None = None,
    min_pairs: int = 30,
) -> dict[str, Any]:
    """
    Offline Bradley–Terry readiness check (eval only).

    Does **not** fit skills until pair count ≥ min_pairs; never rewrites weights.
    """
    evs = normalize_preference_events(events)
    if profile_name:
        evs = [e for e in evs if (e.profile_name or "") == profile_name or not e.profile_name]
    pairs = 0
    ties = 0
    for ev in evs:
        et = (ev.event_type or "").lower()
        if et in ("tie", "both_keep"):
            ties += 1
        for _ in ev.preferred_over_ids or []:
            pairs += 1
    ready = pairs >= min_pairs
    return {
        "ok": ready,
        "n_pairs": pairs,
        "n_ties": ties,
        "min_pairs": min_pairs,
        "skills": None,
        "reason": None if ready else "insufficient_pairs_for_stable_bt",
        "honesty": (
            "BT fit is eval-only and gated on pair volume. This call does not "
            "auto-overwrite ValueProfile weights. Prefer axis weight hints until ready."
        ),
        "docs": "docs/LIMITS.md",
    }
