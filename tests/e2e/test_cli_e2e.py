"""CLI end-to-end journeys via curiosity.cli.main (offline / fast path)."""

from __future__ import annotations

import json

import pytest

from artificial_curiosity.cli import main

pytestmark = pytest.mark.e2e


def test_cli_spark_json(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["spark", "--domain", "ai", "--n", "3", "--json"])
    assert code == 0
    pack = json.loads(capsys.readouterr().out)
    assert pack["count"] >= 1
    assert "inject" in pack
    assert pack["unknowns"][0]["question"]
    assert pack["value_profile"]["name"]


def test_cli_run_no_literature_json(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(
        [
            "run",
            "--domain",
            "ai",
            "--n",
            "3",
            "--candidates",
            "8",
            "--no-literature",
            "--json",
        ]
    )
    assert code == 0
    rows = json.loads(capsys.readouterr().out)
    assert isinstance(rows, list)
    assert len(rows) >= 1
    assert rows[0]["question"]["question"]
    assert "curiosity_score" in rows[0]
    flags = rows[0].get("flags") or []
    assert "no_literature" in flags or rows[0]["gap"]["status"]


def test_cli_profiles_and_eval_json(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["profiles", "--json"])
    assert code == 0
    profiles = json.loads(capsys.readouterr().out)
    names = {p["name"] for p in profiles}
    assert "humanity_default" in names
    assert "alignment_lab" in names

    code = main(["eval", "--json"])
    assert code == 0
    report = json.loads(capsys.readouterr().out)
    assert report["n_cases"] >= 1
    assert "match_rate" in report
    assert "methodology" in report
    assert "already_answered_fail_rate" in report


def test_cli_spark_text_mentions_investigate(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["spark", "--domain", "biology", "--n", "2"])
    assert code == 0
    out = capsys.readouterr().out
    assert "What should we investigate next?" in out


def test_cli_emotions_cues_annotate_pack(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["emotions", "cues", "--json"])
    assert code == 0
    cues = json.loads(capsys.readouterr().out)
    assert "information_gap" in cues["tags"]

    code = main(
        [
            "epistemic",
            "annotate",
            "What remains unknown about epistemic emotion elicitation?",
            "--surprise",
            "0.8",
            "--json",
        ]
    )
    assert code == 0
    ann = json.loads(capsys.readouterr().out)
    assert ann["epistemic_cues"]["tags"]

    code = main(["emotions", "pack", "--json"])
    assert code == 0
    pack = json.loads(capsys.readouterr().out)
    assert pack["count"] >= 8
    assert pack["name"] == "affective_science"

    code = main(["emotions", "catalog", "--json"])
    assert code == 0
    cat = json.loads(capsys.readouterr().out)
    assert cat["count"] >= 20
    assert "curiosity" in cat["ids"]

    code = main(
        [
            "emotions",
            "mix",
            "curiosity=40",
            "confusion=30",
            "awe=30",
            "--json",
        ]
    )
    assert code == 0
    mix = json.loads(capsys.readouterr().out)
    assert abs(mix["sum_weights"] - 1.0) < 1e-9
    assert mix["honesty"] == "annotation_only"
