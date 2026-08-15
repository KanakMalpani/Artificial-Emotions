"""Catalog-driven appraisal interpreter.

The catalog is the runtime contract. Production dispatch evaluates catalog
``when`` via ``evaluate_when``; empty ``when`` does not fire.

Keep:

* Emotion set: exact match on FIRING_CONTEXTS (named emotion fires) and the
  6-step x 5-domain offline explore suite (``evaluate_when`` vs ``appraise_run``).
* Weights: ``evaluate_when`` vs ``appraise_run`` on the same context must match.
* ``because``: catalog ``use_for``.
"""

from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

import pytest

from artificial_emotions.appraisal import (
    AppraisalContext,
    appraise_run,
    build_context,
    evaluate_when,
)
from artificial_emotions.emotions import emotion_catalog
from artificial_emotions.models import CuriosityConfig
from artificial_emotions.pipeline import CuriosityEngine
from tests.test_appraisal_coverage import _OFFLINE_EXPLORE_DOMAINS, FIRING_CONTEXTS

_MIN_SIGNAL = 0.04
_TWELVE_LEFTOVERS = frozenset(
    {
        "anger",
        "fear",
        "joy",
        "sadness",
        "disgust",
        "gratitude",
        "pride",
        "shame",
        "embarrassment",
        "relief",
        "intrigue",
        "admiration",
    }
)


def _catalog_by_id() -> dict[str, dict]:
    return {str(e["id"]): e for e in emotion_catalog()["emotions"]}


def _evaluate_when_weights(ctx: AppraisalContext, by_id: dict[str, dict]) -> dict[str, float]:
    """Weights from catalog ``when`` via ``evaluate_when``."""
    out: dict[str, float] = {}
    for emotion, entry in by_id.items():
        when = entry.get("when") or []
        if not when:
            continue
        weight = evaluate_when(ctx, when)
        if weight is not None and weight >= _MIN_SIGNAL:
            out[emotion] = float(weight)
    return out


def _signal_weights(signals) -> dict[str, float]:
    return {s.emotion: float(s.weight) for s in signals if s.weight >= _MIN_SIGNAL}


def _assert_when_matches_appraise(ctx: AppraisalContext, signals, *, label: str) -> None:
    when_w = _evaluate_when_weights(ctx, _catalog_by_id())
    run_w = _signal_weights(signals)
    assert set(when_w) == set(run_w), {
        "label": label,
        "evaluate_when_only": sorted(set(when_w) - set(run_w)),
        "appraise_run_only": sorted(set(run_w) - set(when_w)),
    }
    for emotion, expected in when_w.items():
        assert run_w[emotion] == expected, (
            f"{label}: {emotion} evaluate_when {expected} vs appraise_run {run_w[emotion]}"
        )


@pytest.fixture(scope="module")
def neutral_context() -> AppraisalContext:
    items = CuriosityEngine(
        CuriosityConfig(domain="ai", use_llm=False, use_literature=False, n_return=5)
    ).run()
    ctx = build_context(items)
    return replace(
        ctx,
        gap_ratio=0.0,
        mean_impact=0.3,
        mean_neglect=0.3,
        mean_surprise=0.2,
        mean_tractability=0.4,
        mean_answerability=0.6,
        mean_risk=0.1,
        mean_confidence=0.5,
        mean_cost=0.6,
        max_risk=0.1,
        disagreement=0.0,
        band_width=0.2,
        score_spread=0.0,
        top_score=0.3,
        top_answerability=0.4,
        top_ops_len=200,
        top_clause_count=1,
        thin_evidence=0.0,
        dense_yet_open=0.0,
        answered_ratio=0.0,
        dual_use_ratio=0.0,
        ungrounded_ratio=0.0,
        duplicate_ratio=0.0,
        repeat_ratio=0.0,
        mean_related=0.0,
        mean_citations=0.0,
        term_saturation=0.0,
        steps_without_progress=0,
        rejected_ratio=0.0,
        top_repeated=False,
    )


def test_evaluate_when_empty_is_not_catalog_driven(neutral_context: AppraisalContext):
    assert evaluate_when(neutral_context, []) is None
    assert evaluate_when(neutral_context, None) is None


def test_missing_previous_feature_fails_closed(neutral_context: AppraisalContext):
    when = [{"feature": "previous.max_risk", "op": "ge", "value": 0.5, "weight": 0.4}]
    assert evaluate_when(neutral_context, when) is None


def test_previous_and_outcome_read_nested_or_flat():
    when_prev = [{"feature": "previous.max_risk", "op": "ge", "value": 0.5, "weight": 0.4}]
    when_out = [{"feature": "outcome.result", "op": "eq", "value": "answered", "weight": 0.3}]
    nested = SimpleNamespace(previous=SimpleNamespace(max_risk=0.9), outcome=None)
    as_map = SimpleNamespace(previous={"max_risk": 0.9, "hubris": 0.2, "top_id": "q1"})
    flat = SimpleNamespace(previous_max_risk=0.9)
    outcome = SimpleNamespace(outcome={"result": "answered", "question_id": "q1"})
    assert evaluate_when(nested, when_prev) == pytest.approx(0.4)
    assert evaluate_when(as_map, when_prev) == pytest.approx(0.4)
    assert evaluate_when(flat, when_prev) == pytest.approx(0.4)
    assert evaluate_when(outcome, when_out) == pytest.approx(0.3)
    assert evaluate_when(SimpleNamespace(outcome=None), when_out) is None


