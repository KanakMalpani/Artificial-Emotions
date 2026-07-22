"""Unit tests for scoring, gates, diversity, and offline pipeline."""

from __future__ import annotations

from artificial_curiosity.diversity import diversify, jaccard
from artificial_curiosity.models import (
    CuriosityConfig,
    GapStatus,
    RankedQuestion,
    ScoreAxes,
    UnansweredQuestion,
    ValueProfile,
)
from artificial_curiosity.pipeline import CuriosityEngine
from artificial_curiosity.scoring import aggregate_curiosity, heuristic_score, passes_gates
from artificial_curiosity.verify import classify_gap


def test_aggregate_prefers_balanced_high_axes():
    profile = ValueProfile()
    strong = ScoreAxes(
        impact=0.9,
        neglectedness=0.9,
        tractability=0.8,
        surprise=0.7,
        answerability=0.9,
        risk=0.1,
        cost_proxy=0.4,
    )
    weak_link = ScoreAxes(
        impact=0.95,
        neglectedness=0.95,
        tractability=0.05,
        surprise=0.9,
        answerability=0.9,
        risk=0.1,
        cost_proxy=0.4,
    )
    assert aggregate_curiosity(strong, profile) > aggregate_curiosity(weak_link, profile)


def test_risk_gate_rejects():
    axes = ScoreAxes(
        impact=0.9,
        neglectedness=0.9,
        tractability=0.9,
        surprise=0.9,
        answerability=0.9,
        risk=0.95,
        cost_proxy=0.4,
    )
    ok, flags = passes_gates(axes, GapStatus.UNANSWERED, ValueProfile())
    assert not ok
    assert "risk_reject" in flags


def test_likely_answered_gate():
    axes = ScoreAxes(
        impact=0.8,
        neglectedness=0.8,
        tractability=0.8,
        surprise=0.8,
        answerability=0.8,
        risk=0.1,
        cost_proxy=0.4,
    )
    ok, flags = passes_gates(axes, GapStatus.LIKELY_ANSWERED, ValueProfile())
    assert not ok
    assert "likely_answered" in flags


def test_classify_gap_sparse_is_unanswered():
    assert classify_gap(2, 5.0, 0.2, strong_match_count=0) == GapStatus.UNANSWERED


def test_classify_gap_related_but_weak_overlap_stays_unanswered():
    # Many hits with weak overlap must NOT become partially_answered.
    assert classify_gap(10, 40.0, 0.15, strong_match_count=0) == GapStatus.UNANSWERED


def test_classify_gap_strong_matches_partial():
    assert classify_gap(8, 25.0, 0.4, strong_match_count=2) == GapStatus.PARTIALLY_ANSWERED


def test_diversify_removes_near_duplicates():
    def rq(text: str, score: float) -> RankedQuestion:
        q = UnansweredQuestion(
            id=text[:8],
            question=text,
            domain="ai",
            operationalization="Measure X in experiment Y with success criterion Z.",
            why_it_matters="It matters a lot for safety.",
        )
        return RankedQuestion(
            question=q,
            scores=ScoreAxes(
                impact=0.7,
                neglectedness=0.7,
                tractability=0.7,
                surprise=0.7,
                answerability=0.8,
                risk=0.1,
                cost_proxy=0.4,
            ),
            curiosity_score=score,
            confidence=0.5,
            gap=__import__("artificial_curiosity.models", fromlist=["GapEvidence"]).GapEvidence(
                status=GapStatus.UNANSWERED,
                confidence=0.5,
            ),
        )

    a = rq("What signals predict goal misgeneralization before deployment harm?", 0.9)
    b = rq("What signals predict goal-misgeneralization before deployment-scale harm?", 0.85)
    c = rq("Which carbon removal pathways maximize net climate benefit?", 0.8)
    assert jaccard(a.question.question, b.question.question) > 0.5
    out = diversify([a, b, c], threshold=0.55, n_return=5)
    assert len(out) == 2
    assert out[0].rank == 1


def test_offline_pipeline_returns_ranked_questions():
    engine = CuriosityEngine(
        CuriosityConfig(
            domain="ai",
            n_return=5,
            n_candidates=8,
            use_llm=False,
            use_literature=False,
        )
    )
    results = engine.run()
    assert len(results) >= 1
    assert results[0].rank == 1
    assert results[0].curiosity_score >= results[-1].curiosity_score
    assert results[0].investigation_brief


def test_heuristic_score_bounds():
    q = UnansweredQuestion(
        id="t1",
        question="What causes antibiotic resistance evolution under combination therapy?",
        domain="medicine",
        operationalization="Track resistance allele frequencies in evolution assays.",
        why_it_matters="Antibiotic resistance threatens modern medicine and mortality.",
        tags=["amr"],
    )
    axes = heuristic_score(q, GapStatus.UNANSWERED, 2, 10.0, ValueProfile())
    for v in (
        axes.impact,
        axes.neglectedness,
        axes.tractability,
        axes.surprise,
        axes.answerability,
        axes.risk,
        axes.cost_proxy,
    ):
        assert 0.0 <= v <= 1.0
