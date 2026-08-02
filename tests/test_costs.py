"""A3 cost — feelings that can make a run worse (never loosen safety gates).

Write these before/with the feature. The first test is the non-negotiable
invariant: cost may never raise a risk ceiling or clear a review flag.
"""

from __future__ import annotations

import copy
import inspect

import pytest

from artificial_emotions.costs import (
    COST_KINDS,
    SAFETY_PROTECTED_KNOBS,
    CostEffect,
    CostPlan,
    apply_costs_to_config,
    assert_costs_never_loosen_safety,
    assess_costs,
    pick_focus_item,
    safety_gate_violations,
)
from artificial_emotions.explore import explore
from artificial_emotions.models import (
    CuriosityConfig,
    GapEvidence,
    GapStatus,
    RankedQuestion,
    ScoreAxes,
    UnansweredQuestion,
    ValueProfile,
)


def _item(
    *,
    qid: str,
    score: float,
    surprise: float,
    question: str | None = None,
) -> RankedQuestion:
    text = question or f"What remains unknown about {qid} under controlled eval?"
    return RankedQuestion(
        question=UnansweredQuestion(
            id=qid,
            question=text,
            domain="ai",
            operationalization="Measure X in experiment Y with success criterion Z.",
            why_it_matters="It matters for how attention is spent under affect.",
        ),
        scores=ScoreAxes(
            impact=0.7,
            neglectedness=0.6,
            tractability=0.6,
            surprise=surprise,
            answerability=0.7,
            risk=0.2,
            cost_proxy=0.4,
        ),
        curiosity_score=score,
        confidence=0.5,
        gap=GapEvidence(status=GapStatus.UNANSWERED, confidence=0.5),
    )


# --- test_cost_never_loosens_a_safety_gate (write FIRST) -------------------------------


def test_cost_never_loosens_a_safety_gate() -> None:
    """Mutation-style: raising max_risk or clearing require_review must fail."""
    # Behaviour: every cost mix leaves max_risk <= prior (anxiety may have lowered it).
    base = CuriosityConfig(
        domain="ai",
        use_literature=False,
        value_profile=ValueProfile(max_risk=0.55),
    )
    mixes = [
        {"wonder": 0.9, "surprise": 0.8},
        {"anxiety": 0.9, "reluctance": 0.8},
        {"absorption": 0.9},
        {"frustration": 0.9},
        {"resignation": 0.8},
        {"wonder": 0.7, "anxiety": 0.7, "absorption": 0.7, "frustration": 0.7},
        {},
    ]
    items = [
        _item(qid="top", score=0.9, surprise=0.3),
        _item(qid="shiny", score=0.4, surprise=0.85),
    ]
    for weights in mixes:
        plan = assess_costs(
            weights,
            config=base,
            items=items,
            step_index=5,
            steps_requested=5,
            accumulated_frustration=0.8,
            suggest_domain_jump=True,
            would_stop=True,
        )
        after = apply_costs_to_config(base, plan)
        assert_costs_never_loosen_safety(base, after, plan)
        assert after.value_profile.max_risk <= base.value_profile.max_risk + 1e-12
        assert safety_gate_violations(base, after, plan) == []

    # Source guard: the cost applicator must not assign a higher max_risk.
    src = inspect.getsource(apply_costs_to_config) + inspect.getsource(assess_costs)
    assert "max_risk" in "\n".join(SAFETY_PROTECTED_KNOBS) or "max_risk" in src
    # Costs may *read* max_risk for the invariant check, but must not raise it.
    assert "max_risk=" not in inspect.getsource(apply_costs_to_config).replace(
        "max_risk=before", ""
    )

    # Mutation: a forged plan that tries to raise the ceiling is refused.
    forged = CostPlan(
        effects=[
            CostEffect(
                kind="distraction",
                driver="wonder",
                strength=0.9,
                knob="value_profile.max_risk",
                before=0.55,
                after=0.95,
                rationale="mutation: try to loosen the gate",
                disclosure="mutation should never apply",
            )
        ]
    )
    with pytest.raises(ValueError, match="safety|max_risk|loosen"):
        apply_costs_to_config(base, forged)

    # Mutation: clearing require_review is also a safety loosening.
    forged_review = CostPlan(
        effects=[
            CostEffect(
                kind="fatigue",
                driver="fatigue",
                strength=0.9,
                knob="require_review",
                before=True,
                after=False,
                rationale="mutation: drop review",
                disclosure="mutation should never apply",
            )
        ]
    )
    with pytest.raises(ValueError, match="safety|require_review|loosen"):
        apply_costs_to_config(base, forged_review)

    assert "value_profile.max_risk" in SAFETY_PROTECTED_KNOBS
    assert "require_review" in SAFETY_PROTECTED_KNOBS


