"""Literature adapters, gap reading, and eval harnesses (W10–W12, W15)."""

from __future__ import annotations

from pathlib import Path

from artificial_curiosity.evals import (
    already_answered_fail_rate,
    load_fixtures,
    run_spotcheck,
)
from artificial_curiosity.judge import (
    ScoreAxes,
    disagreement_entropy,
    evidence_titles_grounded,
    mean_axes,
    validate_gap_reader_grounding,
)
from artificial_curiosity.literature import (
    CachedLiteratureClient,
    MergedLiteratureClient,
    build_literature_client,
)
from artificial_curiosity.models import (
    CuriosityConfig,
    GapStatus,
    LiteratureHit,
    UnansweredQuestion,
)
from artificial_curiosity.pipeline import CuriosityEngine
from artificial_curiosity.scoring import heuristic_score, score_uncertainty_band
from artificial_curiosity.verify import verify_gap


def test_w10_spotcheck_harness_offline():
    cases = load_fixtures()
    assert len(cases) >= 9  # v1 + adversarial v2
    report = run_spotcheck(cases)
    assert report.n_cases == len(cases)
    assert report.match_rate is not None
    assert "offline" in report.methodology.lower() or "fixture" in report.methodology.lower()
    assert report.by_gold_status
    payload = report.to_dict()
    assert "by_gold_status" in payload
    # Empty-lit case should match unknown_with_caveat.
    by_id = {r.case_id: r for r in report.results}
    assert by_id["empty-literature"].predicted_status == "unknown_with_caveat"
    assert by_id["empty-hits-unknown"].predicted_status == "unknown_with_caveat"
    assert by_id["adjacent-not-answered"].predicted_status == "unanswered"
    assert by_id["phrase-gaming-open-gap"].predicted_status == "unanswered"
    assert by_id["weak-ops-overlap"].predicted_status == "unanswered"
    # Stale years must not auto-promote to likely_answered (F12).
    assert by_id["stale-strong-overlap"].predicted_status != "likely_answered"
    # Strengthened answered fixture should classify likely_answered (F1 monitor).
    assert by_id["answered-strong-overlap"].predicted_status == "likely_answered"
    assert by_id["answered-strong-overlap"].match
    fail_rate = already_answered_fail_rate(report)
    assert fail_rate is not None
    assert fail_rate == 0.0
    # Never treat match_rate as a marketed accuracy claim — just that harness ran.
    assert 0.0 <= float(report.match_rate) <= 1.0


def test_w11_literature_factory_offline_and_merge():
    # Offline path: engine with use_literature=False never needs a client.
    results = CuriosityEngine(
        CuriosityConfig(domain="ai", use_literature=False, use_llm=False, n_return=2)
    ).run()
    assert results
    assert (
        results[0].gap.literature_backend in (None, "none") or "no_literature" in results[0].flags
    )

    client = build_literature_client("openalex")
    assert client is not None

    class FakeA:
        def search_works(self, query: str, per_page: int = 8):
            return [
                LiteratureHit(title="Alpha Paper", year=2024, cited_by_count=10, source="a"),
            ]

    class FakeB:
        def search_works(self, query: str, per_page: int = 8):
            return [
                LiteratureHit(
                    title="Alpha Paper",
                    year=2024,
                    cited_by_count=12,
                    abstract_snippet="We show results.",
                    source="b",
                ),
                LiteratureHit(title="Beta Paper", year=2023, source="b"),
            ]

    merged = MergedLiteratureClient(FakeA(), FakeB())
    hits = merged.search_works("alpha")
    titles = [h.title for h in hits]
    assert "Alpha Paper" in titles
    assert "Beta Paper" in titles
    # Prefer abstract-bearing duplicate.
    alpha = next(h for h in hits if h.title == "Alpha Paper")
    assert alpha.abstract_snippet


def test_w11_literature_cache(tmp_path: Path):
    calls = {"n": 0}

    class Counting:
        def search_works(self, query: str, per_page: int = 8):
            calls["n"] += 1
            return [LiteratureHit(title="Cached", year=2024, source="t")]

    cached = CachedLiteratureClient(Counting(), backend_name="test", cache_dir=tmp_path, ttl_s=3600)
    assert cached.search_works("q")[0].title == "Cached"
    assert cached.search_works("q")[0].title == "Cached"
    assert calls["n"] == 1


