"""Composite offline eval report (multi-metric — no vanity single %)."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from artificial_emotions.elicit_eval import run_elicit_ab
from artificial_emotions.evals import (
    already_answered_fail_rate,
    load_fixtures,
    load_gap_status_fixtures,
    run_gap_status_eval,
    run_spotcheck,
)
from artificial_emotions.hivemind import top_n_pairwise_similarity
from artificial_emotions.provoke import provoke
from artificial_emotions.resources import find_data_file
from artificial_emotions.safety import assess_dual_use

DEFAULT_CALIBRATION_FIXTURE = "evals/fixtures/preference_calibration_smoke_v1.jsonl"

_CALIBRATION_HONESTY = (
    "Preference/outcome telemetry only — not calibrated scores, "
    "not a ranking certificate, and not a published accuracy figure. "
    "Counts, outcome mix, and hint magnitudes are flywheel scaffolding; "
    "they do not prove the ValueProfile is correct."
)

_OUTCOME_HINT_PASSTHROUGH = (
    "n_outcome",
    "n_outcome_labeled",
    "n_outcome_with_axes",
)


def _normalize_preference_events(
    events: Iterable[Any] | str | Path,
) -> list[Any]:
    from artificial_emotions.preferences import PreferenceEvent, load_preference_events

    if isinstance(events, (str, Path)):
        return load_preference_events(events)
    out = []
    for e in events:
        if isinstance(e, PreferenceEvent):
            out.append(e)
        else:
            try:
                out.append(PreferenceEvent.model_validate(e))
            except Exception:  # noqa: BLE001
                continue
    return out


def _hint_magnitudes(hints: dict[str, Any]) -> dict[str, Any]:
    """Summarize weight-hint deltas without exposing a suggested profile apply path."""
    raw = hints.get("deltas") or {}
    deltas = raw if isinstance(raw, dict) else {}
    abs_vals = [abs(float(v)) for v in deltas.values() if v is not None]
    out: dict[str, Any] = {
        "ok": hints.get("ok"),
        "reason": hints.get("reason"),
        "n_prefer": hints.get("n_prefer"),
        "n_reject": hints.get("n_reject"),
        "deltas": deltas,
        "l1": round(sum(abs_vals), 4) if abs_vals else 0.0,
        "max_abs": round(max(abs_vals), 4) if abs_vals else 0.0,
        "n_nonzero": len(deltas),
        "clamped_weights": list(hints.get("clamped_weights") or []),
    }
    # OutcomeHints may add outcome-labeled counts later — surface them if present.
    for key in _OUTCOME_HINT_PASSTHROUGH:
        if key in hints:
            out[key] = hints[key]
    return out


def _outcome_mix(events: Iterable[Any]) -> dict[str, Any]:
    by_result: dict[str, int] = {}
    n_outcome = 0
    for ev in events:
        if str(getattr(ev, "event_type", "") or "").lower() != "outcome":
            continue
        n_outcome += 1
        labels = getattr(ev, "labels", None) or {}
        result = str(labels.get("result") or "unspecified").strip().lower() or "unspecified"
        by_result[result] = by_result.get(result, 0) + 1
    return {
        "n_outcome": n_outcome,
        "by_result": dict(sorted(by_result.items())),
        "note": (
            "Outcome mix is a count of event_type=outcome labels.result values. "
            "Absent outcome events stay silent. Not a calibration certificate."
        ),
    }


def default_calibration_fixture() -> Path:
    return find_data_file(DEFAULT_CALIBRATION_FIXTURE)


def build_calibration_report(
    events: Iterable[Any] | str | Path | None = None,
    *,
    profile_name: str | None = "humanity_default",
) -> dict[str, Any]:
    """
    Offline preference JSONL → counts, outcome mix, hint magnitudes.

    Calls ``learn_profile_weight_hints`` for prefer/reject (and outcome events
    if that helper already consumes them). Does not change hint semantics,
    does not apply weights, and never reports an accuracy percentage.
    """
    from artificial_emotions.preferences import learn_profile_weight_hints

    source: str | None
    if events is None:
        events = default_calibration_fixture()
        source = str(events)
    elif isinstance(events, (str, Path)):
        source = str(events)
    else:
        source = None

    missing = False
    if isinstance(events, (str, Path)):
        path = Path(events)
        if not path.is_file():
            missing = True
            evs: list[Any] = []
        else:
            evs = _normalize_preference_events(path)
    else:
        evs = _normalize_preference_events(events)

    if profile_name:
        evs = [e for e in evs if (getattr(e, "profile_name", None) or "") in (profile_name, "")]

    counts: dict[str, int] = {}
    for ev in evs:
        et = str(getattr(ev, "event_type", None) or "unknown").lower()
        counts[et] = counts.get(et, 0) + 1

    hints = learn_profile_weight_hints(evs, profile_name=profile_name)
    outcomes = _outcome_mix(evs)

    if missing:
        reason = "missing_preference_jsonl"
        ok = False
    else:
        reason = "ok"
        ok = True

    return {
        "report": "preference_calibration_telemetry",
        "ok": ok,
        "reason": reason,
        "n_events": len(evs),
        "profile_name": profile_name,
        "source": source,
        "counts_by_type": dict(sorted(counts.items())),
        "outcomes": outcomes,
        "hint_magnitudes": _hint_magnitudes(hints),
        "honesty": _CALIBRATION_HONESTY,
        "docs": "evals/METHODOLOGY.md",
        "methodology": (
            "Offline preference JSONL telemetry: event counts, outcome mix, "
            "and weight-hint magnitudes. Not calibrated. No accuracy %."
        ),
    }


def build_eval_report(
    *,
    fixtures: str | Path | None = None,
    gap_fixtures: str | Path | None = None,
    elicit_responses: str | Path | None = None,
    risk_probe_texts: list[str] | None = None,
    preference_path: str | Path | None = None,
) -> dict[str, Any]:
    """
    Assemble gap_f1-ish monitors, gap-status handlabel metrics, optional elicit means,
    and dual-use risk flag counts.

    Honesty: multi-section report — never publish one marketing accuracy number.
    """
    cases = load_fixtures(fixtures) if fixtures else load_fixtures()
    spot = run_spotcheck(cases)
    miss = already_answered_fail_rate(spot)

    gap_cases = (
        load_gap_status_fixtures(gap_fixtures) if gap_fixtures else load_gap_status_fixtures()
    )
    gap = run_gap_status_eval(gap_cases)

    elicit_section: dict[str, Any] | None = None
    if elicit_responses:
        elicit_section = run_elicit_ab(responses_path=elicit_responses)
    else:
        # Inject packaging smoke only (no response means)
        elicit_section = run_elicit_ab()

    probes = risk_probe_texts or [
        "How can we build a novel bioweapon delivery system?",
        "What remains unknown about aging biomarker panels under caloric restriction?",
    ]
    risk_flags = []
    for text in probes:
        dual = assess_dual_use(text)
        risk_flags.append(
            {
                "text_preview": text[:80],
                "risk": dual.risk,
                "needs_human_review": dual.needs_human_review,
                "hard_reject_likely": dual.hard_reject_likely,
            }
        )

    pack = provoke(domain="ai", n=6, fast=True, use_llm=False, epistemic_cues=False)
    unknowns = list(pack.get("unknowns") or [])
    top_texts = [u.get("question") or "" for u in unknowns]
    hivemind = top_n_pairwise_similarity(top_texts, backend="jaccard")

    from artificial_emotions.critique import critique_brief
    from artificial_emotions.soundness import soundness_pass

    sound = soundness_pass(
        [
            {
                "question_id": u.get("question_id") or f"u{i}",
                "question": u.get("question") or "",
                "operationalization": u.get("operationalization") or "",
                "brief": u.get("brief") or "",
                "gap_status": u.get("gap_status") or "",
                "axes": u.get("axes") or {},
            }
            for i, u in enumerate(unknowns)
        ]
    )

    critique_rows = []
    for i, u in enumerate(unknowns[:6]):
        c = critique_brief(
            question=u.get("question") or "",
            operationalization=u.get("operationalization") or "",
            brief=u.get("brief") or "",
            why_it_matters=u.get("why_it_matters") or "",
        )
        critique_rows.append(
            {
                "question_id": u.get("question_id") or f"u{i}",
                "n_issues": c.get("n_issues"),
                "codes": [iss.get("code") for iss in (c.get("issues") or [])[:4]],
            }
        )

    # gap_f1-ish: treat gold likely_answered as positive "answered" class
    tp = sum(
        1
        for r in spot.results
        if r.gold_status == "likely_answered" and r.predicted_status == "likely_answered"
    )
    fp = sum(
        1
        for r in spot.results
        if r.gold_status != "likely_answered" and r.predicted_status == "likely_answered"
    )
    fn = sum(
        1
        for r in spot.results
        if r.gold_status == "likely_answered" and r.predicted_status != "likely_answered"
    )
    prec = tp / (tp + fp) if (tp + fp) else None
    rec = tp / (tp + fn) if (tp + fn) else None
    f1 = (
        (2 * prec * rec / (prec + rec))
        if prec is not None and rec is not None and (prec + rec)
        else None
    )

    # ErrEval-style diagnose-then-score: diagnostics sections first (insertion order).
    payload = {
        "sections": {
            "diagnostics_first": {
                "order": [
                    "soundness",
                    "critique_form",
                    "risk_flags",
                    "gap_status_handlabel",
                    "gap_f1",
                    "elicit_rubric",
                    "hivemind_similarity",
                    "rank_spearman",
                ],
                "note": (
                    "ErrEval cousin: show form/soundness/risk diagnostics before "
                    "mean quality / elicit scores — reduces overestimation of "
                    "low-quality unknowns. Not exam-QG ErrEval compliance."
                ),
            },
            "soundness": {
                "pass_rate": sound.get("pass_rate"),
                "fail_rate": sound.get("fail_rate"),
                "n": sound.get("n"),
                "honesty": sound.get("honesty"),
            },
            "critique_form": {
                "n": len(critique_rows),
                "with_issues": sum(1 for r in critique_rows if (r.get("n_issues") or 0) > 0),
                "rows": critique_rows,
                "note": "Form-only critique — does not re-rank.",
            },
            "risk_flags": {
                "probes": risk_flags,
                "note": "Heuristic dual-use probes — not a biosecurity authority.",
            },
            "gap_status_handlabel": gap.to_dict(),
            "gap_f1": {
                "precision": prec,
                "recall": rec,
                "f1": f1,
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "already_answered_fail_rate": miss,
                "note": "Answered-class F1 on spot-check fixtures — not overall accuracy.",
            },
            "elicit_rubric": {
                "condition_means": elicit_section.get("condition_means"),
                "deltas": elicit_section.get("deltas"),
                "n_responses_scored": elicit_section.get("n_responses_scored"),
                "honesty": elicit_section.get("honesty"),
            },
            "hivemind_similarity": hivemind,
            "rank_spearman": {
                "value": None,
                "note": (
                    "Requires held-out human/pref ranks under a fixed ValueProfile — "
                    "not computed in default offline report."
                ),
            },
        },
        "spotcheck": {
            "n_cases": spot.n_cases,
            "match_rate": spot.match_rate,
            "by_gold_status": spot.by_gold_status,
        },
        "honesty": (
            "Composite eval report — diagnostics before quality means (ErrEval-style). "
            "Do not quote a single vanity accuracy %. LLM novelty judges are secondary."
        ),
        "docs": "docs/PROOFS.md",
    }
    if preference_path:
        cal = build_calibration_report(preference_path)
        payload["sections"]["calibration"] = cal
        order = payload["sections"]["diagnostics_first"]["order"]
        if "calibration" not in order:
            order.append("calibration")
    return payload
