"""Unit tests for scoring, gates, diversity, and offline pipeline."""

from __future__ import annotations

from artificial_curiosity.diversity import diversify, jaccard
from artificial_curiosity.models import (
    CuriosityConfig,
    GapStatus,
    LiteratureHit,
    RankedQuestion,
    ScoreAxes,
    UnansweredQuestion,
    ValueProfile,
)
from artificial_curiosity.pipeline import CuriosityEngine
from artificial_curiosity.scoring import (
    aggregate_curiosity,
    heuristic_score,
    passes_gates,
    score_uncertainty_band,
)
from artificial_curiosity.verify import (
    _abstract_claim_signal,
    _effective_overlap,
    classify_gap,
)


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


def test_score_uncertainty_band_widens_when_low_confidence():
    low_c = score_uncertainty_band(0.8, 0.2, heuristic=True)
    high_c = score_uncertainty_band(0.8, 0.9, heuristic=False)
    assert low_c[0] < high_c[0]
    assert low_c[1] > high_c[1]
    assert low_c[0] <= 0.8 <= low_c[1]


def test_abstract_claim_vs_open_gap_reading():
    claim = LiteratureHit(
        title="A solved case",
        abstract_snippet="We show that the mechanism is X. Our results demonstrate Y.",
    )
    open_q = LiteratureHit(
        title="An open problem",
        abstract_snippet="This remains unknown and is an open question for further research.",
    )
    assert _abstract_claim_signal(claim) > 0
    assert _abstract_claim_signal(open_q) < 0
    # Open-gap language should dampen effective overlap vs claim language.
    dampened = _effective_overlap(0.3, _abstract_claim_signal(open_q))
    boosted = _effective_overlap(0.3, _abstract_claim_signal(claim))
    assert dampened < boosted


def test_offline_results_include_score_band():
    results = CuriosityEngine(
        CuriosityConfig(domain="ai", use_llm=False, use_literature=False, n_return=2)
    ).run()
    assert results[0].score_low is not None
    assert results[0].score_high is not None
    assert results[0].score_low <= results[0].curiosity_score <= results[0].score_high


def test_all_primary_domains_have_seeds():
    from artificial_curiosity.models import Domain
    from artificial_curiosity.seeds import SEED_QUESTIONS

    primary = [
        Domain.AI,
        Domain.BIOLOGY,
        Domain.PHYSICS,
        Domain.CLIMATE,
        Domain.MEDICINE,
        Domain.MATERIALS,
        Domain.SOCIAL,
        Domain.ENERGY,
    ]
    for d in primary:
        qs = SEED_QUESTIONS.get(d.value, [])
        assert len(qs) >= 2, f"{d.value} needs curated seeds"
        for q in qs:
            assert q.question.strip()
            assert q.operationalization.strip()


def test_spark_works_across_domains():
    from artificial_curiosity.provoke import provoke

    for domain in ("biology", "materials", "social", "energy"):
        pack = provoke(domain=domain, n=2, fast=True)
        assert pack["count"] >= 1
        assert pack["unknowns"][0]["question"]


def test_value_profile_presets_exist():
    from artificial_curiosity.models import get_profile, list_profile_names

    names = list_profile_names()
    assert "humanity_default" in names
    assert "funder_10y" in names
    assert "alignment_lab" in names
    assert "climate_adaptation" in names
    p = get_profile("alignment_lab")
    assert p.name == "alignment_lab"
    assert p.max_risk <= 0.85


def test_embedding_backend_falls_back_without_extra():
    """Optional embedding path must not break offline Jaccard default (W1)."""
    from artificial_curiosity.diversity import diversify, embedding_available, similarity

    a = "What signals predict goal misgeneralization before deployment harm?"
    b = "What signals predict goal-misgeneralization before deployment-scale harm?"
    # Jaccard always works.
    assert similarity(a, b, backend="jaccard") > 0.5
    # Requesting embedding without extras still returns a usable similarity
    # (Jaccard fallback inside similarity / diversify).
    sim = similarity(a, b, backend="embedding")
    assert 0.0 <= sim <= 1.0
    if not embedding_available():
        assert sim == similarity(a, b, backend="jaccard")

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

    out = diversify(
        [rq(a, 0.9), rq(b, 0.85)],
        threshold=0.55,
        n_return=5,
        backend="embedding",
    )
    assert len(out) == 1


def test_judge_model_config_field_accepted():
    cfg = CuriosityConfig(
        domain="ai",
        use_llm=False,
        use_literature=False,
        llm_model="gen-model",
        judge_model="judge-model",
        n_return=2,
    )
    assert cfg.judge_model == "judge-model"
    # Offline path still runs with distinct judge_model set.
    results = CuriosityEngine(cfg).run()
    assert results


def test_literature_workers_parallel_verify():
    """Parallel verify uses ThreadPoolExecutor but preserves candidate order."""
    import threading
    import time

    from artificial_curiosity.models import LiteratureHit

    lock = threading.Lock()
    in_flight = 0
    max_in_flight = 0
    call_order: list[str] = []

    class SlowFake:
        def search_works(self, query: str, per_page: int = 8):
            nonlocal in_flight, max_in_flight
            with lock:
                in_flight += 1
                max_in_flight = max(max_in_flight, in_flight)
                call_order.append(query[:40])
            time.sleep(0.05)
            with lock:
                in_flight -= 1
            return [
                LiteratureHit(
                    title="Unrelated neighborhood paper about widgets",
                    year=2024,
                    cited_by_count=2,
                    abstract_snippet="Remains unknown how widgets generalize.",
                )
            ]

    engine = CuriosityEngine(
        CuriosityConfig(
            domain="ai",
            use_llm=False,
            use_literature=True,
            literature_workers=4,
            n_candidates=6,
            n_return=3,
        )
    )
    engine._client = SlowFake()
    results = engine.run()
    assert results
    assert max_in_flight >= 2  # actually overlapped
    assert any("lit_parallel" in (r.flags or []) for r in results)
    # Order of network calls need not match; ranked results still valid.
    assert all(r.gap is not None for r in results)


def test_literature_workers_serial_when_one():
    engine = CuriosityEngine(
        CuriosityConfig(
            domain="ai",
            use_llm=False,
            use_literature=False,
            literature_workers=1,
            n_return=2,
        )
    )
    results = engine.run()
    assert results
    assert all("lit_parallel" not in (r.flags or []) for r in results)
