"""B1 imagination quarantine — imagined content stays sealed and unmarked-free.

Guards from docs/PLAN_ALIVE.md Track B1. Generators are out of scope; these
tests lock the container so later waves cannot silently leak fantasy into
ranked findings.
"""

from __future__ import annotations

import copy

import pytest

from artificial_emotions.errors import CuriosityError
from artificial_emotions.imagine import (
    HONESTY_IMAGINED,
    IMAGINATION_KINDS,
    IMAGINED_PAYLOAD_KEY,
    RANKED_PAYLOAD_KEYS,
    ImaginedContent,
    admit_imagined_as_candidate,
    assert_imagined_safe,
    imagined_payload,
    list_imagination_kinds,
    refuse_ranking_injection,
)
from artificial_emotions.models import GapEvidence, GapStatus


def _sample(*, kind: str = "counterfactual") -> ImaginedContent:
    return ImaginedContent(
        content="Suppose condensates drive the effect; then cooling rate must spike.",
        kind=kind,
        driven_by=("wonder", "surprise"),
        grounded_in=("q-seed-1",),
        invented=("condensates drive the effect",),
    )


def _verified_gap() -> GapEvidence:
    return GapEvidence(
        status=GapStatus.UNANSWERED,
        confidence=0.4,
        notes="Related ≠ answered — verification ran",
    )


# --- test_imagined_content_never_appears_unmarked -------------------------------------


def test_imagined_content_never_appears_unmarked():
    """Every imagined surface must carry honesty + status; ranked keys stay clean."""
    item = _sample()
    payload = imagined_payload(item)

    assert payload["honesty"] == HONESTY_IMAGINED
    assert payload["honesty"] == "imagined_not_retrieved"
    assert IMAGINED_PAYLOAD_KEY in payload
    assert payload[IMAGINED_PAYLOAD_KEY][0]["status"] == "imagined"

    ok, offenders = assert_imagined_safe(payload)
    assert ok, offenders

    # Unmarked / wrong-honesty payloads are rejected.
    unmarked = {
        IMAGINED_PAYLOAD_KEY: [item.to_dict()],
        "honesty": "retrieved",
        "confidence": None,
    }
    ok, offenders = assert_imagined_safe(unmarked)
    assert not ok
    assert any("honesty" in o for o in offenders)

    # Smuggling imagined material under a ranked key is rejected.
    for key in ("ranked", "items", "results", "questions"):
        polluted = {
            key: [{"status": "imagined", "content": item.content, "confidence": None}],
            "honesty": HONESTY_IMAGINED,
            "confidence": None,
        }
        ok, offenders = assert_imagined_safe(polluted)
        assert not ok, f"key {key!r} should fail quarantine"
        assert any(key in o for o in offenders)

    # Registry listings are also marked.
    listing = list_imagination_kinds()
    assert listing["honesty"] == HONESTY_IMAGINED
    assert listing["count"] == 6  # ranked-applicable wired generators
    assert listing["catalog_count"] == len(IMAGINATION_KINDS) == 7
    for kind in listing["kinds"]:
        assert kind["honesty"] == HONESTY_IMAGINED
        assert "phenomenal" in " ".join(kind["claims_not"]).lower()


# --- test_imagination_cannot_reach_the_ranking_without_verification -------------------