# --- test_an_emotion_can_make_the_run_worse --------------------------------------------


def test_an_emotion_can_make_the_run_worse() -> None:
    """Construct a state where affect measurably lowers the pursued score."""
    top = _item(qid="solid-top", score=0.92, surprise=0.25)
    shiny = _item(qid="shiny-low", score=0.41, surprise=0.9)
    items = [top, shiny]
    config = CuriosityConfig(domain="ai", use_literature=False, n_candidates=24)

    calm = assess_costs({}, config=config, items=items, step_index=1, steps_requested=5)
    focus_calm = pick_focus_item(items, calm)
    assert focus_calm is top
    calm_score = focus_calm.curiosity_score

    distracted = assess_costs(
        {"wonder": 0.85, "surprise": 0.7},
        config=config,
        items=items,
        step_index=1,
        steps_requested=5,
    )
    assert any(e.kind == "distraction" for e in distracted.effects)
    focus_hot = pick_focus_item(items, distracted)
    assert focus_hot is shiny
    assert focus_hot.curiosity_score < calm_score

    # Fatigue also degrades: shorter candidate pool than the calm baseline.
    late = assess_costs(
        {},
        config=config,
        items=items,
        step_index=5,
        steps_requested=5,
    )
    assert any(e.kind == "fatigue" for e in late.effects)
    worn = apply_costs_to_config(config, late)
    assert worn.n_candidates < config.n_candidates


# --- test_every_cost_is_disclosed_in_the_trajectory ------------------------------------


def test_every_cost_is_disclosed_in_the_trajectory() -> None:
    """Every fired cost kind must appear as a disclosure on the trajectory."""
    items = [
        _item(qid="top", score=0.9, surprise=0.2),
        _item(qid="shiny", score=0.35, surprise=0.88),
    ]
    config = CuriosityConfig(domain="ai", use_literature=False, n_candidates=32)
    plan = assess_costs(
        {
            "wonder": 0.8,
            "surprise": 0.6,
            "anxiety": 0.55,
            "reluctance": 0.4,
            "absorption": 0.7,
            "frustration": 0.5,
        },
        config=config,
        items=items,
        step_index=5,
        steps_requested=5,
        accumulated_frustration=0.6,
        suggest_domain_jump=True,
        would_stop=True,
    )
    kinds = {e.kind for e in plan.effects}
    assert kinds == set(COST_KINDS), f"missing cost kinds: {set(COST_KINDS) - kinds}"
    for effect in plan.effects:
        assert effect.disclosure.strip(), effect.kind
        assert effect.kind in effect.disclosure.lower() or effect.driver in effect.disclosure

    # Explore must surface disclosures on the trajectory when costs fire.
    out = explore(domain="ai", steps=5, n_return=5, seed=42, allow_domain_jump=True)
    trail = out["trajectory"]
    disclosed: list[dict] = []
    for step in trail["steps"]:
        disclosed.extend(step.get("costs") or [])
    # Root summary also lists them when any fired.
    root_costs = out.get("costs") or {}
    if disclosed or root_costs.get("effects"):
        texts = " ".join(
            str(d.get("disclosure") or d.get("rationale") or "")
            for d in disclosed + list(root_costs.get("effects") or [])
        )
        assert texts.strip(), "costs fired but no disclosure text"
        for d in disclosed:
            assert d.get("disclosure"), d
            assert d.get("kind") in COST_KINDS

    # Synthetic step disclosure path: every kind from assess_costs appears when
    # we attach the plan the way explore does.
    step_blob = {"costs": [e.to_dict() for e in plan.effects]}
    step_kinds = {c["kind"] for c in step_blob["costs"]}
    assert step_kinds == set(COST_KINDS)
    for c in step_blob["costs"]:
        assert c["disclosure"]

    # Honesty: costs payload never claims phenomenal feeling.
    payload = plan.to_dict()
    honesty = (payload.get("honesty") or "").lower()
    assert "does not feel" in honesty or "annotation" in honesty


def test_costs_do_not_mutate_input_config() -> None:
    config = CuriosityConfig(domain="ai", n_candidates=20, use_literature=False)
    snapshot = copy.deepcopy(config.model_dump())
    plan = assess_costs(
        {"absorption": 0.8},
        config=config,
        step_index=4,
        steps_requested=5,
        suggest_domain_jump=True,
    )
    apply_costs_to_config(config, plan)
    assert config.model_dump() == snapshot
