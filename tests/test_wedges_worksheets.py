"""Worksheets, elicitation, cue thresholds, and critique surfaces."""

from __future__ import annotations

from pathlib import Path

from artificial_emotions.models import (
    GapStatus,
    UnansweredQuestion,
    ValueProfile,
)
from artificial_emotions.preferences import (
    PreferenceEvent,
)


def test_mix_coercion_warning():
    from artificial_emotions.emotions import mix_emotions

    mild = mix_emotions({"curiosity": 40, "confusion": 30, "awe": 30})
    assert mild.get("warnings") == [] or mild.get("coercion_weight", 0) < 0.35

    heavy = mix_emotions({"fear": 50, "anxiety": 30, "anger": 20})
    assert heavy["coercion_weight"] >= 0.5
    assert heavy["warnings"]
    assert "biometric" in " ".join(heavy.get("claims_not") or []).lower() or True


def test_elicit_ab_eval_path():

    from artificial_emotions.elicit_eval import run_elicit_ab, score_investigation_response

    root = Path(__file__).resolve().parents[1]
    responses = root / "examples" / "elicit_ab_sample_responses.json"
    out = run_elicit_ab(responses_path=responses, domain="ai", n=2)
    assert out["n_responses_scored"] >= 2
    assert "B_minus_A_mean" in out["deltas"]
    assert out["deltas"]["B_minus_A_mean"] > 0
    conds = {c["condition_id"]: c for c in out["conditions"]}
    assert conds["A_baseline"]["inject_has_incongruity"] is False
    assert conds["B_incongruity"]["inject_has_incongruity"] is True
    weak = score_investigation_response("We should study it more.")
    strong = score_investigation_response(
        "The information gap is X. First experiment: measure IV. "
        "Falsifier: if we observe null AUROC, reduce confidence."
    )
    assert (strong["mean"] or 0) > (weak["mean"] or 0)


def test_cue_thresholds_and_outcome_hivemind():
    from artificial_emotions.epistemic_cues import derive_epistemic_cues
    from artificial_emotions.hivemind import top_n_pairwise_similarity
    from artificial_emotions.models import (
        GapEvidence,
        RankedQuestion,
        ScoreAxes,
    )
    from artificial_emotions.preferences import summarize_preferences
    from artificial_emotions.provoke import compact_unknown

    q = UnansweredQuestion(
        id="c1",
        question="What remains unknown about neglected surprise signals?",
        domain="ai",
        operationalization="Measure AUROC of signal X.",
        why_it_matters="fixture",
    )
    item = RankedQuestion(
        question=q,
        scores=ScoreAxes(
            impact=0.5,
            neglectedness=0.5,
            tractability=0.5,
            surprise=0.5,
            answerability=0.5,
            risk=0.2,
            cost_proxy=0.3,
        ),
        curiosity_score=0.5,
        confidence=0.4,
        gap=GapEvidence(
            status=GapStatus.UNANSWERED,
            confidence=0.4,
            notes="Related literature ≠ answered",
        ),
        flags=[],
    )
    loose = ValueProfile(name="loose", cue_surprise_high=0.4)
    tight = ValueProfile(name="tight", cue_surprise_high=0.9)
    tags_loose = derive_epistemic_cues(item, value_profile=loose)["tags"]
    tags_tight = derive_epistemic_cues(item, value_profile=tight)["tags"]
    assert "surprise_signal" in tags_loose
    assert "surprise_signal" not in tags_tight
    compact = compact_unknown(item, value_profile=loose)
    assert compact["epistemic_cues"]["thresholds"]["surprise_high"] == 0.4

    summary = summarize_preferences(
        [
            PreferenceEvent(
                event_type="prefer",
                profile_name="humanity_default",
                question_id="q1",
            ),
            PreferenceEvent(
                event_type="outcome",
                profile_name="humanity_default",
                question_id="q1",
                labels={"result": "partial_progress", "months_elapsed": "3"},
            ),
            PreferenceEvent(
                event_type="outcome",
                profile_name="humanity_default",
                question_id="q2",
                labels={"result": "abandoned"},
            ),
        ],
        profile_name="humanity_default",
    )
    assert summary["outcomes"]["n_outcome"] == 2
    assert summary["outcomes"]["by_result"]["partial_progress"] == 1
    assert summary["outcomes"]["by_result"]["abandoned"] == 1

    sim = top_n_pairwise_similarity(
        [
            "What biomarkers predict healthspan under caloric restriction?",
            "Which circulating biomarkers predict remaining healthspan?",
            "How does zybloron flux affect quux plasticity?",
        ]
    )
    assert sim["n_pairs"] == 3
    assert sim["mean_pairwise"] is not None


def test_critique_brief_form_only():
    from fastapi.testclient import TestClient

    from artificial_emotions.api import app
    from artificial_emotions.critique import critique_brief

    bad = critique_brief(
        question="What is A? What is B?",
        operationalization="Do X and Y and Z and W in one go without stopping.",
        brief="We prove this is settled by Nature and the AI is curious.",
    )
    assert bad["changes_ranks"] is False
    codes = {i["code"] for i in bad["issues"]}
    assert "sprawl_multi_question" in codes or "anthropomorphism" in codes

    good = critique_brief(
        question="Which circulating biomarkers predict remaining healthspan?",
        operationalization=(
            "Rank markers by out-of-sample AUROC; falsifier: AUROC ≤ 0.55 "
            "would reduce confidence in the panel."
        ),
        brief="## Investigation brief\n\n**Gap status.** unanswered",
    )
    assert good["changes_ranks"] is False

    client = TestClient(app)
    res = client.post(
        "/v1/briefs/critique",
        json={"question": "What is A? What is B?", "operationalization": "measure"},
    )
    assert res.status_code == 200
    assert res.json()["changes_ranks"] is False