def test_w11_verify_accepts_fixture_client():
    q = UnansweredQuestion(
        id="t1",
        question="Does CRISPR-Cas9 enable targeted gene editing in mammalian cells?",
        domain="biology",
        operationalization="Site-specific DNA edits with sequencing confirmation.",
        why_it_matters="Gene editing.",
    )

    class Fake:
        def search_works(self, query: str, per_page: int = 8):
            return [
                LiteratureHit(
                    title="CRISPR-Cas9 targeted gene editing in mammalian cells",
                    year=2024,
                    cited_by_count=100,
                    abstract_snippet="We demonstrate site-specific DNA edits in mammalian cells.",
                    source="fixture",
                )
            ]

    gap = verify_gap(q, client=Fake(), use_literature=True, literature_backend="fixture")
    assert gap.literature_backend == "fixture"
    assert gap.related_works


def test_w12_gap_reader_rejects_ungrounded_titles():
    related = ["CRISPR-Cas9 targeted gene editing in mammalian cells", "Scaling laws"]
    ok, unmatched = evidence_titles_grounded(
        ["A completely invented Nature paper about unicorns"],
        related,
    )
    assert not ok
    assert unmatched

    ok2, _ = evidence_titles_grounded(
        ["CRISPR-Cas9 targeted gene editing in mammalian cells"],
        related,
    )
    assert ok2

    grounded, reason = validate_gap_reader_grounding(
        {
            "status": "likely_answered",
            "strongest_evidence": "Invented Paper Title XYZ",
            "evidence_titles": ["Invented Paper Title XYZ"],
        },
        related,
    )
    assert not grounded
    assert "ungrounded" in reason

    grounded2, _ = validate_gap_reader_grounding(
        {
            "status": "unknown_with_caveat",
            "strongest_evidence": "",
            "evidence_titles": [],
        },
        related,
    )
    assert grounded2


def test_w15_multi_judge_disagreement_widens_bands():
    a = ScoreAxes(
        impact=0.9,
        neglectedness=0.5,
        tractability=0.5,
        surprise=0.5,
        answerability=0.9,
        risk=0.1,
        cost_proxy=0.5,
    )
    b = ScoreAxes(
        impact=0.2,
        neglectedness=0.5,
        tractability=0.5,
        surprise=0.5,
        answerability=0.3,
        risk=0.7,
        cost_proxy=0.5,
    )
    ent = disagreement_entropy([a, b])
    assert ent >= 0.35
    mean = mean_axes([a, b])
    assert abs(mean.impact - 0.55) < 1e-6

    low1, high1 = score_uncertainty_band(0.8, 0.7, disagreement_entropy=0.0)
    low2, high2 = score_uncertainty_band(0.8, 0.7, disagreement_entropy=0.8)
    assert (high2 - low2) > (high1 - low1)


def test_lit_rationale_keys_no_weight_change():
    from artificial_curiosity.evals import _FixtureLitClient
    from artificial_curiosity.models import CuriosityConfig, LiteratureHit, UnansweredQuestion
    from artificial_curiosity.scoring import lit_rationale_keys
    from artificial_curiosity.verify import verify_gap

    hits = [
        LiteratureHit(
            title="CRISPR-Cas9 targeted gene editing in mammalian cells",
            year=2024,
            cited_by_count=100,
            abstract_snippet=(
                "We demonstrate site-specific DNA edits in cultured mammalian cells "
                "with sequencing confirmation. CRISPR-Cas9 gene editing works."
            ),
            has_funder=True,
        ),
        LiteratureHit(
            title="Efficient genome editing using CRISPR-Cas9 in mammals",
            year=2023,
            cited_by_count=50,
            abstract_snippet=(
                "Results show targeted gene editing in mammalian cells with "
                "sequencing confirmation of site-specific DNA edits."
            ),
            has_funder=False,
        ),
    ]
    keys = lit_rationale_keys(hits)
    assert keys["openalex_hit_n"] == "2"
    assert "funder_field_missing_rate" in keys
    assert keys["funder_metadata_note"] == "from_has_funder_field"

    q = UnansweredQuestion(
        id="t",
        question="Does CRISPR-Cas9 enable targeted gene editing in mammalian cells?",
        domain="biology",
        operationalization=(
            "Demonstration of site-specific DNA edits in cultured mammalian cells "
            "with sequencing confirmation."
        ),
        why_it_matters="fixture",
    )
    gap = verify_gap(
        q,
        client=_FixtureLitClient(hits),
        use_literature=True,
        literature_backend="fixture",
    )
    axes = heuristic_score(q, gap.status, len(hits), 75.0, CuriosityConfig().value_profile)
    before = (
        axes.impact,
        axes.neglectedness,
        axes.tractability,
        axes.surprise,
        axes.answerability,
        axes.risk,
        axes.cost_proxy,
    )
    axes.rationale = {**(axes.rationale or {}), **keys}
    after = (
        axes.impact,
        axes.neglectedness,
        axes.tractability,
        axes.surprise,
        axes.answerability,
        axes.risk,
        axes.cost_proxy,
    )
    assert before == after
    assert axes.rationale["funder_field_missing_rate"] == keys["funder_field_missing_rate"]


