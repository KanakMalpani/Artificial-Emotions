"""Outcome events with score_axes + labels.result feed tiny profile-scoped hints.

learn_profile_weight_hints never mutates a profile; callers must apply via
apply_weight_hints_to_profile. Not calibrated. Silent without usable events.
"""

from __future__ import annotations

from artificial_emotions.models import ValueProfile, resolve_value_profile
from artificial_emotions.preferences import (
    PreferenceEvent,
    apply_weight_hints_to_profile,
    learn_profile_weight_hints,
)


def _axes(**kwargs: float) -> dict[str, float]:
    base = {
        "impact": 0.5,
        "neglectedness": 0.5,
        "tractability": 0.5,
        "surprise": 0.5,
    }
    base.update(kwargs)
    return base


def _outcome(
    result: str,
    axes: dict[str, float],
    *,
    profile_name: str = "humanity_default",
    question_id: str = "q1",
) -> PreferenceEvent:
    return PreferenceEvent(
        event_type="outcome",
        profile_name=profile_name,
        question_id=question_id,
        score_axes=axes,
        labels={"result": result},
    )


def test_outcome_hints_silent_without_events():
    hints = learn_profile_weight_hints([], profile_name="humanity_default")
    assert hints["ok"] is False
    assert hints["deltas"] == {}
    assert hints["n_prefer"] == 0
    assert hints["n_reject"] == 0
    assert hints["n_outcome"] == 0
    assert "not calibrated" in hints["honesty"].lower()


def test_outcome_hints_silent_without_score_axes():
    hints = learn_profile_weight_hints(
        [
            PreferenceEvent(
                event_type="outcome",
                profile_name="humanity_default",
                question_id="q1",
                labels={"result": "partial_progress"},
            ),
            PreferenceEvent(
                event_type="outcome",
                profile_name="humanity_default",
                question_id="q2",
                labels={"result": "contradicted"},
            ),
        ],
        profile_name="humanity_default",
    )
    assert hints["ok"] is False
    assert hints["deltas"] == {}
    assert hints["n_outcome"] == 0


def test_outcome_hints_silent_without_result_label():
    axes = _axes(impact=0.9, tractability=0.2)
    hints = learn_profile_weight_hints(
        [
            PreferenceEvent(
                event_type="outcome",
                profile_name="humanity_default",
                question_id="q1",
                score_axes=axes,
            ),
            PreferenceEvent(
                event_type="outcome",
                profile_name="humanity_default",
                question_id="q2",
                score_axes=_axes(impact=0.2, tractability=0.9),
                labels={},
            ),
        ],
        profile_name="humanity_default",
    )
    assert hints["ok"] is False
    assert hints["deltas"] == {}
    assert hints["n_outcome"] == 0


def test_outcome_hints_silent_unknown_result():
    hints = learn_profile_weight_hints(
        [
            _outcome("maybe_later", _axes(impact=0.9, neglectedness=0.8)),
            _outcome("unspecified", _axes(impact=0.2, neglectedness=0.2)),
        ],
        profile_name="humanity_default",
    )
    assert hints["ok"] is False
    assert hints["deltas"] == {}
    assert hints["n_outcome"] == 0


def test_outcome_progress_vs_contradicted_nudges_matching_axes():
    hints = learn_profile_weight_hints(
        [
            _outcome(
                "partial_progress",
                _axes(impact=0.9, neglectedness=0.85, tractability=0.3, surprise=0.7),
                question_id="progress",
            ),
            _outcome(
                "contradicted",
                _axes(impact=0.3, neglectedness=0.25, tractability=0.9, surprise=0.2),
                question_id="miss",
            ),
        ],
        profile_name="humanity_default",
    )
    assert hints["ok"] is True
    assert hints["n_outcome"] == 2
    assert hints["n_prefer"] == 1
    assert hints["n_reject"] == 1
    assert hints["deltas"]["weight_impact"] > 0
    assert hints["deltas"]["weight_tractability"] < 0
    assert abs(hints["deltas"]["weight_impact"]) <= 0.08
    assert abs(hints["deltas"]["weight_tractability"]) <= 0.08
    assert "not calibrated" in hints["honesty"].lower()


def test_answered_is_progress_like_abandoned_and_elsewhere_are_reject_like():
    hints = learn_profile_weight_hints(
        [
            _outcome(
                "answered",
                _axes(impact=0.88, neglectedness=0.8, tractability=0.25, surprise=0.7),
                question_id="done",
            ),
            _outcome(
                "abandoned",
                _axes(impact=0.25, neglectedness=0.2, tractability=0.92, surprise=0.2),
                question_id="drop",
            ),
            _outcome(
                "answered_elsewhere",
                _axes(impact=0.3, neglectedness=0.22, tractability=0.88, surprise=0.25),
                question_id="false_unknown",
            ),
        ],
        profile_name="humanity_default",
    )
    assert hints["ok"] is True
    assert hints["n_outcome"] == 3
    assert hints["deltas"]["weight_impact"] > 0
    assert hints["deltas"]["weight_tractability"] < 0