@pytest.mark.parametrize("emotion", sorted(FIRING_CONTEXTS))
def test_named_emotion_fires_on_firing_fixture(emotion: str, neutral_context: AppraisalContext):
    ctx = replace(neutral_context, **FIRING_CONTEXTS[emotion])
    weights = _evaluate_when_weights(ctx, _catalog_by_id())
    assert emotion in weights


@pytest.mark.parametrize("emotion", sorted(FIRING_CONTEXTS))
def test_catalog_when_stays_quiet_on_neutral_context(
    emotion: str, neutral_context: AppraisalContext
):
    by_id = _catalog_by_id()
    weight = evaluate_when(neutral_context, by_id[emotion]["when"])
    if weight is not None:
        assert weight < _MIN_SIGNAL, f"{emotion} catalog-fires on a neutral run ({weight})"


def test_twelve_leftovers_do_not_fire_from_appraise_run():
    items = CuriosityEngine(
        CuriosityConfig(domain="ai", use_llm=False, use_literature=False, n_return=5)
    ).run()
    fired = {s.emotion for s in appraise_run(items)}
    assert not (fired & _TWELVE_LEFTOVERS)


@pytest.fixture(scope="module")
def ranked_ai():
    return CuriosityEngine(
        CuriosityConfig(domain="ai", use_llm=False, use_literature=False, n_return=5)
    ).run()


def test_catalog_weights_skip_empty_when(neutral_context: AppraisalContext):
    """Empty ``when`` is skip — not a fire."""
    by_id = _catalog_by_id()
    ctx = replace(neutral_context, **FIRING_CONTEXTS["curiosity"])
    assert "curiosity" in _evaluate_when_weights(ctx, by_id)
    patched = {**by_id, "curiosity": {**by_id["curiosity"], "when": []}}
    assert "curiosity" not in _evaluate_when_weights(ctx, patched)


def test_empty_when_does_not_fire_even_if_evaluate_when_would(
    monkeypatch: pytest.MonkeyPatch, ranked_ai
):
    """Runtime: emptying catalog ``when`` must omit the id even when evaluate_when would fire."""
    import copy

    from artificial_emotions import appraisal as appraisal_mod

    by_id = _catalog_by_id()
    ctx = build_context(ranked_ai)
    live = evaluate_when(ctx, by_id["curiosity"]["when"])
    assert live is not None and live >= _MIN_SIGNAL

    clone = copy.deepcopy(emotion_catalog())
    for entry in clone["emotions"]:
        if entry["id"] == "curiosity":
            entry["when"] = []
            break
    patched = {str(e["id"]): e for e in clone["emotions"]}
    monkeypatch.setattr(appraisal_mod, "_catalog_by_id", lambda: patched)
    signals = appraise_run(ranked_ai)
    assert "curiosity" not in {s.emotion for s in signals}


def test_evaluate_when_matches_appraise_run_on_ranked(ranked_ai):
    ctx = build_context(ranked_ai)
    signals = appraise_run(ranked_ai)
    _assert_when_matches_appraise(ctx, signals, label="ranked-ai")


def test_appraise_run_because_matches_catalog_use_for(ranked_ai):
    """Catalog-driven ``because`` is ``use_for``. Empty-items special case is not this path."""
    by_id = _catalog_by_id()
    runs = [
        appraise_run(ranked_ai),
        appraise_run(ranked_ai, seen_question_ids={i.question.id for i in ranked_ai}),
        appraise_run(ranked_ai, steps_without_progress=3),
    ]
    checked: set[str] = set()
    for signals in runs:
        assert signals
        for signal in signals:
            expected = str(by_id[signal.emotion]["use_for"]).strip()
            assert expected, signal.emotion
            assert signal.because == expected, {
                "emotion": signal.emotion,
                "because": signal.because,
                "use_for": expected,
            }
            checked.add(signal.emotion)
    assert checked


def test_six_step_five_domain_evaluate_when_matches_appraise_run(
    monkeypatch: pytest.MonkeyPatch,
):
    """Live 6 x 5 offline explore: catalog ``when`` vs ``appraise_run`` weights."""
    from artificial_emotions import explore as explore_mod
    from artificial_emotions.appraisal import build_context
    from artificial_emotions.explore import explore

    original = explore_mod.appraise_run
    mismatches: list[str] = []
    compared = 0

    def wrapped(items, **kwargs):
        nonlocal compared
        signals = original(items, **kwargs)
        if items:
            ctx = build_context(
                items,
                seen_question_ids=kwargs.get("seen_question_ids"),
                term_saturation=float(kwargs.get("term_saturation") or 0.0),
                steps_without_progress=int(kwargs.get("steps_without_progress") or 0),
                rejected_count=int(kwargs.get("rejected_count") or 0),
                previous_top_id=kwargs.get("previous_top_id"),
                previous_max_risk=float(kwargs.get("previous_max_risk") or 0.0),
                previous_hubris=float(kwargs.get("previous_hubris") or 0.0),
                outcome_result=str(kwargs.get("outcome_result") or ""),
                outcome_question_id=str(kwargs.get("outcome_question_id") or ""),
            )
            try:
                _assert_when_matches_appraise(ctx, signals, label=f"explore-step-{compared}")
            except AssertionError as exc:
                mismatches.append(str(exc))
            compared += 1
        return signals

    monkeypatch.setattr(explore_mod, "appraise_run", wrapped)
    for domain in _OFFLINE_EXPLORE_DOMAINS:
        explore(
            domain=domain,
            steps=6,
            n_return=5,
            use_literature=False,
            use_llm=False,
            seed=42,
            persist_memory=False,
        )
    assert compared >= 5 * 1, f"expected a 6-step x 5-domain suite, compared {compared} steps"
    assert not mismatches, "evaluate_when vs appraise_run mismatches:\n" + "\n".join(mismatches)
