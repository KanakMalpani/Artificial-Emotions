"""Dual-use safety, domain packs, constitution compare, and MCP tiers (W14)."""

from __future__ import annotations

from pathlib import Path

from artificial_emotions.models import (
    GapStatus,
    UnansweredQuestion,
    ValueProfile,
)
from artificial_emotions.packs import questions_from_pack
from artificial_emotions.safety import assess_dual_use
from artificial_emotions.scoring import dual_use_flags, heuristic_score


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


def test_dual_use_redteam_fixtures():
    import json

    from artificial_emotions.models import ValueProfile, get_profile
    from artificial_emotions.safety import assess_dual_use
    from artificial_emotions.scoring import dual_use_flags

    root = Path(__file__).resolve().parents[1]
    data = json.loads(
        (root / "evals" / "fixtures" / "dual_use_redteam_v1.json").read_text(encoding="utf-8")
    )
    demo = get_profile("public_demo_strict_risk")
    assert isinstance(demo, ValueProfile)
    for item in data["items"]:
        text = item["question_text"]
        expect = item["expect_risk"]
        assessment = assess_dual_use(text)
        flags = dual_use_flags(text, demo)
        if expect == "low":
            assert assessment.risk < 0.45, item["question_id"]
            assert not assessment.hard_reject_likely
        else:
            assert assessment.risk >= 0.45 or assessment.needs_human_review, item["question_id"]
            assert (
                "dual_use_high" in flags
                or "human_review_risk" in flags
                or assessment.hard_reject_likely
            ), item["question_id"]


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


def test_bundled_alignment_and_climate_packs():
    from artificial_emotions.packs import load_domain_packs

    qs = load_domain_packs()
    ids = {q.id for q in qs}
    assert "align-pack-01" in ids
    assert "clim-pack-01" in ids
    assert "affect-pack-01" in ids
    assert "aging-pack-01" in ids
    assert "matcat-pack-01" in ids
    assert all(len(q.operationalization) >= 20 for q in qs)


def test_mcp_resources():
    from artificial_emotions.agent_tools import mcp_resource_list, mcp_resource_read

    resources = mcp_resource_list()
    uris = {r["uri"] for r in resources}
    assert "curiosity://domains" in uris
    assert "curiosity://profiles" in uris
    assert "curiosity://limits" in uris
    limits = mcp_resource_read("curiosity://limits")
    assert "decision aids" in limits["contents"][0]["text"].lower()


def test_constitution_compare_and_mcp_tiers():
    import os

    from fastapi.testclient import TestClient

    from artificial_emotions.agent_tools import mcp_tool_list, mcp_tool_tiers
    from artificial_emotions.api import app
    from artificial_emotions.compare import apply_risk_veto, compare_constitution

    out = compare_constitution(
        domain="ai",
        primary_profile="alignment_lab",
        veto_profile="public_demo_strict_risk",
        n=6,
    )
    assert "veto_applied" in out
    assert out["constitution"]["veto_profile"] == "public_demo_strict_risk"
    assert "consensus" in (out.get("honesty") or "").lower()
    assert out["veto_applied"]["max_risk"] <= 0.55

    veto = apply_risk_veto(
        [
            {"rank": 1, "question": "safe", "axes": {"risk": 0.2}},
            {"rank": 2, "question": "risky", "axes": {"risk": 0.9}},
        ],
        max_risk=0.55,
    )
    assert veto["n_kept"] == 1
    assert veto["n_flagged"] == 1
    assert veto["flagged"][0]["veto"] == "exceeds_max_risk"

    prev = os.environ.get("CURIOSITY_MCP_TIER")
    try:
        os.environ["CURIOSITY_MCP_TIER"] = "core"
        names = {t["name"] for t in mcp_tool_list()}
        assert "list_profiles" in names
        assert "mix_emotions" not in names
        assert "voi_worksheet" not in names
        tiers = mcp_tool_tiers()
        assert tiers["active"] == "core"
        assert "core" in tiers["tiers"]
    finally:
        if prev is None:
            os.environ.pop("CURIOSITY_MCP_TIER", None)
        else:
            os.environ["CURIOSITY_MCP_TIER"] = prev

    client = TestClient(app)
    res = client.post(
        "/v1/profiles/constitution-compare",
        json={
            "domain": "ai",
            "primary_profile": "alignment_lab",
            "veto_profile": "public_demo_strict_risk",
            "n": 5,
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert "veto_applied" in body
    agent = client.get("/v1/agent")
    assert agent.status_code == 200
    assert "tool_tiers" in agent.json()["mcp"]
    assert "constitution_compare" in agent.json()["mcp"]["tools"]


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
