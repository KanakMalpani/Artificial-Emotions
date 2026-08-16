"""Retrospective validation — the repo's one falsifiable usefulness claim.

The headline test is `test_predicts_the_raynaud_link_from_pre_1986_literature`:
given only literature published before 1986, the method must propose fish oil →
Raynaud's, and that link must then be found in the held-out post-1986 slice.
That is the historical case Swanson actually got right, reproduced as a test.

`test_lift_falls_to_chance_when_the_future_confirms_everything` is the guard
that keeps the metric honest — if a dense future makes every pair "confirm",
lift must collapse toward 1.0 rather than flattering the method.
"""

from __future__ import annotations

import json

import pytest

from artificial_emotions.resources import find_data_file
from artificial_emotions.validate import (
    ValidationReport,
    concept_pool,
    split_by_year,
    validate_retrospective,
)

CORPUS = [
    # pre-cutoff: the two halves, never joined
    {
        "year": 1979,
        "title": "Fish oil and blood viscosity",
        "concepts": ["Fish oil", "Blood viscosity"],
    },
    {
        "year": 1976,
        "title": "Blood viscosity in Raynaud's",
        "concepts": ["Blood viscosity", "Raynaud disease"],
    },
    {"year": 1980, "title": "Vasospasm and cold", "concepts": ["Vasospasm", "Raynaud disease"]},
    {
        "year": 1981,
        "title": "Soil nitrogen in grassland",
        "concepts": ["Soil nitrogen", "Grassland ecology"],
    },
    {"year": 1983, "title": "Grazing and grassland", "concepts": ["Grassland ecology", "Grazing"]},
    # post-cutoff: the link gets made
    {
        "year": 1989,
        "title": "Fish oil in Raynaud's: a trial",
        "concepts": ["Fish oil", "Raynaud disease"],
    },
    {
        "year": 1993,
        "title": "Soil carbon under grazing",
        "concepts": ["Grassland ecology", "Soil carbon"],
    },
]


# --- the claim -------------------------------------------------------------------------


def test_predicts_the_raynaud_link_from_pre_1986_literature():
    report = validate_retrospective(CORPUS, seeds=["Fish oil"], cutoff_year=1986)
    confirmed = [(p["b"], p["c"]) for p in report.proposals if p["confirmed"]]
    assert ("Blood viscosity", "Raynaud disease") in confirmed


def test_the_future_slice_is_genuinely_hidden_from_discovery():
    """If the future leaked in, the proposal would not be a prediction."""
    past, future = split_by_year(CORPUS, 1986)
    assert all(int(d["year"]) < 1986 for d in past)
    assert all(int(d["year"]) >= 1986 for d in future)
    # The A–C pair must not co-occur anywhere in the past slice.
    from artificial_emotions.discover import LocalCorpusClient

    assert LocalCorpusClient(documents=past).cooccurrence_count("Fish oil", "Raynaud disease") == 0


def test_report_carries_a_baseline_and_lift():
    report = validate_retrospective(CORPUS, seeds=["Fish oil"], cutoff_year=1986)
    payload = report.to_dict()
    assert payload["baseline_hit_rate"] is not None
    assert payload["hit_rate"] is not None
    assert "baseline_note" in payload


def test_lift_falls_to_chance_when_the_future_confirms_everything():
    """A dense future must not flatter the method — that is the vanity trap."""
    dense_future = CORPUS + [
        {
            "year": 1990,
            "title": "Everything together",
            "concepts": [
                "Fish oil",
                "Raynaud disease",
                "Blood viscosity",
                "Vasospasm",
                "Soil nitrogen",
                "Grassland ecology",
                "Grazing",
            ],
        },
    ]
    report = validate_retrospective(dense_future, seeds=["Fish oil"], cutoff_year=1986)
    assert report.baseline_hit_rate == pytest.approx(1.0)
    assert report.lift == pytest.approx(1.0, abs=0.01)


def test_no_confirmations_yields_a_zero_hit_rate():
    isolated = [
        {"year": 1979, "title": "A and B", "concepts": ["Fish oil", "Blood viscosity"]},
        {"year": 1980, "title": "B and C", "concepts": ["Blood viscosity", "Raynaud disease"]},
        {"year": 1995, "title": "Unrelated", "concepts": ["Sediment transport"]},
    ]
    report = validate_retrospective(isolated, seeds=["Fish oil"], cutoff_year=1986)
    assert report.n_proposals >= 1
    assert report.hit_rate == 0.0


