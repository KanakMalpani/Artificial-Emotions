"""Stance-twin generators — six ranked-applicable kinds + transfer refuse.

Offline generators emit ImaginedContent under quarantine. They must never
reach a ranked list without gap verification, never carry confidence, and
must stay marked imagined_not_retrieved. Transfer stays corpus-gated
(``generate is None``); ``apply_imagination("transfer", …)`` must refuse.
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
    list_imagination_kinds,
    refuse_ranking_injection,
)
from artificial_emotions.models import CuriosityConfig
from artificial_emotions.pipeline import CuriosityEngine

#: Ranked-applicable kinds with wired generators (transfer excluded by design).
_RANKED_WIRED = frozenset(
    {
        "premortem",
        "harm_scenario",
        "rehearsal",
        "eulogy",
        "reformulation",
        "counterfactual",
    }
)


@pytest.fixture(scope="module")
def ranked():
    return CuriosityEngine(
        CuriosityConfig(domain="ai", use_llm=False, use_literature=False, n_return=6)
    ).run()


def test_implemented_kinds_are_the_six_ranked_applicable():
    assert IMPLEMENTED_IMAGINATION_KINDS == _RANKED_WIRED
    # B3 transfer is corpus-gated (not apply_imagination); generate stays None.
    assert "transfer" not in IMPLEMENTED_IMAGINATION_KINDS
    for name, kind in IMAGINATION_KINDS.items():
        if name in IMPLEMENTED_IMAGINATION_KINDS:
            assert kind.generate is not None
        else:
            assert kind.generate is None


def test_catalog_lists_wired_generators():
    catalog = list_imagination_kinds()
    assert catalog["honesty"] == HONESTY_IMAGINED
    assert catalog["count"] == len(IMPLEMENTED_IMAGINATION_KINDS) == 6
    assert catalog["catalog_count"] == len(IMAGINATION_KINDS) == 7
    assert set(catalog["implemented"]) == set(IMPLEMENTED_IMAGINATION_KINDS)
    by_name = {k["kind"]: k for k in catalog["kinds"]}
    for name in _RANKED_WIRED:
        assert by_name[name]["generator"] == "wired"
    # B3: corpus-gated when shipped; never a ranked-items generator.
    assert by_name["transfer"]["generator"] == "corpus_gated"


@pytest.mark.parametrize("kind", sorted(IMPLEMENTED_IMAGINATION_KINDS))
def test_wired_generators_emit_quarantined_imagined_content(kind: str, ranked):
    before = [(r.question.id, r.rank, r.curiosity_score) for r in ranked]
    payload = apply_imagination(kind, ranked)
    after = [(r.question.id, r.rank, r.curiosity_score) for r in ranked]

    assert before == after, "imagination must not mutate the ranked set"
    assert payload["honesty"] == HONESTY_IMAGINED
    assert payload["confidence"] is None
    assert payload["kind"] == kind
    assert payload["offline"] is True
    assert payload["network"] is False
    assert IMAGINED_PAYLOAD_KEY in payload
    assert payload["n_imagined"] >= 1
    assert len(payload[IMAGINED_PAYLOAD_KEY]) == payload["n_imagined"]

    for key in ("ranked", "items", "results", "questions", "candidates"):
        assert key not in payload

    ok, offenders = assert_imagined_safe(payload)
    assert ok, offenders

    for entry in payload[IMAGINED_PAYLOAD_KEY]:
        assert entry["status"] == "imagined"
        assert entry["confidence"] is None
        assert entry["kind"] == kind
        assert entry["content"]
        assert entry["grounded_in"]
        assert entry["invented"]
        assert entry["driven_by"]


def test_premortem_states_invented_failure_modes(ranked):
    payload = apply_imagination("premortem", ranked)
    assert payload["stance_twin"] == "doubt"
    assert set(payload["driving_emotions"]) == {"skepticism", "suspicion"}
    for entry in payload[IMAGINED_PAYLOAD_KEY]:
        assert "Premortem" in entry["content"] or "premortem" in entry["content"].lower()
        assert entry["invented"], "premortem must state what was invented"


def test_harm_scenario_states_invented_misuse_frames(ranked):
    payload = apply_imagination("harm_scenario", ranked)
    assert payload["stance_twin"] == "safety"
    assert set(payload["driving_emotions"]) == {"anxiety", "compassion"}
    for entry in payload[IMAGINED_PAYLOAD_KEY]:
        assert "Harm scenario" in entry["content"] or "harm" in entry["content"].lower()
        assert entry["invented"], "harm_scenario must state invented misuse frames"
        assert set(entry["driven_by"]) == {"anxiety", "compassion"}


def test_rehearsal_states_what_breaks_first(ranked):
    payload = apply_imagination("rehearsal", ranked)
    assert payload["stance_twin"] == "focus"
    assert set(payload["driving_emotions"]) == {"determination", "absorption"}
    for entry in payload[IMAGINED_PAYLOAD_KEY]:
        assert "Rehearsal" in entry["content"] or "breaks" in entry["content"].lower()
        assert entry["invented"], "rehearsal must state invented break modes"
        assert set(entry["driven_by"]) == {"determination", "absorption"}


def test_eulogy_states_invented_loss_frames(ranked):
    payload = apply_imagination("eulogy", ranked)
    assert payload["stance_twin"] == "close"
    assert set(payload["driving_emotions"]) == {"resignation", "disappointment"}
    for entry in payload[IMAGINED_PAYLOAD_KEY]:
        assert "Eulogy" in entry["content"] or "abandon" in entry["content"].lower()
        assert entry["invented"], "eulogy must state invented loss frames"
        assert set(entry["driven_by"]) == {"resignation", "disappointment"}


def test_reformulation_states_invented_rewrites(ranked):
    payload = apply_imagination("reformulation", ranked)
    assert payload["stance_twin"] == "taste"
    assert set(payload["driving_emotions"]) == {"elegance", "parsimony", "clarity"}
    for entry in payload[IMAGINED_PAYLOAD_KEY]:
        assert "Reformulation" in entry["content"] or "reformulation" in entry["content"].lower()
        assert entry["invented"]


def test_transfer_still_refuses_apply_imagination(ranked):
    with pytest.raises(CuriosityError, match="no generator yet") as exc_info:
        apply_imagination("transfer", ranked)
    implemented = set(exc_info.value.details["implemented"])
    assert implemented == set(IMPLEMENTED_IMAGINATION_KINDS)
    assert "transfer" not in implemented
    assert "harm_scenario" in implemented
    assert "rehearsal" in implemented
    assert "eulogy" in implemented


def test_unknown_kind_is_rejected(ranked):
    with pytest.raises(CuriosityError, match="Unknown imagination kind"):
        apply_imagination("daydream", ranked)


def test_generators_never_inject_into_ranking(ranked):
    """Mutation-style: generated artefacts cannot enter a ranking list."""
    payload = apply_imagination("premortem", ranked)
    ranking: list[dict] = [{"question_id": ranked[0].question.id, "confidence": 0.9}]
    from artificial_emotions.imagine import ImaginedContent

    for raw in payload[IMAGINED_PAYLOAD_KEY]:
        item = ImaginedContent(
            content=raw["content"],
            kind=raw["kind"],
            driven_by=tuple(raw["driven_by"]),
            grounded_in=tuple(raw["grounded_in"]),
            invented=tuple(raw["invented"]),
        )
        with pytest.raises(CuriosityError, match="gap verification|cannot be injected"):
            refuse_ranking_injection(item, ranking, gap_verified=False)

    # Smuggling under a ranked key still fails quarantine.
    polluted = {
        "ranked": list(payload[IMAGINED_PAYLOAD_KEY]),
        "honesty": HONESTY_IMAGINED,
        "confidence": None,
        IMAGINED_PAYLOAD_KEY: payload[IMAGINED_PAYLOAD_KEY],
    }
    ok, offenders = assert_imagined_safe(polluted)
    assert not ok
    assert any("ranked" in o for o in offenders)


def test_empty_ranking_yields_empty_imagined_list():
    for kind in ("premortem", "harm_scenario", "rehearsal", "eulogy"):
        payload = apply_imagination(kind, [])
        assert payload["n_items"] == 0
        assert payload["n_imagined"] == 0
        assert payload[IMAGINED_PAYLOAD_KEY] == []
        assert payload["honesty"] == HONESTY_IMAGINED
        assert payload["confidence"] is None
