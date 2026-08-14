"""Catalog-driven appraisal interpreter vs the existing RULES lambdas.

The catalog is the runtime contract. ``RULES`` lambdas stay a characterization
golden for ``evaluate_when`` (exact set, weights ``abs=1e-6``). Dispatch must
not consult ``RULES`` at runtime.

Tolerance (measured against the ported formulas, not guessed):

* Emotion set: exact match on FIRING_CONTEXTS, a neutral context, and the
  6-step x 5-domain offline explore suite.
* Weights: ``abs=1e-6`` (formulas copied; float rounding only).
* Evidence keys: catalog feature names, not RULES aliases
  (``open_gap_ratio`` vs ``gap_ratio``). Not compared.
* ``because``: catalog ``use_for`` (not the RULES why-string).
"""

from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

import pytest
from tests.test_appraisal_coverage import _OFFLINE_EXPLORE_DOMAINS, FIRING_CONTEXTS

from artificial_emotions.appraisal import (
    RULES,
    AppraisalContext,
    appraise_run,
    build_context,
    evaluate_when,
)
from artificial_emotions.emotions import emotion_catalog
from artificial_emotions.models import CuriosityConfig
from artificial_emotions.pipeline import CuriosityEngine

_MIN_SIGNAL = 0.04
_WEIGHT_TOLERANCE = 1e-6
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


def _rule_weights(ctx: AppraisalContext) -> dict[str, float]:
    out: dict[str, float] = {}
    for emotion, (_why, rule) in RULES.items():
        got = rule(ctx)
        if got is None:
            continue
        weight, _evidence = got
        if weight >= _MIN_SIGNAL:
            out[emotion] = float(weight)
    return out


def _catalog_weights(ctx: AppraisalContext, by_id: dict[str, dict]) -> dict[str, float]:
    """Weights from catalog ``when`` via ``evaluate_when`` — never RULES fallback."""
    out: dict[str, float] = {}
    for emotion in RULES:
        when = by_id[emotion].get("when") or []
        if not when:
            continue
        weight = evaluate_when(ctx, when)
        if weight is not None and weight >= _MIN_SIGNAL:
            out[emotion] = float(weight)
    return out


def _assert_weights_match(
    rules_w: dict[str, float], cat_w: dict[str, float], *, label: str
) -> None:
    assert set(cat_w) == set(rules_w), {
        "label": label,
        "catalog_only": sorted(set(cat_w) - set(rules_w)),
        "rules_only": sorted(set(rules_w) - set(cat_w)),
    }
    for emotion, expected in rules_w.items():
        assert cat_w[emotion] == pytest.approx(expected, abs=_WEIGHT_TOLERANCE), (
            f"{label}: {emotion} catalog {cat_w[emotion]} vs rules {expected}"
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


@pytest.mark.parametrize("emotion", sorted(RULES))
def test_catalog_when_matches_rules_on_firing_fixtures(
    emotion: str, neutral_context: AppraisalContext
):
    by_id = _catalog_by_id()
    ctx = replace(neutral_context, **FIRING_CONTEXTS[emotion])
    rules_w = _rule_weights(ctx)
    cat_w = _catalog_weights(ctx, by_id)
    assert emotion in rules_w
    _assert_weights_match(rules_w, cat_w, label=f"firing:{emotion}")


@pytest.mark.parametrize("emotion", sorted(RULES))
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
    """Characterization: empty ``when`` is skip, not a RULES-lambda fallback."""
    by_id = _catalog_by_id()
    ctx = replace(neutral_context, **FIRING_CONTEXTS["curiosity"])
    assert "curiosity" in _rule_weights(ctx)
    patched = {**by_id, "curiosity": {**by_id["curiosity"], "when": []}}
    assert "curiosity" not in _catalog_weights(ctx, patched)


def test_empty_when_does_not_fire_even_if_rules_would(monkeypatch: pytest.MonkeyPatch, ranked_ai):
    """Runtime: emptying catalog ``when`` must not consult the RULES lambda."""
    import copy

    from artificial_emotions import emotions as emotions_mod

    clone = copy.deepcopy(emotion_catalog())
    for entry in clone["emotions"]:
        if entry["id"] == "curiosity":
            entry["when"] = []
            break
    monkeypatch.setattr(emotions_mod, "emotion_catalog", lambda: clone)
    ctx = build_context(ranked_ai)
    rules_out = RULES["curiosity"][1](ctx)
    assert rules_out is not None and rules_out[0] >= _MIN_SIGNAL
    signals = appraise_run(ranked_ai)
    assert "curiosity" not in {s.emotion for s in signals}


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


def test_six_step_five_domain_catalog_matches_rules(monkeypatch: pytest.MonkeyPatch):
    """Live 6 x 5 offline explore: catalog ``when`` vs RULES lambdas via evaluate_when."""
    from artificial_emotions import explore as explore_mod
    from artificial_emotions.appraisal import build_context
    from artificial_emotions.explore import explore

    by_id = _catalog_by_id()
    original = explore_mod.appraise_run
    mismatches: list[str] = []
    compared = 0

    def wrapped(items, **kwargs):
        nonlocal compared
        if items:
            ctx = build_context(
                items,
                seen_question_ids=kwargs.get("seen_question_ids"),
                term_saturation=float(kwargs.get("term_saturation") or 0.0),
                steps_without_progress=int(kwargs.get("steps_without_progress") or 0),
                rejected_count=int(kwargs.get("rejected_count") or 0),
                previous_top_id=kwargs.get("previous_top_id"),
            )
            try:
                _assert_weights_match(
                    _rule_weights(ctx),
                    _catalog_weights(ctx, by_id),
                    label=f"explore-step-{compared}",
                )
            except AssertionError as exc:
                mismatches.append(str(exc))
            compared += 1
        return original(items, **kwargs)

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
    assert not mismatches, "catalog vs RULES mismatches:\n" + "\n".join(mismatches)