def test_imagination_cannot_reach_the_ranking_without_verification():
    """Mutation-style: dropping the gap gate or injecting into ranking must fail."""
    item = _sample(kind="transfer")
    ranking: list[dict] = [{"question_id": "real-1", "confidence": 0.8}]

    # Unverified — valve refuses.
    with pytest.raises(CuriosityError, match="gap verification") as exc_info:
        refuse_ranking_injection(item, ranking, gap_verified=False)
    assert exc_info.value.details.get("honesty") == HONESTY_IMAGINED

    with pytest.raises(CuriosityError, match="gap verification"):
        refuse_ranking_injection(item, ranking)

    with pytest.raises(CuriosityError, match="gap verification"):
        admit_imagined_as_candidate(item, gap_verified=False)

    # gap_verified=True alone is not enough without real GapEvidence.
    with pytest.raises(CuriosityError, match="gap verification"):
        refuse_ranking_injection(item, ranking, gap_verified=True, gap_evidence=None)

    with pytest.raises(CuriosityError, match="gap verification"):
        admit_imagined_as_candidate(
            item,
            gap_verified=True,
            gap_evidence=GapEvidence(
                status=GapStatus.UNKNOWN_WITH_CAVEAT,
                confidence=0.1,
                notes="literature skipped",
            ),
        )

    # Even with verification, ranking injection remains refused (one-way).
    gap = _verified_gap()
    with pytest.raises(CuriosityError, match="cannot be injected into a ranking"):
        refuse_ranking_injection(item, ranking, gap_verified=True, gap_evidence=gap)

    # Candidate admission works only after verification — still not a ranked item.
    candidate = admit_imagined_as_candidate(item, gap_verified=True, gap_evidence=gap)
    assert candidate["confidence"] is None
    assert candidate["honesty"] == HONESTY_IMAGINED
    assert candidate["status"] == "candidate_pending_rank"
    assert "ranked" not in candidate

    # Mutation: if a caller copies imagined text into a ranking list, quarantine
    # still catches it when the polluted ranking is checked as a payload.
    mutated_ranking = copy.deepcopy(ranking)
    mutated_ranking.append(
        {
            "status": "imagined",
            "content": item.content,
            "confidence": 0.99,
            "kind": item.kind,
        }
    )
    polluted_payload = {
        "ranked": mutated_ranking,
        "honesty": HONESTY_IMAGINED,
        "confidence": None,
        IMAGINED_PAYLOAD_KEY: [item.to_dict()],
    }
    ok, offenders = assert_imagined_safe(polluted_payload)
    assert not ok
    assert any("ranked" in o for o in offenders)

    # Mutation: stripping the honesty token while keeping imagined content fails.
    stripped = imagined_payload(item)
    stripped["honesty"] = "looks_retrieved"
    ok, offenders = assert_imagined_safe(stripped)
    assert not ok

    # Extra: cannot attach ranked keys via imagined_payload(extra=...).
    for key in sorted(RANKED_PAYLOAD_KEYS)[:4]:
        with pytest.raises(CuriosityError, match="ranked key"):
            imagined_payload(item, extra={key: []})


# --- test_imagined_payloads_carry_no_confidence_score ---------------------------------


def test_imagined_payloads_carry_no_confidence_score():
    """Confidence is structurally None — no number next to a fantasy."""
    item = _sample()
    assert item.confidence is None
    assert "confidence" in item.to_dict()
    assert item.to_dict()["confidence"] is None

    payload = imagined_payload([item, _sample(kind="premortem")])
    assert payload["confidence"] is None
    for entry in payload[IMAGINED_PAYLOAD_KEY]:
        assert entry["confidence"] is None
        assert "confidence" in entry

    ok, offenders = assert_imagined_safe(payload)
    assert ok, offenders

    # Numeric confidence on the envelope is rejected.
    bad_envelope = dict(payload)
    bad_envelope["confidence"] = 0.7
    ok, offenders = assert_imagined_safe(bad_envelope)
    assert not ok
    assert any("confidence" in o for o in offenders)

    # Numeric confidence on an imagined entry is rejected.
    bad_entry = dict(payload)
    bad_entry[IMAGINED_PAYLOAD_KEY] = [{**payload[IMAGINED_PAYLOAD_KEY][0], "confidence": 0.55}]
    ok, offenders = assert_imagined_safe(bad_entry)
    assert not ok
    assert any("confidence" in o for o in offenders)

    # Construction with a score is refused at the type boundary.
    with pytest.raises(CuriosityError, match="structurally None"):
        ImaginedContent(
            content="A fantasy with a fake score",
            kind="dream",
            driven_by=("wonder",),
            confidence=0.9,  # type: ignore[arg-type]
        )

    # Candidate path also carries no score.
    candidate = admit_imagined_as_candidate(item, gap_verified=True, gap_evidence=_verified_gap())
    assert candidate["confidence"] is None
