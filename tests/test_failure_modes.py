"""Adversarial checks for documented failure modes (research/FAILURE_MODES.md)."""

from __future__ import annotations

from artificial_emotions.diversity import diversify, is_near_duplicate
from artificial_emotions.models import (
    CuriosityConfig,
    GapEvidence,
    GapStatus,
    RankedQuestion,
    ScoreAxes,
    UnansweredQuestion,
    ValueProfile,
)
from artificial_emotions.pipeline import CuriosityEngine
from artificial_emotions.provoke import provoke
from artificial_emotions.scoring import (
    aggregate_curiosity,
    heuristic_score,
    passes_gates,
    score_uncertainty_band,
)
from artificial_emotions.verify import classify_gap


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


def _q(
    text: str,
    *,
    ops: str = "Run experiment X and measure Y against baseline Z with success criteria.",
    why: str = "High stakes for safe deployment and reliable knowledge.",
    enabling: list[str] | None = None,
) -> UnansweredQuestion:
    return UnansweredQuestion(
        id="t",
        question=text,
        domain="ai",
        operationalization=ops,
        why_it_matters=why,
        enabling_questions=enabling or [],
        tags=["test"],
    )


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
        q = _q(text)
        q.id = str(score)
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
    a = _q("What causes goal-misgeneralization in agents?")
    b = _q("What causes goal misgeneralization in agents?")
    assert is_near_duplicate(a, b, 0.85)


def test_pipeline_flags_heuristic_when_no_llm():
    results = CuriosityEngine(
        CuriosityConfig(domain="ai", use_llm=False, use_literature=False, n_return=3)
    ).run()
    assert results
    assert "heuristic_scoring" in results[0].flags
    assert len(results) >= 3


def test_f3_citations_do_not_inflate_impact():
    """McNamara: citation density must not raise impact — only neglectedness."""
    base = _q("What measurable internal signals most reliably predict goal-misgeneralization?")
    low_cites = heuristic_score(base, GapStatus.UNANSWERED, 2, 5.0, ValueProfile())
    high_cites = heuristic_score(base, GapStatus.UNANSWERED, 2, 500.0, ValueProfile())
    assert high_cites.impact == low_cites.impact
    assert high_cites.neglectedness < low_cites.neglectedness


def test_f6_density_penalizes_crowded_neighborhood():
    q = _q("Which interventions most increase honest uncertainty reporting?")
    sparse = heuristic_score(q, GapStatus.UNANSWERED, 1, 5.0, ValueProfile(), 0)
    crowded = heuristic_score(q, GapStatus.UNANSWERED, 40, 5.0, ValueProfile(), 3)
    assert crowded.neglectedness < sparse.neglectedness


def test_f8_uncertainty_band_widens_when_heuristic():
    low_c = score_uncertainty_band(0.7, 0.25, heuristic=True)
    high_c = score_uncertainty_band(0.7, 0.9, heuristic=False)
    assert (low_c[1] - low_c[0]) > (high_c[1] - high_c[0])


def test_f9_scope_creep_lowers_answerability():
    single = heuristic_score(
        _q("What host factors predict latent-to-active TB progression?"),
        GapStatus.UNANSWERED,
        2,
        10.0,
        ValueProfile(),
    )
    sprawl = heuristic_score(
        _q(
            "What host factors predict TB? Which vaccines work? How do we fund clinics?",
            ops="Map every subsystem and rewrite national policy within one year.",
        ),
        GapStatus.UNANSWERED,
        2,
        10.0,
        ValueProfile(),
    )
    assert sprawl.answerability < single.answerability


def test_f11_value_profile_exposed_in_provoke():
    pack = provoke(domain="ai", n=2, fast=True)
    assert "value_profile" in pack
    assert pack["value_profile"]["name"]
    assert "NOT" in pack["capability"] or "not" in pack["capability"].lower()
    assert "ValueProfile" in pack["inject"]


def test_f11_named_preset_visible_in_provoke():
    pack = provoke(domain="ai", n=2, fast=True, profile_name="alignment_lab")
    assert pack["value_profile"]["name"] == "alignment_lab"
    assert "alignment_lab" in pack["inject"]


def test_f12_likely_answered_requires_recent_strong():
    # Strong + cited but no recent signal → not likely_answered
    assert (
        classify_gap(10, 50.0, 0.5, strong_match_count=3, recent_strong_count=0)
        != GapStatus.LIKELY_ANSWERED
    )
    assert (
        classify_gap(10, 50.0, 0.5, strong_match_count=3, recent_strong_count=2)
        == GapStatus.LIKELY_ANSWERED
    )


def test_f13_paraphrase_gaming_suppressed():
    a = _q("How can we quantify expected value of unanswered scientific questions?")
    b = _q("How can we quantify the expected value of unanswered scientific questions?")
    assert is_near_duplicate(a, b, 0.8)


