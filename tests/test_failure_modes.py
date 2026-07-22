"""Adversarial checks for documented failure modes."""

from __future__ import annotations

from artificial_curiosity.diversity import diversify, is_near_duplicate
from artificial_curiosity.models import (
    CuriosityConfig,
    GapStatus,
    RankedQuestion,
    ScoreAxes,
    UnansweredQuestion,
    ValueProfile,
)
from artificial_curiosity.pipeline import CuriosityEngine
from artificial_curiosity.scoring import passes_gates
from artificial_curiosity.models import GapEvidence


def _axes(**kwargs: float) -> ScoreAxes:
    base = dict(
        impact=0.8,
        neglectedness=0.8,
        tractability=0.8,
        surprise=0.8,
        answerability=0.8,
        risk=0.1,
        cost_proxy=0.4,
    )
    base.update(kwargs)
    return ScoreAxes(**base)


def test_f2_ill_posed_low_answerability_rejected():
    ok, flags = passes_gates(
        _axes(answerability=0.2),
        GapStatus.UNANSWERED,
        ValueProfile(),
    )
    assert not ok
    assert "low_answerability" in flags


def test_f10_dual_use_risk_rejected():
    ok, flags = passes_gates(
        _axes(risk=0.95),
        GapStatus.UNANSWERED,
        ValueProfile(),
    )
    assert not ok
    assert "risk_reject" in flags


def test_f1_likely_answered_rejected():
    ok, flags = passes_gates(
        _axes(),
        GapStatus.LIKELY_ANSWERED,
        ValueProfile(),
    )
    assert not ok
    assert "likely_answered" in flags


def test_f4_mode_collapse_suppressed():
    def make(text: str, score: float) -> RankedQuestion:
        q = UnansweredQuestion(
            id=str(score),
            question=text,
            domain="ai",
            operationalization="Run experiment X and measure Y against baseline Z.",
            why_it_matters="High stakes for safe deployment.",
        )
        return RankedQuestion(
            question=q,
            scores=_axes(),
            curiosity_score=score,
            confidence=0.5,
            gap=GapEvidence(status=GapStatus.UNANSWERED, confidence=0.5),
        )

    a = make("How do we detect deceptive alignment in multi-step agents?", 0.9)
    b = make("How do we detect deceptive-alignment in multi step agents?", 0.88)
    assert is_near_duplicate(a.question, b.question, 0.7)
    out = diversify([a, b], threshold=0.7, n_return=5)
    assert len(out) == 1


def test_normalize_treats_hyphen_variants_as_duplicates():
    a = UnansweredQuestion(
        id="a",
        question="What causes goal-misgeneralization in agents?",
        domain="ai",
        operationalization="Measure prediction error across held-out environments with fixed success criteria.",
        why_it_matters="Safety-critical failure mode.",
    )
    b = UnansweredQuestion(
        id="b",
        question="What causes goal misgeneralization in agents?",
        domain="ai",
        operationalization="Measure prediction error across held-out environments with fixed success criteria.",
        why_it_matters="Safety-critical failure mode.",
    )
    assert is_near_duplicate(a, b, 0.85)


def test_pipeline_flags_heuristic_when_no_llm():
    results = CuriosityEngine(
        CuriosityConfig(domain="ai", use_llm=False, use_literature=False, n_return=3)
    ).run()
    assert results
    assert "heuristic_scoring" in results[0].flags
    assert len(results) >= 3
