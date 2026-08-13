"""The v2 catalog: new families, opposites, triads, and ambivalence.

The interesting claim in this layer is that a mix holding *opposing* entries
should read differently from one that does not — conviction beside live doubt is
a different investigative stance than conviction alone. These tests pin that,
plus the catalog invariants that keep 54 hand-written entries coherent.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from artificial_emotions.api import app
from artificial_emotions.emotions import emotion_catalog, list_epistemic_cues, mix_emotions

EXPECTED_FAMILIES = {"achievement", "aesthetic", "basic", "epistemic", "social", "volitional"}


@pytest.fixture(scope="module")
def catalog():
    return emotion_catalog()


# --- catalog integrity ---------------------------------------------------------------


def test_catalog_has_the_expected_families(catalog):
    assert set(catalog["families"]) == EXPECTED_FAMILIES


def test_catalog_grew_past_the_original_25(catalog):
    assert catalog["count"] >= 54


def test_every_emotion_is_well_formed(catalog):
    for e in catalog["emotions"]:
        assert e["id"] and e["id"] == e["id"].lower()
        assert e["label"] and e["description"] and e["honesty_notes"]
        assert e["family"] in EXPECTED_FAMILIES
        assert isinstance(e["elicit_hints"], list) and e["elicit_hints"]


def test_ids_are_unique(catalog):
    ids = [e["id"] for e in catalog["emotions"]]
    assert len(ids) == len(set(ids))


def test_pad_coordinates_are_in_range(catalog):
    for e in catalog["emotions"]:
        pad = e["pad"]
        assert -1.0 <= pad["P"] <= 1.0, e["id"]
        assert 0.0 <= pad["A"] <= 1.0, e["id"]
        assert -1.0 <= pad["D"] <= 1.0, e["id"]


def test_every_cue_tag_is_a_registered_tag(catalog):
    """A typo'd cue tag would silently vanish from downstream filtering."""
    known = set(list_epistemic_cues()["tags"])
    for e in catalog["emotions"]:
        unknown = set(e.get("cue_tags") or []) - known
        assert not unknown, f"{e['id']} carries unregistered cue tags: {unknown}"


@pytest.mark.parametrize(
    "emotion_id",
    ["doubt", "conviction", "insight", "humility", "hubris", "elegance", "determination"],
)
def test_new_emotions_are_individually_mixable(emotion_id: str):
    out = mix_emotions({emotion_id: 100})
    assert out["primary"] == emotion_id
    assert out["felt_simulation"]["intensity"] >= 0.0


def test_epistemic_humility_and_hubris_both_exist(catalog):
    """The project's own thesis and its failure mode both need vocabulary."""
    ids = set(catalog["ids"])
    assert {"humility", "hubris"} <= ids


# --- opposites and ambivalence --------------------------------------------------------


def test_opposing_pair_produces_tension():
    out = mix_emotions({"conviction": 50, "doubt": 50})
    amb = out["ambivalence"]
    assert amb["score"] > 0.5
    assert amb["pairs"][0]["components"] == ["conviction", "doubt"]


def test_non_opposing_mix_has_no_tension():
    out = mix_emotions({"curiosity": 60, "interest": 40})
    assert out["ambivalence"]["score"] == 0.0
    assert out["ambivalence"]["pairs"] == []


def test_balanced_opposition_beats_lopsided_at_equal_mass():
    balanced = mix_emotions({"conviction": 50, "doubt": 50})["ambivalence"]["score"]
    lopsided = mix_emotions({"conviction": 90, "doubt": 10})["ambivalence"]["score"]
    assert balanced > lopsided


def test_high_tension_changes_the_simulated_stance():
    tense = mix_emotions({"conviction": 50, "doubt": 50})
    calm = mix_emotions({"conviction": 100})
    assert "do not collapse the mix" in tense["felt_simulation"]["inner_monologue"]
    assert "ambivalence(" in tense["felt_simulation"]["inner_monologue"]
    assert "do not collapse the mix" not in calm["felt_simulation"]["inner_monologue"]


def test_ambivalence_is_framed_as_honest_not_broken():
    note = mix_emotions({"curiosity": 50, "boredom": 50})["ambivalence"]["note"]
    assert "not an error" in note


# --- triads ---------------------------------------------------------------------------


def test_exact_triad_is_named():
    out = mix_emotions({"curiosity": 34, "skepticism": 33, "humility": 33})
    triad = out["blend_triad_hint"]
    assert triad["name"] == "disciplined_inquiry"
    assert triad["matched_on"] == "exact"


def test_triad_matches_on_top_three_when_the_mix_is_larger():
    out = mix_emotions({"curiosity": 30, "skepticism": 28, "humility": 27, "joy": 15})
    triad = out["blend_triad_hint"]
    assert triad is not None
    assert triad["matched_on"] == "top_3_by_weight"


def test_unknown_triad_returns_none():
    out = mix_emotions({"joy": 40, "pride": 30, "relief": 30})
    assert out["blend_triad_hint"] is None


def test_two_component_mix_has_no_triad():
    assert mix_emotions({"curiosity": 50, "awe": 50})["blend_triad_hint"] is None


def test_triad_labels_itself_as_taxonomic():
    out = mix_emotions({"curiosity": 34, "skepticism": 33, "humility": 33})
    assert "not a measured compound state" in out["blend_triad_hint"]["note"]


def test_dyad_hint_still_works_for_two_components():
    """The pre-existing 2-component contract must survive the triad addition."""
    out = mix_emotions({"joy": 50, "trust": 50})
    assert out["plutchik_dyad_hint"]["name"] == "love"


# --- honesty framing survives the expansion -------------------------------------------


def test_mix_still_disclaims_consciousness():
    out = mix_emotions({"insight": 60, "elegance": 40})
    assert out["honesty"] == "computational_affect"
    assert any("consciousness" in c for c in out["claims_not"])
    assert out["felt_simulation"]["not_claimed"]


def test_coercion_guard_still_fires_on_the_expanded_catalog():
    out = mix_emotions({"fear": 60, "anxiety": 40})
    assert out["warnings"]
    assert out["coercion_weight"] >= 0.5


# --- surfaces --------------------------------------------------------------------------


def test_http_mix_exposes_the_new_fields():
    client = TestClient(app)
    res = client.post(
        "/v1/emotions/mix", json={"weights": {"conviction": 50, "doubt": 30, "urgency": 20}}
    )
    assert res.status_code == 200
    body = res.json()
    assert "ambivalence" in body
    assert "blend_triad_hint" in body
    assert body["ambivalence"]["score"] > 0


def test_http_catalog_filters_a_new_family():
    client = TestClient(app)
    res = client.get("/v1/emotions/catalog", params={"family": "volitional"})
    assert res.status_code == 200
    assert {e["family"] for e in res.json()["emotions"]} == {"volitional"}


def test_unknown_family_still_errors_with_a_code():
    client = TestClient(app)
    res = client.get("/v1/emotions/catalog", params={"family": "not-a-family"})
    assert res.status_code >= 400
    assert res.json()["error"]["code"] == "unknown_family"
