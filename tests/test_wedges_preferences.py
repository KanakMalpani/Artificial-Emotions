"""Preference JSONL flywheel: rerank, weight hints, pairing, voting (W13)."""

from __future__ import annotations

from pathlib import Path

from artificial_curiosity.models import (
    CuriosityConfig,
    GapStatus,
    UnansweredQuestion,
    resolve_value_profile,
)
from artificial_curiosity.pipeline import CuriosityEngine
from artificial_curiosity.preferences import (
    PreferenceEvent,
    append_preference_event,
    load_preference_events,
    preference_score_adjustments,
)


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
    from fastapi.testclient import TestClient

    from artificial_curiosity.api import app
    from artificial_curiosity.compare import compare_profiles
    from artificial_curiosity.preferences import summarize_preferences

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


def test_preference_outcome_summarize_counts():
    from artificial_curiosity.preferences import summarize_preferences

    summary = summarize_preferences(
        [
            {
                "event_type": "prefer",
                "profile_name": "humanity_default",
                "question_id": "a",
                "preferred_over_ids": ["b"],
            },
            {
                "event_type": "outcome",
                "profile_name": "humanity_default",
                "question_id": "a",
                "labels": {"result": "partial_progress"},
            },
            {
                "event_type": "outcome",
                "profile_name": "humanity_default",
                "question_id": "a",
                "labels": {"result": "null"},
            },
        ],
        profile_name="humanity_default",
    )
    assert summary["outcomes"]["n_outcome"] == 2
    assert summary["outcomes"]["by_result"]["partial_progress"] == 1
    assert summary["outcomes"]["by_result"]["null"] == 1
    assert (
        "certificate" in (summary["honesty"] or "").lower()
        or "small" in (summary["honesty"] or "").lower()
    )


def test_suggest_next_pair_and_bt_gate():
    from fastapi.testclient import TestClient

    from artificial_curiosity.api import app
    from artificial_curiosity.preferences import (
        PreferenceEvent,
        fit_bt_offline,
        suggest_next_pair,
        summarize_preferences,
    )

    cands = [
        {"question_id": "a", "rank": 1, "curiosity_score": 0.9},
        {"question_id": "b", "rank": 2, "curiosity_score": 0.88},
        {"question_id": "c", "rank": 3, "curiosity_score": 0.7},
    ]
    prior = [
        PreferenceEvent(
            event_type="prefer",
            profile_name="humanity_default",
            question_id="a",
            preferred_over_ids=["b"],
        )
    ]
    nxt = suggest_next_pair(cands, prior, profile_name="humanity_default")
    assert nxt["ok"] is True
    pair = nxt["pair"]
    ids = {pair["a"]["question_id"], pair["b"]["question_id"]}
    assert ids != {"a", "b"}

    bt = fit_bt_offline(prior, profile_name="humanity_default", min_pairs=30)
    assert bt["ok"] is False
    assert bt["skills"] is None

    summary = summarize_preferences(
        [
            PreferenceEvent(
                event_type="tie",
                profile_name="humanity_default",
                question_id="a",
                preferred_over_ids=["b"],
            )
        ],
        profile_name="humanity_default",
    )
    assert summary["counts_by_type"].get("tie") == 1

    client = TestClient(app)
    res = client.post(
        "/v1/preferences/suggest-pair",
        json={"candidates": cands, "profile_name": "humanity_default"},
    )
    assert res.status_code == 200
    assert res.json()["ok"] is True


def test_cross_model_vote_offline():
    from fastapi.testclient import TestClient

    from artificial_curiosity.api import app
    from artificial_curiosity.hybrid_vote import cross_model_vote

    out = cross_model_vote(
        [
            {
                "question_id": "good",
                "question": "Which circulating biomarkers best predict remaining healthspan under interventions?",
                "operationalization": "AUROC ≥ 0.7; falsifier: AUROC ≤ 0.55 reduces confidence.",
            },
            {
                "question_id": "bad",
                "question": "What causes aging and how do we cure cancer and what is consciousness?",
                "operationalization": "Everything.",
            },
        ]
    )
    assert out["changes_ranks"] is False
    assert out["n_candidates"] == 2
    by_id = {v["question_id"]: v["decision"] for v in out["votes"]}
    assert by_id["bad"] in ("drop", "rewrite")
    assert by_id["good"] in ("keep", "rewrite")

    client = TestClient(app)
    res = client.post(
        "/v1/evals/cross-model-vote",
        json={
            "candidates": [
                {"question": "Short?", "operationalization": "x"},
            ]
        },
    )
    assert res.status_code == 200
    assert res.json()["changes_ranks"] is False
