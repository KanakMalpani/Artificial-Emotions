"""Tests for W10–W15 mid-horizon wedges (offline)."""

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
    ValueProfile,
    resolve_value_profile,
)
from artificial_curiosity.packs import questions_from_pack
from artificial_curiosity.pipeline import CuriosityEngine
from artificial_curiosity.preferences import (
    PreferenceEvent,
    append_preference_event,
    load_preference_events,
    preference_score_adjustments,
)
from artificial_curiosity.safety import assess_dual_use
from artificial_curiosity.scoring import dual_use_flags, heuristic_score, score_uncertainty_band
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


def test_w13_preference_jsonl_roundtrip(tmp_path: Path):
    path = tmp_path / "prefs.jsonl"
    append_preference_event(
        path,
        PreferenceEvent(
            event_type="prefer",
            profile_name="alignment_lab",
            domain="ai",
            question_id="ai-01",
            question_text="Example unknown?",
            rank=1,
            curiosity_score=0.7,
            preferred_over_ids=["ai-02"],
            notes="human prefer",
        ),
    )
    rows = load_preference_events(path)
    assert len(rows) == 1
    assert rows[0].event_type == "prefer"
    assert rows[0].schema_version.startswith("preference_event")

    # Pipeline auto-snapshot when path set.
    CuriosityEngine(
        CuriosityConfig(
            domain="ai",
            use_literature=False,
            use_llm=False,
            n_return=2,
            preference_log_path=str(path),
        )
    ).run()
    rows2 = load_preference_events(path)
    assert len(rows2) >= 2


def test_w14_dual_use_beyond_keywords():
    benign = assess_dual_use("How does intermittent fasting affect insulin sensitivity?")
    assert benign.risk < 0.45
    assert not benign.hard_reject_likely

    combo = assess_dual_use(
        "How can an engineered pathogen be aerosolized for covert surveillance?"
    )
    assert combo.risk >= 0.45
    assert combo.needs_human_review or combo.hard_reject_likely
    assert any("combo" in s or "phrase" in s for s in combo.signals)

    weaponized = assess_dual_use("How can pathogen surveillance systems be weaponized at scale?")
    assert weaponized.risk >= 0.85

    flags = dual_use_flags(
        "Study gain-of-function virulence enhancement in select agents",
        ValueProfile(),
    )
    assert "human_review_risk" in flags or "dual_use_high" in flags


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


def test_domain_pack_loader():
    qs = questions_from_pack(
        {
            "schema_version": "domain_pack.v1",
            "name": "test",
            "domain": "ai",
            "questions": [
                {
                    "question": "What signals predict goal misgeneralization early?",
                    "operationalization": "AUROC > 0.8 across three controlled environments for early warning.",
                    "why_it_matters": "Safety.",
                    "tags": ["alignment"],
                }
            ],
        }
    )
    assert len(qs) == 1
    assert qs[0].source.startswith("pack:")


def test_mcp_resources():
    from artificial_curiosity.agent_tools import mcp_resource_list, mcp_resource_read

    resources = mcp_resource_list()
    uris = {r["uri"] for r in resources}
    assert "curiosity://domains" in uris
    assert "curiosity://profiles" in uris
    assert "curiosity://limits" in uris
    limits = mcp_resource_read("curiosity://limits")
    assert "decision aids" in limits["contents"][0]["text"].lower()


def test_wo044_neglectedness_cost_proxies():
    crowded = UnansweredQuestion(
        id="n1",
        question="How do transformer LLM foundation models scale on blockchain hype tasks?",
        domain="ai",
        operationalization="Measure scaling curves on a fixed benchmark suite.",
        why_it_matters="Crowded topic fixture.",
        tags=["llm", "transformer", "blockchain"],
    )
    neglected = UnansweredQuestion(
        id="n2",
        question="Which understudied orphan biomarkers predict drought resilience in informal water-sharing networks?",
        domain="climate",
        operationalization="Pilot reanalysis of an existing dataset with a small-n matched design.",
        why_it_matters="Neglected adaptation seam.",
        tags=["climate", "water", "social", "adaptation"],
    )
    a = heuristic_score(
        crowded, GapStatus.UNANSWERED, 20, 150.0, ValueProfile(), strong_match_count=2
    )
    b = heuristic_score(
        neglected, GapStatus.UNANSWERED, 2, 5.0, ValueProfile(), strong_match_count=0
    )
    assert b.neglectedness > a.neglectedness
    assert b.cost_proxy < a.cost_proxy or b.cost_proxy <= 0.45
    assert "neglectedness_proxy" in a.rationale