# --- splitting -------------------------------------------------------------------------


def test_documents_without_a_year_are_dropped_not_guessed():
    past, future = split_by_year([{"title": "no year", "concepts": ["X"]}], 1986)
    assert past == [] and future == []


def test_unparseable_years_are_dropped():
    past, future = split_by_year([{"year": "circa 1980", "concepts": ["X"]}], 1986)
    assert past == [] and future == []


def test_cutoff_year_belongs_to_the_future():
    past, future = split_by_year([{"year": 1986, "concepts": ["X"]}], 1986)
    assert not past and len(future) == 1


# --- report contract -------------------------------------------------------------------


def test_empty_report_has_no_rates_rather_than_zero():
    report = ValidationReport(cutoff_year=2000, n_past_docs=0, n_future_docs=0)
    assert report.hit_rate is None
    assert report.baseline_hit_rate is None
    assert report.lift is None


def test_lift_is_none_when_the_baseline_never_hits():
    report = ValidationReport(cutoff_year=2000, n_past_docs=1, n_future_docs=1)
    report.proposals = [{"confirmed": True, "gap_score": 0.5, "a": "a", "c": "c"}]
    report.baseline = [{"confirmed": False}]
    assert report.baseline_hit_rate == 0.0
    assert report.lift is None  # undefined, not infinity


def test_report_disclaims_being_a_benchmark():
    payload = validate_retrospective(CORPUS, seeds=["Fish oil"], cutoff_year=1986).to_dict()
    joined = " ".join(payload["claims_not"]).lower()
    assert "benchmark" in joined
    assert "significance" in joined
    assert payload["honesty"] == "retrospective_small_n"


def test_report_is_json_serialisable():
    json.dumps(validate_retrospective(CORPUS, seeds=["Fish oil"], cutoff_year=1986).to_dict())


def test_summary_reads_as_one_line():
    line = validate_retrospective(CORPUS, seeds=["Fish oil"], cutoff_year=1986).summary()
    assert "cutoff 1986" in line
    assert "hit_rate" in line


def test_validation_is_deterministic_given_a_seed():
    a = validate_retrospective(CORPUS, seeds=["Fish oil"], cutoff_year=1986, seed=7).to_dict()
    b = validate_retrospective(CORPUS, seeds=["Fish oil"], cutoff_year=1986, seed=7).to_dict()
    assert a == b


def test_baseline_can_be_switched_off():
    report = validate_retrospective(
        CORPUS, seeds=["Fish oil"], cutoff_year=1986, baseline_samples_per_seed=0
    )
    assert report.baseline == []
    assert report.baseline_hit_rate is None
    assert report.lift is None


# --- shipped corpus + CLI ---------------------------------------------------------------


def test_bundled_timesplit_corpus_beats_chance():
    """The shipped demo must actually demonstrate the claim it advertises."""
    report = validate_retrospective(
        find_data_file("examples/discovery_corpus_timesplit_demo.json"),
        seeds=["Fish oil"],
        cutoff_year=1986,
    )
    assert report.n_confirmed >= 1
    assert report.lift is not None and report.lift > 1.0


def test_cli_validate_json_and_text(capsys):
    from artificial_emotions.cli import main

    path = str(find_data_file("examples/discovery_corpus_timesplit_demo.json"))
    argv = ["validate", "--corpus", path, "--cutoff", "1986", "--seeds", "Fish oil"]

    assert main([*argv, "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["n_confirmed"] >= 1

    assert main(argv) == 0
    text = capsys.readouterr().out
    assert "CONFIRMED" in text
    assert "baseline" in text
    assert "Not claimed" in text


def test_concept_pool_dedupes_strips_and_sorts():
    docs = [
        {"concepts": ["Fish oil", " Blood viscosity ", "Fish oil", ""]},
        {"concepts": ["Raynaud disease", "Blood viscosity"]},
        {"title": "no concepts key"},
        {"concepts": None},
    ]
    assert concept_pool(docs) == ["Blood viscosity", "Fish oil", "Raynaud disease"]
    assert concept_pool([]) == []