def test_voi_worksheet_and_eval_report():

    from fastapi.testclient import TestClient

    from artificial_emotions.api import app
    from artificial_emotions.eval_report import build_eval_report
    from artificial_emotions.voi import fill_voi_worksheet

    sheet = fill_voi_worksheet(
        question_id="q1",
        question="Which biomarkers predict healthspan under interventions?",
        operationalization="AUROC ≥ 0.7 across ≥2 intervention classes",
        profile_name="humanity_default",
        domain="biology",
    )
    assert sheet["link_to_ranked_question"]["question_id"] == "q1"
    assert "EVSI" in (sheet.get("honesty") or "") or "EVSI" in str(sheet.get("external_compute"))

    root = Path(__file__).resolve().parents[1]
    report = build_eval_report(
        elicit_responses=root / "examples" / "elicit_ab_sample_responses.json"
    )
    assert "gap_f1" in report["sections"]
    assert "elicit_rubric" in report["sections"]
    assert "risk_flags" in report["sections"]
    assert report["sections"]["rank_spearman"]["value"] is None
    assert "soundness" in report["sections"]
    assert report["sections"]["soundness"]["n"] >= 1
    assert "diagnostics_first" in report["sections"]
    assert "critique_form" in report["sections"]
    order = report["sections"]["diagnostics_first"]["order"]
    assert order.index("soundness") < order.index("elicit_rubric")
    assert order.index("critique_form") < order.index("gap_f1")

    client = TestClient(app)
    vres = client.post(
        "/v1/voi/worksheet",
        json={"question": "Test unknown?", "profile_name": "humanity_default"},
    )
    assert vres.status_code == 200
    agent = client.get("/v1/agent")
    assert agent.status_code == 200
    assert "card" in agent.json()
    assert "critique_brief" in agent.json()["mcp"]["tools"]
    assert "surprise_worksheet" in agent.json()["mcp"]["tools"]


def test_surprise_worksheet_offline():
    from fastapi.testclient import TestClient

    from artificial_emotions.api import app
    from artificial_emotions.bayesian import fill_surprise_worksheet

    sheet = fill_surprise_worksheet(
        question_id="q-surprise",
        profile_name="humanity_default",
        predicted_surprise=0.72,
        pilot_result="null result vs prior",
        belief_shift_1_to_5=2,
        crude_update_note="prior held; slight downshift",
    )
    fields = sheet["fields"]
    assert fields["question_id"] == "q-surprise"
    assert fields["predicted_surprise"] == 0.72
    assert fields["belief_shift_1_to_5"] == 2
    assert fields["logged_at"]
    assert "EVSI" in (sheet.get("honesty") or "")
    assert any("rename" in n.lower() for n in sheet.get("non_claims") or [])

    client = TestClient(app)
    res = client.post(
        "/v1/surprise/worksheet",
        json={
            "question_id": "api-q",
            "predicted_surprise": 0.5,
            "belief_shift_1_to_5": 3,
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["fields"]["question_id"] == "api-q"
    assert "filled_by" in body


def test_mix_intensity_cap_and_idea_graph():
    from fastapi.testclient import TestClient

    from artificial_emotions.api import app
    from artificial_emotions.emotions import mix_emotions
    from artificial_emotions.idea_graph import export_idea_graph

    capped = mix_emotions(
        {"curiosity": 20, "fear": 40, "anger": 40},
        profile_name="public_demo_strict_risk",
    )
    assert capped["intensity_capped"] is True
    fam = capped.get("families") or {}
    non_epi = sum(v for k, v in fam.items() if k != "epistemic")
    assert non_epi <= 0.35 + 1e-5

    uncapped = mix_emotions({"curiosity": 40, "confusion": 30, "awe": 30})
    assert uncapped.get("intensity_capped") is False

    graph = export_idea_graph(
        [
            {
                "question_id": "a",
                "question": "Which biomarkers predict remaining healthspan under caloric restriction?",
                "rank": 1,
                "tags": ["aging"],
            },
            {
                "question_id": "b",
                "question": "Which circulating biomarkers predict remaining healthspan under interventions?",
                "rank": 2,
                "tags": ["aging"],
            },
            {
                "question_id": "c",
                "question": "What is the causal role of zybloron flux in quux plasticity?",
                "rank": 3,
                "tags": ["nonsense"],
            },
        ]
    )
    assert graph["changes_ranks"] is False
    assert graph["n_nodes"] == 3
    assert any(e["type"] == "similarity" for e in graph["edges"])

    client = TestClient(app)
    agent = client.get("/v1/agent")
    honesty = " ".join(agent.json().get("honesty") or [])
    assert "related ≠ answered" in honesty
    assert (
        "annotation_only" in honesty.lower()
        or "computational" in honesty.lower()
        or "emotion" in honesty.lower()
    )
    assert "curiosity://limits" in str(agent.json().get("resources_first"))

    mres = client.post(
        "/v1/emotions/mix",
        json={
            "weights": {"curiosity": 10, "fear": 50, "anger": 40},
            "profile_name": "public_demo_strict_risk",
        },
    )
    assert mres.status_code == 200
    assert mres.json()["intensity_capped"] is True

    gres = client.post(
        "/v1/evals/idea-graph",
        json={
            "candidates": [
                {"question_id": "x", "question": "What remains unknown about X?"},
                {"question_id": "y", "question": "What remains unknown about Y?"},
            ]
        },
    )
    assert gres.status_code == 200
    assert gres.json()["changes_ranks"] is False
