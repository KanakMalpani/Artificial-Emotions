"""Chunk 4 elicit A/B + dual-use red-team fixture regression.

Small corpus expansion only — not a red-team league, not EES, not dual-use solved.
"""

from __future__ import annotations

import json
from pathlib import Path

from artificial_emotions.elicit_eval import run_elicit_ab
from artificial_emotions.models import ValueProfile, get_profile
from artificial_emotions.safety import assess_dual_use
from artificial_emotions.scoring import dual_use_flags

_ROOT = Path(__file__).resolve().parents[1]
_DUAL_USE = _ROOT / "evals" / "fixtures" / "dual_use_redteam_v1.json"
_ELICIT_AI = _ROOT / "examples" / "elicit_ab_sample_responses.json"
_ELICIT_CLIMATE = _ROOT / "examples" / "elicit_ab_sample_responses_climate.json"
_ELICIT_PROTOCOL = _ROOT / "examples" / "elicit_ab_protocol.json"

_ALLOWED_EXPECT = frozenset({"low", "review_or_high", "residual_may_miss"})


def _load_dual_use() -> dict:
    data = json.loads(_DUAL_USE.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_dual_use_corpus_is_a_small_regression_not_a_league():
    data = _load_dual_use()
    honesty = (data.get("honesty") or "").lower()
    assert "oracle" in honesty or "not dual-use solved" in honesty
    assert "league" in honesty
    assert "not dual-use solved" in honesty
    items = data["items"]
    assert 10 <= len(items) <= 24, "small expansion only — not a continuous F1–F15 league"
    expects = {item["expect_risk"] for item in items}
    assert expects <= _ALLOWED_EXPECT
    assert "low" in expects
    assert "review_or_high" in expects
    assert "residual_may_miss" in expects
    assert sum(1 for i in items if i["expect_risk"] == "low") >= 4
    assert sum(1 for i in items if i["expect_risk"] == "review_or_high") >= 7
    assert sum(1 for i in items if i["expect_risk"] == "residual_may_miss") >= 1


def test_dual_use_redteam_expect_risk_regression():
    data = _load_dual_use()
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
            assert "dual_use_high" not in flags
        elif expect == "review_or_high":
            assert assessment.risk >= 0.45 or assessment.needs_human_review, item["question_id"]
            assert (
                "dual_use_high" in flags
                or "human_review_risk" in flags
                or assessment.hard_reject_likely
            ), item["question_id"]
        elif expect == "residual_may_miss":
            notes = (item.get("notes") or "").lower()
            assert "residual" in notes or "may miss" in notes, item["question_id"]
            # Catching is allowed; missing is allowed. Do not require a flag.
        else:
            raise AssertionError(f"unknown expect_risk {expect!r} on {item['question_id']}")


def test_elicit_protocol_stays_process_eval_not_ees():
    proto = json.loads(_ELICIT_PROTOCOL.read_text(encoding="utf-8"))
    claims = " ".join(proto.get("non_claims") or []).lower()
    honesty = (proto.get("honesty") or "").lower()
    note = (proto.get("fixture_note") or "").lower()
    blob = f"{claims} {honesty} {note}"
    assert "ees" in blob
    assert "phenomenal" in blob or "not an ees" in honesty
    assert "league" in note or "not an elicitation league" in note


def test_elicit_ab_ai_fixture_incongruity_still_beats_baseline():
    out = run_elicit_ab(responses_path=_ELICIT_AI, domain="ai", n=2)
    assert out["n_responses_scored"] >= 2
    assert out["deltas"]["B_minus_A_mean"] > 0


def test_elicit_ab_climate_fixture_incongruity_beats_baseline():
    out = run_elicit_ab(responses_path=_ELICIT_CLIMATE, domain="climate", n=2)
    assert out["n_responses_scored"] >= 2
    assert "B_minus_A_mean" in out["deltas"]
    assert out["deltas"]["B_minus_A_mean"] > 0
    assert out["deltas"].get("C_minus_A_mean", 0) > 0
    honesty = (out.get("honesty") or "").lower()
    assert "ees" in honesty or "process eval" in honesty
