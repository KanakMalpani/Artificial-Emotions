"""RankedQuestion flag/band helpers — shared by stances and imagination lenses."""

from __future__ import annotations

import json

import pytest

from artificial_emotions.models import (
    GapEvidence,
    GapStatus,
    RankedQuestion,
    ScoreAxes,
    UnansweredQuestion,
)


def _item(**kwargs: object) -> RankedQuestion:
    defaults: dict[str, object] = {
        "question": UnansweredQuestion(
            id="q-helper",
            question="What remains unknown about ranked helpers?",
            domain="ai",
            operationalization="Measure X in experiment Y with success criterion Z.",
            why_it_matters="Helpers must not change serialized ranks.",
        ),
        "scores": ScoreAxes(
            impact=0.5,
            neglectedness=0.5,
            tractability=0.5,
            surprise=0.5,
            answerability=0.5,
            risk=0.1,
            cost_proxy=0.4,
        ),
        "curiosity_score": 0.5,
        "confidence": 0.5,
        "gap": GapEvidence(status=GapStatus.UNANSWERED, confidence=0.5),
    }
    defaults.update(kwargs)
    return RankedQuestion.model_validate(defaults)


def test_flag_set_and_band_width_match_legacy_helpers():
    item = _item(flags=["heuristic_scoring", "no_literature"], score_low=0.2, score_high=0.8)
    assert item.flag_set() == {"heuristic_scoring", "no_literature"}
    assert item.score_band_width() == pytest.approx(0.6)


def test_missing_flags_and_bounds_are_empty_or_zero():
    item = _item()
    assert item.flag_set() == set()
    assert item.score_band_width() == 0.0
    half = _item(score_low=0.1, score_high=None)
    assert half.score_band_width() == 0.0


def test_helpers_are_not_serialized():
    item = _item(flags=["heuristic_scoring"], score_low=0.1, score_high=0.4)
    for dumped in (
        item.model_dump(),
        item.model_dump(mode="json"),
        json.loads(item.model_dump_json()),
    ):
        assert "flag_set" not in dumped
        assert "score_band_width" not in dumped
        assert dumped["flags"] == ["heuristic_scoring"]
        assert dumped["score_low"] == 0.1
