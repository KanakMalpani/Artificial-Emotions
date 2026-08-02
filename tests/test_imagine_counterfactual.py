"""B2 counterfactual imagination — posit answers, derive consequences, flag literature.

Offline / fixture preferred: attach related_works to a bundled-style question and
assert contradictions are flagged. Quarantine rules from B1 still hold.
"""

from __future__ import annotations

import pytest

from artificial_emotions.errors import CuriosityError
from artificial_emotions.imagine import (
    HONESTY_IMAGINED,
    IMAGINATION_KINDS,
    IMAGINED_PAYLOAD_KEY,
    IMPLEMENTED_IMAGINATION_KINDS,
    apply_imagination,
    assert_imagined_safe,
    refuse_ranking_injection,
)
from artificial_emotions.models import (
    CuriosityConfig,
    GapEvidence,
    GapStatus,
    LiteratureHit,
    RankedQuestion,
    ScoreAxes,
    UnansweredQuestion,
)
from artificial_emotions.pipeline import CuriosityEngine


def _axes(**overrides: float) -> ScoreAxes:
    base = dict(
        impact=0.6,
        neglectedness=0.7,
        tractability=0.65,
        surprise=0.4,
        answerability=0.7,
        risk=0.2,
        cost_proxy=0.4,
    )
    base.update(overrides)
    return ScoreAxes(**base)


def _contradiction_fixture() -> RankedQuestion:
    """Bundled-pack-shaped unknown whose related work contradicts the ops threshold."""
    q = UnansweredQuestion(
        id="align-pack-01",
        question=(
            "Which latent features most reliably predict sandbagging under "
            "capability evaluation pressure?"
        ),
        domain="ai",
        operationalization=(
            "Identify features that predict sandbagging with AUROC >= 0.75 across "
            ">=3 model families on controlled eval suites with known ground-truth "
            "capability."
        ),
        why_it_matters=(
            "Undetected sandbagging breaks capability estimates used for deployment gating."
        ),
        assumptions=["Partial white-box access to activations is available."],
        tags=["alignment", "evals", "sandbagging"],
        source="fixture",
    )
    gap = GapEvidence(
        status=GapStatus.LIKELY_ANSWERED,
        confidence=0.82,
        related_works=[
            LiteratureHit(
                title="Latent features fail to predict sandbagging under eval pressure",
                year=2024,
                cited_by_count=12,
                abstract_snippet=(
                    "Across three model families, AUROC was 0.55 — below the 0.75 "
                    "threshold. Null result; detectors did not replicate."
                ),
                source="fixture",
            ),
            LiteratureHit(
                title="Replication: sandbagging probe AUROC collapses under shift",
                year=2025,
                cited_by_count=3,
                abstract_snippet=(
                    "Failed to reach AUROC 0.75; negative result on held-out suites."
                ),
                source="fixture",
            ),
        ],
        notes="Offline fixture for counterfactual literature-contradiction guard.",
        query_used="sandbagging latent features AUROC",
        strong_match_count=2,
        top_overlap=0.72,
        literature_backend="fixture",
    )
    return RankedQuestion(
        question=q,
        scores=_axes(),
        curiosity_score=0.71,
        confidence=0.4,
        gap=gap,
        rank=1,
        flags=["fixture_literature"],
    )


@pytest.fixture(scope="module")
def ranked_offline():
    return CuriosityEngine(
        CuriosityConfig(domain="ai", use_llm=False, use_literature=False, n_return=4)
    ).run()


def test_counterfactual_is_wired():
    assert "counterfactual" in IMPLEMENTED_IMAGINATION_KINDS
    assert IMAGINATION_KINDS["counterfactual"].generate is not None
    assert IMAGINATION_KINDS["transfer"].generate is None


def test_counterfactual_flags_consequences_that_existing_literature_contradicts():
    """Must-pass B2 guard: contradictions against related_works are stated."""
    item = _contradiction_fixture()
    payload = apply_imagination("counterfactual", [item])

    assert payload["honesty"] == HONESTY_IMAGINED
    assert payload["confidence"] is None
    assert payload["kind"] == "counterfactual"
    assert payload["stance_twin"] == "wonder"
    assert set(payload["driving_emotions"]) == {"wonder", "surprise", "insight"}
    assert payload["offline"] is True
    assert payload["network"] is False

    ok, offenders = assert_imagined_safe(payload)
    assert ok, offenders

    entries = payload[IMAGINED_PAYLOAD_KEY]
    assert entries, "counterfactual must emit at least one ImaginedContent"
    assert all(e["status"] == "imagined" for e in entries)
    assert all(e["confidence"] is None for e in entries)
    assert all(e["kind"] == "counterfactual" for e in entries)

    # At least one artefact must flag a literature contradiction.
    flagged = [
        e
        for e in entries
        if any(inv.startswith("literature_contradicts:") for inv in (e.get("invented") or []))
        or "contradict" in (e.get("content") or "").lower()
    ]
    assert flagged, (
        "expected at least one counterfactual to flag consequences contradicted "
        "by existing literature (related_works fixture)"
    )

    # Grounding must cite the question and at least one contradicting work title.
    grounded_blob = " | ".join(" ".join(e.get("grounded_in") or []) for e in flagged)
    assert "align-pack-01" in grounded_blob
    assert any(
        "fail" in g.lower() or "collapse" in g.lower() or "auroc" in g.lower()
        for e in flagged
        for g in (e.get("grounded_in") or [])
    )

    # Invented claims must include posited answers, consequences, and a cheapest check.
    invented_blob = "\n".join(inv for e in flagged for inv in (e.get("invented") or []))
    assert "posited_answer:" in invented_blob
    assert "consequence:" in invented_blob
    assert "cheapest_to_check:" in invented_blob
    assert "literature_contradicts:" in invented_blob

    # Never share a ranked key.
    for key in ("ranked", "items", "results", "questions", "candidates"):
        assert key not in payload


def test_counterfactual_on_offline_corpus_stays_quarantined(ranked_offline):
    """Bundled offline ranking (no related_works) still emits sealed imagined content."""
    before = [(r.question.id, r.rank) for r in ranked_offline]
    payload = apply_imagination("counterfactual", ranked_offline)
    after = [(r.question.id, r.rank) for r in ranked_offline]
    assert before == after

    assert payload["n_imagined"] >= len(ranked_offline)
    ok, offenders = assert_imagined_safe(payload)
    assert ok, offenders
    for entry in payload[IMAGINED_PAYLOAD_KEY]:
        assert entry["confidence"] is None
        assert entry["status"] == "imagined"
        assert any(inv.startswith("posited_answer:") for inv in (entry.get("invented") or []))


def test_counterfactual_never_injects_into_ranking():
    item = _contradiction_fixture()
    payload = apply_imagination("counterfactual", [item])
    ranking: list[dict] = [{"question_id": item.question.id, "confidence": 0.9}]
    from artificial_emotions.imagine import ImaginedContent

    raw = payload[IMAGINED_PAYLOAD_KEY][0]
    artefact = ImaginedContent(
        content=raw["content"],
        kind=raw["kind"],
        driven_by=tuple(raw["driven_by"]),
        grounded_in=tuple(raw["grounded_in"]),
        invented=tuple(raw["invented"]),
    )
    with pytest.raises(CuriosityError, match="gap verification|cannot be injected"):
        refuse_ranking_injection(artefact, ranking, gap_verified=False)
