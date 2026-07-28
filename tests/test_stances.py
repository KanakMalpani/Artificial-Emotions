"""Stances must be genuinely different questions, not relabelled curiosity.

A stance is the only place a non-curiosity emotion is the *point* rather than a
modifier on search behaviour. That makes two failure modes worth guarding:

1. A stance that agrees with the curiosity ranking on everything is decoration —
   it added a name and no information.
2. A stance that quietly reorders the ranked set would make the ValueProfile a
   lie, since the user was told the ordering came from their stated values.
"""

from __future__ import annotations

import pytest

from artificial_emotions.errors import CuriosityError
from artificial_emotions.models import CuriosityConfig
from artificial_emotions.pipeline import CuriosityEngine
from artificial_emotions.stances import STANCES, apply_stance, list_stances


@pytest.fixture(scope="module")
def ranked():
    return CuriosityEngine(
        CuriosityConfig(domain="ai", use_llm=False, use_literature=False, n_return=6)
    ).run()


def test_every_stance_produces_a_view(ranked):
    for name in STANCES:
        payload = apply_stance(name, ranked)
        assert payload["stance"] == name
        assert payload["asks"].endswith("?"), f"{name} does not ask a question"
        assert payload["driving_emotions"], f"{name} is driven by nothing"
        assert payload["view"], f"{name} returned an empty view"


def test_stances_never_reorder_the_ranking(ranked):
    """The honesty claim printed on every payload has to actually hold."""
    before = [(r.question.id, r.rank, r.curiosity_score) for r in ranked]
    for name in STANCES:
        apply_stance(name, ranked)
    after = [(r.question.id, r.rank, r.curiosity_score) for r in ranked]
    assert before == after, "a stance mutated the ranked set it was given"


def test_every_stance_says_what_it_is_not(ranked):
    for name in STANCES:
        payload = apply_stance(name, ranked)
        assert payload["honesty"] == "stance_view_only"
        joined = " ".join(payload["claims_not"]).lower()
        assert "re-ranking" in joined, f"{name} does not disclaim re-ranking"


def test_stances_disagree_with_each_other(ranked):
    """If every stance surfaced the same item first, they would be one stance."""
    heads = {}
    for name in STANCES:
        view = apply_stance(name, ranked)["view"]
        for value in view.values():
            if isinstance(value, list) and value and isinstance(value[0], dict):
                head = value[0].get("question_id") or value[0].get("term")
                if head:
                    heads[name] = head
                    break
    assert len(heads) >= 5, f"only {len(heads)} stances expose an ordered view: {sorted(heads)}"
    assert len(set(heads.values())) > 1, (
        f"every stance leads with the same item ({heads}) — they are not distinct questions"
    )


def test_wonder_can_disagree_with_the_value_profile(ranked):
    """Wonder exists precisely to escape the ValueProfile; it must be able to."""
    view = apply_stance("wonder", ranked)["view"]
    gaps = [row["rank_gap"] for row in view["by_novelty_pull"]]
    assert all(g is not None for g in gaps)
    assert any(g != 0 for g in gaps), (
        "wonder reproduced the curiosity ranking exactly — it is adding nothing"
    )


def test_unknown_stance_is_rejected_with_the_known_list(ranked):
    with pytest.raises(CuriosityError) as excinfo:
        apply_stance("smugness", ranked)
    assert "smugness" in str(excinfo.value)
    assert set(excinfo.value.details["known"]) == set(STANCES)


def test_catalog_lists_every_stance():
    catalog = list_stances()
    assert {s["stance"] for s in catalog["stances"]} == set(STANCES)
    for entry in catalog["stances"]:
        assert entry["use_when"], f"{entry['stance']} does not say when to use it"


def test_taste_actually_discriminates_rather_than_rubber_stamping(ranked):
    """A critic that approves everything is not a critic."""
    bad = ranked[0].model_copy(
        update={
            "question": ranked[0].question.model_copy(
                update={
                    "id": "bad-01",
                    "question": (
                        "Is it better and faster and more effective to do this? "
                        "And what about that?"
                    ),
                    "operationalization": "TBD.",
                }
            )
        }
    )
    view = apply_stance("taste", [*ranked, bad])["view"]
    worst = view["worst_formed_first"][0]
    assert worst["question_id"] == "bad-01", "the malformed question did not sort worst"
    assert worst["problems"], "the malformed question drew no critique"
    assert view["n_with_form_problems"] >= 1
    assert worst["form_score"] < 1.0
