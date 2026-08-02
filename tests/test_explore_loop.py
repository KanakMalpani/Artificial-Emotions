"""The curiosity loop: appraisal, memory, modulation, and the honesty bounds.

Two tests here carry more weight than the rest.

``test_value_profile_is_untouched_by_default`` is the invariant: affect may
change how the engine *searches*, but the score must stay a pure function of the
ValueProfile you stated. If affect ever silently moves a weight, this project has
smuggled hidden values into the one tool built to refuse them.

``test_every_signal_carries_its_evidence`` is the other: affect you cannot audit
is affect you cannot trust.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from artificial_emotions.api import app
from artificial_emotions.appraisal import (
    APPRAISAL_RULES,
    AppraisalSignal,
    appraise_run,
    signals_to_weights,
)
from artificial_emotions.explore import MAX_STEPS, explore
from artificial_emotions.models import CuriosityConfig
from artificial_emotions.modulate import MAX_WEIGHT_DELTA, modulate_config
from artificial_emotions.pipeline import CuriosityEngine
from artificial_emotions.trajectory import Trajectory, TrajectoryStep, question_terms


@pytest.fixture(scope="module")
def ranked():
    return CuriosityEngine(
        CuriosityConfig(domain="ai", use_llm=False, use_literature=False, n_return=5)
    ).run()


# --- appraisal: emotion as output ----------------------------------------------------


def test_appraisal_derives_affect_from_the_run_not_the_caller(ranked):
    signals = appraise_run(ranked)
    assert signals
    assert {s.emotion for s in signals} <= set(APPRAISAL_RULES) | {"disorientation"}


def test_every_signal_carries_its_evidence(ranked):
    """Affect you cannot audit is affect you cannot trust."""
    for signal in appraise_run(ranked):
        assert signal.because, signal.emotion
        assert signal.evidence, signal.emotion
        assert 0.0 < signal.weight <= 1.0


def test_an_offline_heuristic_run_appraises_itself_as_humble(ranked):
    """Thin evidence plus low confidence is exactly the humility rule."""
    emotions = {s.emotion for s in appraise_run(ranked)}
    assert "humility" in emotions
    assert "hubris" not in emotions


def test_empty_run_reads_as_disorientation():
    signals = appraise_run([])
    assert {s.emotion for s in signals} == {"disorientation", "confusion"}


def test_seen_questions_produce_boredom(ranked):
    seen = {i.question.id for i in ranked}
    fresh = {s.emotion for s in appraise_run(ranked)}
    stale = {s.emotion for s in appraise_run(ranked, seen_question_ids=seen)}
    assert "boredom" not in fresh
    assert "boredom" in stale


def test_repeated_dead_ends_produce_frustration(ranked):
    emotions = {s.emotion for s in appraise_run(ranked, steps_without_progress=3)}
    assert "frustration" in emotions


def test_signals_to_weights_keeps_the_mix_legible(ranked):
    weights = signals_to_weights(appraise_run(ranked), max_components=3)
    assert 1 <= len(weights) <= 3


def test_signals_to_weights_never_returns_empty():
    assert signals_to_weights([]) == {"curiosity": 1.0}


def test_appraisal_is_deterministic(ranked):
    a = [s.to_dict() for s in appraise_run(ranked)]
    b = [s.to_dict() for s in appraise_run(ranked)]
    assert a == b


# --- trajectory: the past that makes boredom possible --------------------------------


def test_trajectory_records_what_was_seen(ranked):
    trail = Trajectory()
    new = trail.observe(ranked)
    assert len(new) == len(ranked)
    assert trail.observe(ranked) == []  # nothing new the second time


def test_term_saturation_rises_with_repetition(ranked):
    trail = Trajectory()
    terms = question_terms(ranked[0].question.question)
    assert trail.term_saturation(terms) == 0.0
    trail.observe(ranked)
    assert trail.term_saturation(terms) > 0.5


def test_term_saturation_of_nothing_is_zero():
    assert Trajectory().term_saturation([]) == 0.0


def test_steps_without_progress_counts_only_the_trailing_run():
    trail = Trajectory()
    for made_progress in (True, False, False):
        trail.record(
            TrajectoryStep(
                step=len(trail.steps) + 1,
                domain="ai",
                topic="",
                n_returned=1,
                top_question_id="q",
                top_question="q?",
                top_score=0.5,
                made_progress=made_progress,
            )
        )
    assert trail.steps_without_progress() == 2
    assert trail.is_exhausted(threshold=2)


# --- modulation: the honesty bounds ---------------------------------------------------


def test_value_profile_is_untouched_by_default():
    """The invariant: affect changes search, never the stated scoring weights."""
    config = CuriosityConfig(domain="ai", use_literature=False)
    new_config, plan = modulate_config(config, {"curiosity": 0.8, "boredom": 0.5})
    assert plan.weights_touched is False
    assert new_config.value_profile == config.value_profile
    assert not any("value_profile" in c.knob for c in plan.changes)


def test_opt_in_weight_deltas_are_bounded_and_logged():
    config = CuriosityConfig(domain="ai", use_literature=False)
    new_config, plan = modulate_config(
        config, {"curiosity": 1.0, "confusion": 1.0, "boredom": 1.0}, allow_weight_deltas=True
    )
    assert plan.weights_touched is True
    weight_changes = [c for c in plan.changes if c.knob.startswith("value_profile.")]
    assert weight_changes
    for change in weight_changes:
        assert abs(float(change.after) - float(change.before)) <= MAX_WEIGHT_DELTA + 1e-9
        assert change.bounded_by
    assert new_config.value_profile != config.value_profile


def test_modulation_never_mutates_the_input_config():
    config = CuriosityConfig(domain="ai", n_candidates=16, use_literature=False)
    modulate_config(config, {"curiosity": 0.9}, allow_weight_deltas=True)
    assert config.n_candidates == 16


def test_curiosity_widens_the_search():
    config = CuriosityConfig(domain="ai", n_candidates=16)
    new_config, _ = modulate_config(config, {"curiosity": 0.8})
    assert new_config.n_candidates > 16


def test_confusion_narrows_and_forces_decomposition():
    config = CuriosityConfig(domain="ai", n_return=10)
    new_config, plan = modulate_config(config, {"confusion": 0.7})
    assert new_config.n_return < 10
    assert plan.force_decompose is True


def test_hubris_makes_the_system_demand_evidence_of_itself():
    config = CuriosityConfig(domain="ai", use_literature=False)
    new_config, plan = modulate_config(config, {"hubris": 0.6})
    assert new_config.use_literature is True
    assert any(c.driver == "hubris" for c in plan.changes)


def test_boredom_suggests_changing_ground():
    _cfg, plan = modulate_config(CuriosityConfig(domain="ai"), {"boredom": 0.5})
    assert plan.suggest_domain_jump is True


def test_frustration_stops_the_loop():
    _cfg, plan = modulate_config(CuriosityConfig(domain="ai"), {"frustration": 0.5})
    assert plan.stop is True
    assert "frustration" in plan.stop_reason


def test_every_change_names_its_driver_and_rationale():
    _cfg, plan = modulate_config(
        CuriosityConfig(domain="ai", use_literature=False),
        {"curiosity": 0.8, "confusion": 0.4, "boredom": 0.4, "hubris": 0.4},
    )
    assert plan.changes
    for change in plan.changes:
        assert change.driver
        assert change.rationale


def test_a_flat_affect_changes_nothing():
    config = CuriosityConfig(domain="ai", use_literature=False)
    new_config, plan = modulate_config(config, {"interest": 0.05})
    assert plan.changes == []
    assert new_config.n_candidates == config.n_candidates


# --- the loop -------------------------------------------------------------------------


def test_explore_produces_a_trajectory_with_reasons():
    out = explore(domain="ai", steps=3, n_return=4)
    steps = out["trajectory"]["steps"]
    assert 1 <= len(steps) <= 3
    for step in steps:
        assert step["appraisal"]
        assert step["note"]
        assert step["primary_feeling"]


def test_explore_remembers_and_gets_bored():
    """Re-running the same ground must stop feeling novel."""
    out = explore(domain="ai", steps=3, n_return=4, allow_domain_jump=False)
    later = out["trajectory"]["steps"][-1]
    assert any(a["emotion"] == "boredom" for a in later["appraisal"])
    assert later["new_question_ids"] == []


def test_boredom_changes_ground_when_jumping_is_allowed():
    out = explore(domain="ai", steps=4, n_return=4, allow_domain_jump=True)
    assert len(out["trajectory"]["domains_visited"]) > 1


def test_domain_stays_put_when_jumping_is_disallowed():
    out = explore(domain="ai", steps=4, n_return=4, allow_domain_jump=False)
    assert out["trajectory"]["domains_visited"] == ["ai"]


def test_explore_ends_with_an_investigation_plan():
    out = explore(domain="ai", steps=2, n_return=4)
    plan = out["investigation_plan"]
    assert plan is not None
    assert plan["assertion_free"] is True


def test_explore_is_deterministic():
    a = json.dumps(explore(domain="ai", steps=3, n_return=4), sort_keys=True)
    b = json.dumps(explore(domain="ai", steps=3, n_return=4), sort_keys=True)
    assert a == b


def test_steps_are_clamped():
    assert explore(domain="ai", steps=99, n_return=3)["steps_requested"] == MAX_STEPS
    assert explore(domain="ai", steps=0, n_return=3)["steps_requested"] == 1


def test_explore_disclaims_what_it_is_not():
    out = explore(domain="ai", steps=1, n_return=3)
    joined = " ".join(out["claims_not"]).lower()
    assert "answer" in joined
    assert "closed-loop" in joined
    assert out["honesty"] == "affect_driven_search"


def test_explore_reports_whether_weights_moved():
    assert explore(domain="ai", steps=1, n_return=3)["weights_modulated"] is False
    assert (
        explore(domain="ai", steps=1, n_return=3, allow_weight_deltas=True)["weights_modulated"]
        is True
    )


# --- surfaces --------------------------------------------------------------------------


def test_http_explore_endpoint():
    client = TestClient(app)
    res = client.post("/v1/curiosity/explore", json={"domain": "ai", "steps": 2, "n_return": 3})
    assert res.status_code == 200
    body = res.json()
    assert body["trajectory"]["steps"]
    assert body["weights_modulated"] is False


def test_http_explore_rejects_too_many_steps():
    client = TestClient(app)
    res = client.post("/v1/curiosity/explore", json={"domain": "ai", "steps": 99})
    assert res.status_code == 422


def test_mcp_explore_tool():
    from artificial_emotions.agent_tools import dispatch_tool, mcp_tool_list

    assert "explore_curiosity" in {t["name"] for t in mcp_tool_list()}
    out = dispatch_tool("explore_curiosity", {"domain": "ai", "steps": 2, "n_return": 3})
    assert out["trajectory"]["steps"]


def test_cli_explore_json_and_text(capsys):
    from artificial_emotions.cli import main

    assert (
        main(["explore", "--domain", "ai", "--steps", "2", "--n", "3", "--json", "--no-memory"])
        == 0
    )
    assert json.loads(capsys.readouterr().out)["trajectory"]

    assert main(["explore", "--domain", "ai", "--steps", "2", "--n", "3", "--no-memory"]) == 0
    text = capsys.readouterr().out
    # Emotions that changed something are separated from those merely surfaced,
    # so a reader can tell which of them mattered.
    assert "acted:" in text
    assert "observed:" in text
    assert "Best found" in text


def test_appraisal_signal_serialises():
    signal = AppraisalSignal("curiosity", 0.5, "because", {"x": 1})
    assert signal.to_dict() == {
        "emotion": "curiosity",
        "weight": 0.5,
        "because": "because",
        "evidence": {"x": 1},
    }
