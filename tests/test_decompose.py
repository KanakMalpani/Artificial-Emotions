"""Curiosity depth — the ladder must deepen a question without answering it.

The load-bearing test here is `test_no_output_path_asserts_an_answer`: the whole
surface exists to go one step further toward a solution *while* preserving the
project's "returns unknowns, not answers" invariant. If a template edit ever
turns an output into a claim, that test is what catches it.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from artificial_emotions.api import app
from artificial_emotions.decompose import (
    MAX_DEPTH,
    SUB_QUESTION_KINDS,
    assert_free,
    decompose_question,
    decompose_ranked,
    key_terms,
)
from artificial_emotions.models import CuriosityConfig, UnansweredQuestion
from artificial_emotions.pipeline import CuriosityEngine

QUESTION = "Which biomarkers predict remaining healthspan under caloric restriction?"
OPS = "AUROC >= 0.7 on a held-out cohort with p < 0.05; effect size >= 0.3."


def _q(question: str = QUESTION, ops: str = OPS) -> UnansweredQuestion:
    return UnansweredQuestion(
        id="q-1",
        question=question,
        domain="biology",
        operationalization=ops,
        why_it_matters="Aging interventions need surrogate endpoints.",
    )


# --- the invariant ------------------------------------------------------------------


def test_no_output_path_asserts_an_answer():
    """Every string in the payload must remain a question, test, or criterion."""
    for depth in range(1, MAX_DEPTH + 1):
        payload = decompose_question(_q(), depth=depth)
        ok, offenders = assert_free(payload)
        assert ok, offenders
        assert payload["assertion_free"] is True


def test_assert_free_actually_detects_an_assertion():
    """Guard the guard — a permissive checker would make the test above vacuous."""
    ok, offenders = assert_free({"note": "The answer is that condensates drive it."})
    assert not ok
    assert offenders


def test_every_sub_question_is_phrased_as_a_question():
    payload = decompose_question(_q(), depth=2)

    def walk(nodes):
        for n in nodes:
            assert n["question"].rstrip().endswith("?"), n["question"]
            assert n["why_this_narrows_it"]
            walk(n["children"])

    walk(payload["sub_questions"])


def test_it_says_the_gap_is_still_open_afterwards():
    payload = decompose_question(_q())
    assert "not thereby answered" in payload["open_after_this"]
    assert "an answer to the question" in payload["claims_not"]


# --- structure ----------------------------------------------------------------------


def test_depth_one_covers_every_kind_once():
    payload = decompose_question(_q(), depth=1)
    assert [s["kind"] for s in payload["sub_questions"]] == list(SUB_QUESTION_KINDS)
    assert all(s["children"] == [] for s in payload["sub_questions"])


def test_depth_two_splits_only_mechanism_and_confound():
    payload = decompose_question(_q(), depth=2)
    with_children = {s["kind"] for s in payload["sub_questions"] if s["children"]}
    assert with_children == {"mechanism", "confound"}
    assert payload["sub_question_count"] == len(SUB_QUESTION_KINDS) + 4


def test_child_questions_reference_their_parent_move():
    payload = decompose_question(_q(), depth=2)
    mech = next(s for s in payload["sub_questions"] if s["kind"] == "mechanism")
    texts = " ".join(c["question"] for c in mech["children"])
    assert "mechanism" in texts
    assert all(c["narrows"] == "mechanism" for c in mech["children"])


def test_children_are_not_reparsed_parent_sentences():
    """Recursing on generated text used to produce word salad — keep it readable."""
    payload = decompose_question(_q(), depth=2)
    for sub in payload["sub_questions"]:
        for child in sub["children"]:
            assert "what observable quantity would make what" not in child["question"].lower()
            assert child["question"].count("—") == 1


def test_depth_is_clamped_to_the_supported_range():
    assert decompose_question(_q(), depth=0)["depth"] == 1
    assert decompose_question(_q(), depth=99)["depth"] == MAX_DEPTH


def test_node_ids_are_unique():
    payload = decompose_question(_q(), depth=3)
    ids = []

    def walk(nodes):
        for n in nodes:
            ids.append(n["id"])
            walk(n["children"])

    walk(payload["sub_questions"])
    assert len(ids) == len(set(ids))


# --- falsifiers ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("ops", "expected"),
    [
        ("AUROC >= 0.7 on held-out data.", "AUROC < 0.7"),
        ("Error rate <= 5%.", "Error rate > 5%"),
        ("Effect size > 0.3.", "Effect size ≤ 0.3"),
        ("p < 0.05.", "p ≥ 0.05"),
    ],
)
def test_stated_thresholds_become_their_refutation(ops: str, expected: str):
    payload = decompose_question(_q(ops=ops))
    refuted = [f["refuted_if"] for f in payload["falsifiers"]]
    assert any(expected in r for r in refuted), refuted


def test_falsifiers_exist_even_with_no_numeric_criteria():
    payload = decompose_question(_q(ops="It works better."))
    sources = {f["source"] for f in payload["falsifiers"]}
    assert {"gap", "framing"} <= sources


def test_a_vague_operationalization_is_itself_flagged():
    payload = decompose_question(_q(ops="Better."))
    refuted = " ".join(f["refuted_if"] for f in payload["falsifiers"])
    assert "disagree" in refuted


# --- first step and stop rules -------------------------------------------------------


def test_missing_criteria_forces_measurement_first():
    step = decompose_question(_q(ops=""))["discriminating_step"]
    assert step["kind"] == "measurement"


def test_low_answerability_probes_the_boundary_first():
    step = decompose_question(_q(), answerability=0.2, tractability=0.9)["discriminating_step"]
    assert step["kind"] == "boundary"


def test_a_well_posed_question_starts_by_eliminating_rivals():
    step = decompose_question(_q(), answerability=0.8, tractability=0.8)["discriminating_step"]
    assert step["kind"] == "confound"


def test_the_first_step_disclaims_optimality():
    step = decompose_question(_q())["discriminating_step"]
    assert "not a computed expected-information-gain" in step["honesty"]


def test_elevated_risk_adds_a_review_stop_rule():
    rules = " ".join(decompose_question(_q(), risk=0.8)["stop_rules"])
    assert "review" in rules


def test_low_tractability_requires_a_pilot_first():
    rules = " ".join(decompose_question(_q(), tractability=0.2)["stop_rules"])
    assert "pilot" in rules


# --- ranked integration --------------------------------------------------------------


def test_decompose_ranked_carries_the_ranking_context():
    items = CuriosityEngine(
        CuriosityConfig(domain="ai", use_llm=False, use_literature=False, n_return=1)
    ).run()
    payload = decompose_ranked(items[0], depth=2)
    assert payload["rank"] == items[0].rank
    assert payload["gap_status"]
    assert payload["curiosity_score"] == items[0].curiosity_score
    assert payload["assertion_free"] is True


def test_decomposition_is_deterministic():
    a = json.dumps(decompose_question(_q(), depth=3), sort_keys=True)
    b = json.dumps(decompose_question(_q(), depth=3), sort_keys=True)
    assert a == b


def test_key_terms_drops_stopwords_and_keeps_order():
    terms = key_terms("Which protein condensates drive proteostasis failure?")
    assert "which" not in terms
    assert terms[0] == "protein"


# --- surfaces -------------------------------------------------------------------------


def test_http_decompose_endpoint():
    client = TestClient(app)
    res = client.post(
        "/v1/curiosity/decompose",
        json={"question": QUESTION, "operationalization": OPS, "depth": 2},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["assertion_free"] is True
    assert body["sub_question_count"] == len(SUB_QUESTION_KINDS) + 4


def test_http_decompose_rejects_a_too_short_question():
    client = TestClient(app)
    assert client.post("/v1/curiosity/decompose", json={"question": "why?"}).status_code == 422


def test_http_decompose_rejects_out_of_range_depth():
    client = TestClient(app)
    res = client.post("/v1/curiosity/decompose", json={"question": QUESTION, "depth": 9})
    assert res.status_code == 422


def test_mcp_tool_dispatches():
    from artificial_emotions.agent_tools import dispatch_tool, mcp_tool_list

    assert "decompose_question" in {t["name"] for t in mcp_tool_list()}
    out = dispatch_tool("decompose_question", {"question": QUESTION, "operationalization": OPS})
    assert out["assertion_free"] is True


def test_cli_decompose_json_and_text(capsys):
    from artificial_emotions.cli import main

    assert main(["decompose", QUESTION, "--ops", OPS, "--depth", "2", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["assertion_free"] is True

    assert main(["decompose", QUESTION, "--ops", OPS]) == 0
    text = capsys.readouterr().out
    assert "Do this first" in text
    assert "Falsifiers:" in text
    assert "Stop rules:" in text