def test_null_result_is_reject_like_against_progress():
    hints = learn_profile_weight_hints(
        [
            _outcome(
                "partial_progress",
                _axes(impact=0.9, neglectedness=0.8, tractability=0.3, surprise=0.65),
                question_id="progress",
            ),
            _outcome(
                "null",
                _axes(impact=0.25, neglectedness=0.3, tractability=0.9, surprise=0.2),
                question_id="null_result",
            ),
        ],
        profile_name="humanity_default",
    )
    assert hints["ok"] is True
    assert hints["n_outcome"] == 2
    assert hints["n_reject"] == 1
    assert hints["deltas"]["weight_impact"] > 0
    assert hints["deltas"]["weight_tractability"] < 0


def test_already_answered_outcome_is_reject_like():
    hints = learn_profile_weight_hints(
        [
            _outcome(
                "partial_progress",
                _axes(impact=0.85, neglectedness=0.8, tractability=0.3, surprise=0.7),
                question_id="live",
            ),
            _outcome(
                "already_answered",
                _axes(impact=0.3, neglectedness=0.25, tractability=0.85, surprise=0.25),
                question_id="closed",
            ),
        ],
        profile_name="humanity_default",
    )
    assert hints["ok"] is True
    assert hints["n_outcome"] == 2
    assert hints["deltas"]["weight_tractability"] < 0


def test_outcome_hints_floors_prevent_zero_weights():
    base = ValueProfile(
        name="floor_probe",
        weight_impact=0.16,
        weight_neglectedness=1.0,
        weight_tractability=1.0,
        weight_surprise=1.0,
    )
    hints = learn_profile_weight_hints(
        [
            _outcome(
                "partial_progress",
                _axes(impact=0.1, neglectedness=0.8, tractability=0.8, surprise=0.8),
                question_id="low_impact_progress",
            ),
            _outcome(
                "contradicted",
                _axes(impact=0.95, neglectedness=0.2, tractability=0.2, surprise=0.2),
                question_id="high_impact_miss",
            ),
        ],
        profile_name="humanity_default",
        base_profile=base,
    )
    assert hints["ok"] is True
    suggested = hints["suggested_profile"]
    for key in (
        "weight_impact",
        "weight_neglectedness",
        "weight_tractability",
        "weight_surprise",
    ):
        assert suggested[key] >= 0.15
        assert suggested[key] > 0.0
    assert "weight_impact" in hints["clamped_weights"]


def test_learn_does_not_apply_until_caller_asks():
    base = resolve_value_profile(profile_name="humanity_default")
    impact_before = base.weight_impact
    tract_before = base.weight_tractability
    hints = learn_profile_weight_hints(
        [
            _outcome(
                "partial_progress",
                _axes(impact=0.9, neglectedness=0.85, tractability=0.3, surprise=0.7),
            ),
            _outcome(
                "contradicted",
                _axes(impact=0.3, neglectedness=0.25, tractability=0.9, surprise=0.2),
            ),
        ],
        profile_name="humanity_default",
        base_profile=base,
    )
    assert hints["ok"] is True
    assert base.weight_impact == impact_before
    assert base.weight_tractability == tract_before
    applied = apply_weight_hints_to_profile(base, hints)
    assert applied is not base
    assert applied.weight_impact > impact_before
    assert applied.weight_tractability < tract_before
    noop = apply_weight_hints_to_profile(base, {"ok": False, "deltas": hints["deltas"]})
    assert noop is base
    assert noop.weight_impact == impact_before


def test_outcome_hints_are_profile_scoped():
    hints = learn_profile_weight_hints(
        [
            _outcome(
                "partial_progress",
                _axes(impact=0.9, neglectedness=0.85, tractability=0.3, surprise=0.7),
                profile_name="alignment_lab",
            ),
            _outcome(
                "contradicted",
                _axes(impact=0.3, neglectedness=0.25, tractability=0.9, surprise=0.2),
                profile_name="alignment_lab",
            ),
        ],
        profile_name="humanity_default",
    )
    assert hints["ok"] is False
    assert hints["n_outcome"] == 0
    assert hints["deltas"] == {}


def test_one_usable_outcome_is_not_enough():
    hints = learn_profile_weight_hints(
        [
            _outcome(
                "partial_progress",
                _axes(impact=0.9, neglectedness=0.8, tractability=0.3, surprise=0.7),
            ),
        ],
        profile_name="humanity_default",
    )
    assert hints["ok"] is False
    assert hints["n_outcome"] == 1
    assert hints["deltas"] == {}


def test_outcomes_mix_with_prefer_reject():
    hints = learn_profile_weight_hints(
        [
            PreferenceEvent(
                event_type="prefer",
                profile_name="humanity_default",
                question_id="p1",
                score_axes=_axes(impact=0.9, neglectedness=0.8, tractability=0.3, surprise=0.7),
            ),
            _outcome(
                "contradicted",
                _axes(impact=0.3, neglectedness=0.25, tractability=0.9, surprise=0.2),
                question_id="o1",
            ),
        ],
        profile_name="humanity_default",
    )
    assert hints["ok"] is True
    assert hints["n_outcome"] == 1
    assert hints["n_prefer"] == 1
    assert hints["n_reject"] == 1
    assert hints["deltas"]["weight_impact"] > 0
    assert hints["deltas"]["weight_tractability"] < 0