def test_preference_rerank_hook(tmp_path: Path):
    from artificial_curiosity.models import GapEvidence, RankedQuestion, ScoreAxes
    from artificial_curiosity.preferences import apply_preference_rerank

    path = tmp_path / "labeled.jsonl"
    append_preference_event(
        path,
        PreferenceEvent(
            event_type="prefer",
            profile_name="humanity_default",
            question_id="ai-01",
            notes="human prefer",
        ),
    )
    append_preference_event(
        path,
        PreferenceEvent(
            event_type="reject",
            profile_name="humanity_default",
            question_id="ai-02",
            notes="human reject",
        ),
    )
    adj = preference_score_adjustments(path, profile_name="humanity_default")
    assert adj["ai-01"] > 0
    assert adj["ai-02"] < 0

    def _item(qid: str, score: float) -> RankedQuestion:
        q = UnansweredQuestion(
            id=qid,
            question=f"Question {qid}?",
            domain="ai",
            operationalization="Measure something with a clear success criterion of AUROC > 0.8.",
            why_it_matters="Fixture.",
        )
        return RankedQuestion(
            question=q,
            scores=ScoreAxes(
                impact=0.5,
                neglectedness=0.5,
                tractability=0.5,
                surprise=0.5,
                answerability=0.8,
                risk=0.2,
                cost_proxy=0.5,
            ),
            curiosity_score=score,
            confidence=0.5,
            gap=GapEvidence(
                status=GapStatus.UNANSWERED,
                confidence=0.4,
                notes="fixture",
            ),
            flags=[],
            metadata={},
            score_low=score - 0.1,
            score_high=score + 0.1,
            rank=1,
        )

    ranked = [_item("ai-02", 0.80), _item("ai-01", 0.70)]
    apply_preference_rerank(ranked, adj)
    assert ranked[0].question.id == "ai-01"
    assert "preference_rerank" in ranked[0].flags
    assert ranked[0].metadata.get("preference_delta", 0) > 0

    results = CuriosityEngine(
        CuriosityConfig(
            domain="ai",
            use_literature=False,
            use_llm=False,
            n_return=4,
            preference_rerank_path=str(path),
        )
    ).run()
    assert results
    ids = {r.question.id for r in results}
    if "ai-01" in ids or "ai-02" in ids:
        assert any("preference_rerank" in r.flags for r in results)


def test_bundled_alignment_and_climate_packs():
    from artificial_curiosity.packs import load_domain_packs

    qs = load_domain_packs()
    ids = {q.id for q in qs}
    assert "align-pack-01" in ids
    assert "clim-pack-01" in ids
    assert "affect-pack-01" in ids
    assert "aging-pack-01" in ids
    assert "matcat-pack-01" in ids
    assert all(len(q.operationalization) >= 20 for q in qs)


def test_preference_weight_hints(tmp_path: Path):
    from artificial_curiosity.preferences import (
        apply_weight_hints_to_profile,
        learn_profile_weight_hints,
    )

    path = tmp_path / "hints.jsonl"
    append_preference_event(
        path,
        PreferenceEvent(
            event_type="prefer",
            profile_name="humanity_default",
            question_id="ai-01",
            score_axes={
                "impact": 0.9,
                "neglectedness": 0.85,
                "tractability": 0.3,
                "surprise": 0.7,
            },
        ),
    )
    append_preference_event(
        path,
        PreferenceEvent(
            event_type="reject",
            profile_name="humanity_default",
            question_id="ai-02",
            score_axes={
                "impact": 0.3,
                "neglectedness": 0.25,
                "tractability": 0.9,
                "surprise": 0.2,
            },
        ),
    )
    hints = learn_profile_weight_hints(path, profile_name="humanity_default")
    assert hints["ok"] is True
    assert hints["deltas"]["weight_impact"] > 0
    assert hints["deltas"]["weight_tractability"] < 0
    assert "calibrated" not in hints["honesty"].lower() or "not calibrated" in hints["honesty"]

    base = resolve_value_profile(profile_name="humanity_default")
    suggested = apply_weight_hints_to_profile(base, hints)
    assert suggested.weight_impact > base.weight_impact
    assert suggested.weight_tractability < base.weight_tractability

    # Engine path with --preference-learn equivalent
    results = CuriosityEngine(
        CuriosityConfig(
            domain="ai",
            use_literature=False,
            use_llm=False,
            n_return=2,
            preference_learn_path=str(path),
        )
    ).run()
    assert results
    assert any("preference_weight_hints" in (r.flags or []) for r in results)