def test_f13_paraphrase_set_suppressed_in_diversify():
    """Adversarial paraphrase cluster must collapse to one survivor (F13)."""

    def make(text: str, score: float) -> RankedQuestion:
        q = _q(text)
        q.id = str(score) + text[:12]
        return RankedQuestion(
            question=q,
            scores=_axes(),
            curiosity_score=score,
            confidence=0.5,
            gap=GapEvidence(status=GapStatus.UNANSWERED, confidence=0.5),
        )

    # Keep lexical overlap high enough that Jaccard@0.72 treats them as one cluster.
    cluster = [
        make("What measurable signals predict deceptive alignment in agents?", 0.95),
        make("What measurable signals predict deceptive-alignment in agents?", 0.94),
        make("What measurable signals predict deceptive alignment among agents?", 0.93),
        make("Which carbon removal pathway maximizes net climate benefit per dollar?", 0.80),
    ]
    out = diversify(cluster, threshold=0.72, n_return=5)
    texts = [r.question.question for r in out]
    # Only one of the deceptive-alignment paraphrases + the climate outlier.
    assert len(out) == 2
    assert sum("deceptive" in t.lower() for t in texts) == 1
    assert any("carbon" in t.lower() for t in texts)


def test_f7_phrase_gaming_open_gap_damps_overlap():
    """Open-gap abstract language must not inflate 'answered' overlap (F7)."""
    from artificial_emotions.models import LiteratureHit
    from artificial_emotions.verify import _abstract_claim_signal, _effective_overlap

    gaming = LiteratureHit(
        title="Survey",
        abstract_snippet=(
            "Whether agents are deceptively aligned remains an open question; "
            "this is unknown and warrants further research."
        ),
    )
    claiming = LiteratureHit(
        title="Result",
        abstract_snippet=(
            "We show that deceptive alignment is detected by probe X. "
            "Our results demonstrate the method works."
        ),
    )
    g = _abstract_claim_signal(gaming)
    c = _abstract_claim_signal(claiming)
    assert g < 0
    assert c > 0
    assert _effective_overlap(0.35, g) < _effective_overlap(0.35, c)


def test_f7_further_research_needed_not_claim():
    """'Further research is needed' abstracts must damp claim signal (F7)."""
    from artificial_emotions.models import LiteratureHit
    from artificial_emotions.verify import _abstract_claim_signal

    hit = LiteratureHit(
        title="Open survey",
        abstract_snippet=(
            "It remains poorly understood which signals predict harm. "
            "Further research is needed; this is an open question."
        ),
    )
    assert _abstract_claim_signal(hit) < 0


def test_f7_null_replication_phrases_dampen_answered():
    """Null/replication open-gap lexicon should damp effective overlap (failure knowledge)."""
    from artificial_emotions.models import LiteratureHit
    from artificial_emotions.verify import _abstract_claim_signal, _effective_overlap

    nullish = LiteratureHit(
        title="Replication note",
        abstract_snippet=(
            "We failed to replicate the earlier effect; null findings remain. "
            "Despite null results, further research is needed."
        ),
    )
    claiming = LiteratureHit(
        title="Positive result",
        abstract_snippet=(
            "We show the method works. Our results demonstrate significant improvement."
        ),
    )
    assert _abstract_claim_signal(nullish) < 0
    assert _abstract_claim_signal(claiming) > 0
    assert _effective_overlap(0.4, _abstract_claim_signal(nullish)) < _effective_overlap(
        0.4, _abstract_claim_signal(claiming)
    )


def test_f7_related_topic_phrase_not_auto_answered():
    """High hit count + weak overlap stays unanswered — related ≠ answered (F7)."""
    status = classify_gap(
        25,
        80.0,
        0.12,
        strong_match_count=0,
        recent_strong_count=0,
    )
    assert status == GapStatus.UNANSWERED


def test_f13_hyphen_and_article_paraphrase_cluster():
    """F13: article/hyphen paraphrases collapse under diversify."""

    def make(text: str, score: float) -> RankedQuestion:
        q = _q(text)
        q.id = f"{score}-{text[:16]}"
        return RankedQuestion(
            question=q,
            scores=_axes(),
            curiosity_score=score,
            confidence=0.5,
            gap=GapEvidence(status=GapStatus.UNANSWERED, confidence=0.5),
        )

    cluster = [
        make("How can we quantify expected value of unanswered scientific questions?", 0.91),
        make("How can we quantify the expected value of unanswered scientific questions?", 0.90),
        make("How can we quantify expected-value of unanswered scientific questions?", 0.89),
        make("What host factors predict latent-to-active TB progression?", 0.70),
    ]
    out = diversify(cluster, threshold=0.72, n_return=5)
    texts = [r.question.question for r in out]
    assert sum("expected" in t.lower() and "value" in t.lower() for t in texts) == 1
    assert any("tb" in t.lower() or "host factors" in t.lower() for t in texts)


def test_f14_cost_blindness_penalizes_aggregate():
    cheap = aggregate_curiosity(_axes(cost_proxy=0.2), ValueProfile())
    expensive = aggregate_curiosity(_axes(cost_proxy=0.9), ValueProfile())
    assert cheap > expensive


def test_f15_empty_literature_degrades_gracefully():
    results = CuriosityEngine(
        CuriosityConfig(domain="ai", use_llm=False, use_literature=False, n_return=2)
    ).run()
    assert results
    assert results[0].gap.status == GapStatus.UNKNOWN_WITH_CAVEAT
    assert "no_literature" in results[0].flags
    assert results[0].confidence < 0.6


def test_f10_heuristic_flags_dual_use_language():
    axes = heuristic_score(
        _q(
            "How can pathogen surveillance systems be weaponized at scale?",
            why="Dual-use concern for biosecurity.",
        ),
        GapStatus.UNANSWERED,
        1,
        5.0,
        ValueProfile(),
    )
    assert axes.risk >= 0.85
    ok, flags = passes_gates(axes, GapStatus.UNANSWERED, ValueProfile())
    assert not ok
    assert "risk_reject" in flags
