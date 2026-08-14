"""Catalog-only production dispatch: empty ``when`` does not fire.

Emptying ``curiosity.when`` must omit curiosity from ``appraise_run`` even
when ``evaluate_when`` on the live catalog ``when`` would fire.
"""

from __future__ import annotations

import copy

import pytest

from artificial_emotions.appraisal import appraise_run, build_context, evaluate_when
from artificial_emotions.emotions import emotion_catalog
from artificial_emotions.models import (
    GapEvidence,
    GapStatus,
    RankedQuestion,
    ScoreAxes,
    UnansweredQuestion,
)


def _open_gap_item() -> RankedQuestion:
    return RankedQuestion(
        question=UnansweredQuestion(
            id="q-open",
            question="What remains unknown about catalog-only dispatch?",
            domain="ai",
            operationalization="Measure X in experiment Y with success criterion Z.",
            why_it_matters="Open gaps should still look closable.",
        ),
        scores=ScoreAxes(
            impact=0.9,
            neglectedness=0.9,
            tractability=0.8,
            surprise=0.2,
            answerability=0.7,
            risk=0.1,
            cost_proxy=0.4,
        ),
        curiosity_score=0.8,
        confidence=0.5,
        gap=GapEvidence(status=GapStatus.UNANSWERED, confidence=0.5),
    )


@pytest.fixture
def open_gap_items() -> list[RankedQuestion]:
    return [_open_gap_item()]


def test_empty_curiosity_when_does_not_fire_even_if_evaluate_when_would(
    monkeypatch: pytest.MonkeyPatch, open_gap_items: list[RankedQuestion]
) -> None:
    ctx = build_context(open_gap_items)
    by_id = {str(e["id"]): e for e in emotion_catalog()["emotions"]}
    live = evaluate_when(ctx, by_id["curiosity"]["when"])
    assert live is not None
    assert live >= 0.04

    clone = copy.deepcopy(emotion_catalog())
    for entry in clone["emotions"]:
        if entry["id"] == "curiosity":
            entry["when"] = []
            break
    else:
        raise AssertionError("curiosity missing from catalog")

    from artificial_emotions import appraisal as appraisal_mod

    patched = {str(e["id"]): e for e in clone["emotions"]}
    monkeypatch.setattr(appraisal_mod, "_catalog_by_id", lambda: patched)

    fired = {s.emotion for s in appraise_run(open_gap_items)}
    assert "curiosity" not in fired


def test_curiosity_with_when_still_fires(open_gap_items: list[RankedQuestion]) -> None:
    by_id = {str(e["id"]): e for e in emotion_catalog()["emotions"]}
    assert by_id["curiosity"]["when"]
    signals = appraise_run(open_gap_items)
    curiosity = next(s for s in signals if s.emotion == "curiosity")
    assert curiosity.weight >= 0.04
    assert curiosity.because == by_id["curiosity"]["use_for"]