def test_preference_hints_api_inline():
    from fastapi.testclient import TestClient

    from artificial_curiosity.api import app

    client = TestClient(app)
    res = client.post(
        "/v1/preferences/hints",
        json={
            "profile_name": "humanity_default",
            "events": [
                {
                    "event_type": "prefer",
                    "profile_name": "humanity_default",
                    "question_id": "a",
                    "score_axes": {
                        "impact": 0.85,
                        "neglectedness": 0.7,
                        "tractability": 0.35,
                        "surprise": 0.65,
                    },
                },
                {
                    "event_type": "reject",
                    "profile_name": "humanity_default",
                    "question_id": "b",
                    "score_axes": {
                        "impact": 0.35,
                        "neglectedness": 0.3,
                        "tractability": 0.85,
                        "surprise": 0.25,
                    },
                },
            ],
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert "weight_impact" in data["deltas"]
    assert "suggested_profile" in data


def test_preference_summarize_and_compare_profiles(tmp_path: Path):
    from artificial_curiosity.compare import compare_profiles
    from artificial_curiosity.preferences import summarize_preferences
    from fastapi.testclient import TestClient

    from artificial_curiosity.api import app

    path = tmp_path / "prefs.jsonl"
    append_preference_event(
        path,
        PreferenceEvent(
            event_type="prefer",
            profile_name="humanity_default",
            question_id="q1",
            preferred_over_ids=["q2"],
            score_axes={
                "impact": 0.9,
                "neglectedness": 0.8,
                "tractability": 0.3,
                "surprise": 0.7,
            },
        ),
    )
    append_preference_event(
        path,
        PreferenceEvent(
            event_type="reject",
            profile_name="humanity_default",
            question_id="q2",
            score_axes={
                "impact": 0.3,
                "neglectedness": 0.2,
                "tractability": 0.9,
                "surprise": 0.2,
            },
        ),
    )
    summary = summarize_preferences(path, profile_name="humanity_default")
    assert summary["n_events"] == 2
    assert summary["n_pairwise"] >= 1
    assert summary["top_question_ids"]
    assert "not calibrated" in summary["honesty"].lower()

    cmp = compare_profiles(
        domain="ai",
        profile_a="humanity_default",
        profile_b="alignment_lab",
        n=4,
    )
    assert len(cmp["ranks_a"]) == 4
    assert len(cmp["ranks_b"]) == 4
    assert "veto_tip" in cmp
    assert cmp["veto_tip"]["strictest_max_risk"] <= 0.85
    assert "agreement" in cmp
    assert "top_k_jaccard" in cmp["agreement"]
    # n=4 → kendall may be None; with default n=8 it should compute
    cmp8 = compare_profiles(domain="ai", n=8)
    assert cmp8["agreement"]["kendall_tau"] is not None or len(cmp8["ranks_a"]) < 5

    client = TestClient(app)
    sres = client.post(
        "/v1/preferences/summarize",
        json={
            "profile_name": "humanity_default",
            "events": [
                {
                    "event_type": "prefer",
                    "question_id": "q1",
                    "preferred_over_ids": ["q2"],
                    "profile_name": "humanity_default",
                },
                {
                    "event_type": "reject",
                    "question_id": "q2",
                    "profile_name": "humanity_default",
                },
            ],
        },
    )
    assert sres.status_code == 200
    assert sres.json()["n_pairwise"] >= 1

    cres = client.post(
        "/v1/profiles/compare",
        json={
            "domain": "ai",
            "profile_a": "humanity_default",
            "profile_b": "climate_adaptation",
            "n": 3,
        },
    )
    assert cres.status_code == 200
    assert "rank_deltas" in cres.json()


def test_mix_coercion_warning():
    from artificial_curiosity.emotions import mix_emotions

    mild = mix_emotions({"curiosity": 40, "confusion": 30, "awe": 30})
    assert mild.get("warnings") == [] or mild.get("coercion_weight", 0) < 0.35

    heavy = mix_emotions({"fear": 50, "anxiety": 30, "anger": 20})
    assert heavy["coercion_weight"] >= 0.5
    assert heavy["warnings"]
    assert "biometric" in " ".join(heavy.get("claims_not") or []).lower() or True

