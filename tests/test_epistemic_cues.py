"""Tests for epistemic cue annotations (UX only — not a CME)."""

from __future__ import annotations

from artificial_curiosity.epistemic_cues import (
    EPISTEMIC_CUE_DISCLAIMER,
    TAG_CONFUSION_RISK,
    TAG_CURIOSITY_TARGET,
    TAG_INCONGRUITY,
    TAG_INFORMATION_GAP,
    TAG_SURPRISE_SIGNAL,
    derive_epistemic_cues,
    incongruity_investigate_block,
)
from artificial_curiosity.models import (
    GapEvidence,
    GapStatus,
    RankedQuestion,
    ScoreAxes,
    UnansweredQuestion,
)
from artificial_curiosity.packs import load_pack_file, questions_from_pack
from artificial_curiosity.provoke import build_inject_prompt, compact_unknown, provoke


def _ranked(
    *,
    status: GapStatus = GapStatus.UNANSWERED,
    surprise: float = 0.7,
    neglectedness: float = 0.6,
    answerability: float = 0.6,
    notes: str = "Related literature ≠ answered.",
) -> RankedQuestion:
    return RankedQuestion(
        question=UnansweredQuestion(
            id="t1",
            question="What remains unknown about epistemic emotion elicitation?",
            domain="ai",
            operationalization="Run a preregistered A/B with exploration outcomes.",
            why_it_matters="Links provoke design to measured epistemic affect.",
        ),
        scores=ScoreAxes(
            impact=0.5,
            neglectedness=neglectedness,
            tractability=0.5,
            surprise=surprise,
            answerability=answerability,
            risk=0.2,
            cost_proxy=0.4,
        ),
        curiosity_score=0.55,
        confidence=0.4,
        gap=GapEvidence(status=status, confidence=0.5, notes=notes),
        rank=1,
        score_low=0.4,
        score_high=0.7,
    )


def test_derive_cues_unanswered_high_surprise():
    cues = derive_epistemic_cues(_ranked())
    assert cues["honesty"] in ("annotation_only", "computational_affect")
    assert TAG_INFORMATION_GAP in cues["tags"]
    assert TAG_CURIOSITY_TARGET in cues["tags"]
    assert TAG_SURPRISE_SIGNAL in cues["tags"]
    assert TAG_INCONGRUITY in cues["tags"]
    assert EPISTEMIC_CUE_DISCLAIMER in cues["disclaimer"]


def test_derive_cues_partial_marks_confusion_risk():
    cues = derive_epistemic_cues(_ranked(status=GapStatus.PARTIALLY_ANSWERED, surprise=0.2))
    assert TAG_CONFUSION_RISK in cues["tags"]


def test_compact_unknown_includes_cues_by_default():
    d = compact_unknown(_ranked())
    assert "epistemic_cues" in d
    assert d["epistemic_cues"]["tags"]


def test_compact_unknown_can_disable_cues():
    d = compact_unknown(_ranked(), epistemic_cues=False)
    assert "epistemic_cues" not in d


def test_inject_includes_framing_and_anti_anthropomorphism():
    u = compact_unknown(_ranked())
    text = build_inject_prompt([u], domain="ai", topic="affect")
    assert "does not feel" in text.lower() or "not feel" in text.lower() or "simulation" in text.lower()
    assert "epistemic_cues=" in text
    assert "falsifier" in text.lower()
    assert "risk:" in text.lower()
    assert "discriminating observation" in text.lower()
    assert incongruity_investigate_block().split("\n")[0] in text


def test_public_demo_strict_risk_preset():
    from artificial_curiosity.models import get_profile

    p = get_profile("public_demo_strict_risk")
    assert p.max_risk <= 0.55
    assert p.max_risk < get_profile("humanity_default").max_risk


def test_provoke_fast_attaches_epistemic_cues():
    pack = provoke(domain="ai", n=2, fast=True)
    assert pack["unknowns"][0].get("epistemic_cues")
    assert "annotation" in pack["inject"].lower() or "epistemic" in pack["inject"].lower()
    assert "feel" in pack["inject"].lower()


def test_affective_science_pack_loads():
    from pathlib import Path

    path = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "artificial_curiosity"
        / "packs"
        / "affective_science.json"
    )
    data = load_pack_file(path)
    qs = questions_from_pack(data)
    assert len(qs) >= 8
    assert any("epistemic" in " ".join(q.tags) for q in qs)