def test_gap_status_handlabel_metric():
    from artificial_curiosity.evals import load_gap_status_fixtures, run_gap_status_eval

    cases = load_gap_status_fixtures()
    assert len(cases) >= 5
    assert any(c.related_but_unanswered for c in cases)
    report = run_gap_status_eval(cases)
    assert report.n_cases == len(cases)
    assert report.status_accuracy is not None
    assert report.related_but_unanswered_recall is not None
    assert report.false_answered_rate is not None
    # Fixtures are calibrated to current verify thresholds — not a marketing claim.
    assert report.false_answered_rate == 0.0
    assert report.related_but_unanswered_recall == 1.0
    assert any("invalid_form" in (c.gold_tags or []) for c in cases)


def test_cooccur_correlation_offline():
    from pathlib import Path

    from artificial_curiosity.cooccur_study import (
        cooccur_rationale_key,
        gap_score,
        run_cooccur_correlation,
    )

    assert gap_score(1.0, 0) == 1.0
    assert gap_score(1.0, 1) == 0.5
    keys = cooccur_rationale_key(0.9, 0)
    assert keys["cooccur_gap_note"] == "display_only_no_weight_change"
    path = (
        Path(__file__).resolve().parents[1]
        / "evals"
        / "fixtures"
        / "cooccur_neglectedness_smoke_v1.json"
    )
    out = run_cooccur_correlation(path)
    assert out["n"] >= 5
    assert out["spearman_rho"] is not None
    assert out["spearman_rho"] > 0.5  # synthetic fixture is aligned by construction


def test_feasibility_note_display_only():
    from artificial_curiosity.brief import feasibility_note, write_brief
    from artificial_curiosity.models import (
        GapEvidence,
        RankedQuestion,
        ScoreAxes,
        UnansweredQuestion,
    )

    q = UnansweredQuestion(
        id="f1",
        question="Which biomarkers predict healthspan under interventions?",
        domain="biology",
        operationalization="AUROC ≥ 0.7 across ≥2 classes with a falsifier.",
        why_it_matters="fixture",
    )
    item = RankedQuestion(
        question=q,
        scores=ScoreAxes(
            impact=0.6,
            neglectedness=0.5,
            tractability=0.7,
            surprise=0.5,
            answerability=0.75,
            risk=0.2,
            cost_proxy=0.3,
        ),
        curiosity_score=0.6,
        confidence=0.5,
        gap=GapEvidence(status=GapStatus.UNANSWERED, confidence=0.4, notes="Related ≠ answered"),
        flags=[],
    )
    note = feasibility_note(item)
    assert "not SFBench" in note
    assert "weighted axis" in note or "display only" in note
    brief = write_brief(item)
    assert "Feasibility note" in brief
    assert item.scores.answerability == 0.75  # unchanged — display only


def test_soundness_pass_offline():
    from fastapi.testclient import TestClient

    from artificial_curiosity.api import app
    from artificial_curiosity.soundness import soundness_pass

    out = soundness_pass(
        [
            {
                "question_id": "good",
                "question": "Which biomarkers predict remaining healthspan under interventions?",
                "operationalization": "AUROC ≥ 0.7; falsifier: AUROC ≤ 0.55.",
                "brief": "Gap status unanswered. Related literature ≠ answered.",
                "gap_status": "unanswered",
                "axes": {"answerability": 0.7, "tractability": 0.6, "risk": 0.2},
            },
            {
                "question_id": "bad",
                "question": "What is A? What is B? What is C?",
                "operationalization": "Everything and everything.",
                "brief": "The AI is curious.",
                "gap_status": "unanswered",
            },
        ]
    )
    assert out["changes_ranks"] is False
    by_id = {r["question_id"]: r["soundness"] for r in out["results"]}
    assert by_id["bad"] == "fail"
    assert by_id["good"] in ("pass", "revise")

    client = TestClient(app)
    res = client.post(
        "/v1/evals/soundness",
        json={"candidates": [{"question": "Short?", "operationalization": "x"}]},
    )
    assert res.status_code == 200
    assert res.json()["changes_ranks"] is False
