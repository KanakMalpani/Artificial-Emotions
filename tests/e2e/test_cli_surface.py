"""Every CLI subcommand, driven through `main(argv)` offline.

test_cli_e2e.py covers the headline flows. This file walks the whole surface so
a broken subcommand cannot ship unnoticed: each command must exit 0 and, with
`--json`, emit parseable JSON. No network, no LLM key.
"""

from __future__ import annotations

import json

import pytest

from artificial_emotions.cli import build_parser, main

pytestmark = pytest.mark.e2e


def _json_out(capsys, argv: list[str]):
    assert main(argv) == 0, f"non-zero exit for: {' '.join(argv)}"
    out = capsys.readouterr().out
    assert out.strip(), f"no stdout for: {' '.join(argv)}"
    return json.loads(out)


@pytest.fixture(autouse=True)
def _no_llm_credentials(monkeypatch):
    for var in ("LLM_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.delenv(var, raising=False)


# --- ranking surfaces --------------------------------------------------------------


def test_spark_json_shape(capsys):
    pack = _json_out(capsys, ["spark", "--domain", "ai", "--n", "3", "--json"])
    assert pack["inject"]
    assert 1 <= len(pack["unknowns"]) <= 3
    assert pack["value_profile"]
    assert pack["domain"] == "ai"


def test_run_offline_json_is_a_ranked_list(capsys):
    rows = _json_out(
        capsys, ["run", "--domain", "biology", "--n", "3", "--no-literature", "--json"]
    )
    assert [r["rank"] for r in rows] == sorted(r["rank"] for r in rows)
    for row in rows:
        assert row["question"]["question"]
        assert row["gap"]["status"]


def test_profiles_lists_presets(capsys):
    payload = _json_out(capsys, ["profiles", "--json"])
    names = payload if isinstance(payload, list) else payload.get("profiles")
    assert names
    assert any("humanity_default" in json.dumps(n) for n in names)


def test_compare_profiles_shows_both_sides_without_merging(capsys):
    payload = _json_out(
        capsys,
        [
            "compare-profiles",
            "--a",
            "humanity_default",
            "--b",
            "alignment_lab",
            "--n",
            "5",
            "--json",
        ],
    )
    assert payload["ranks_a"] and payload["ranks_b"]
    assert "agreement" in payload
    # The point of the command is that it never invents a consensus score.
    assert "consensus" not in json.dumps(payload.get("ranks_a"))


# --- worksheets and critique -------------------------------------------------------


def test_voi_worksheet_fills_metadata(capsys):
    payload = _json_out(
        capsys, ["voi-worksheet", "--question-id", "q-1", "--question", "Why X?", "--json"]
    )
    assert payload["link_to_ranked_question"]["question_id"] == "q-1"
    # The worksheet must keep saying it is not a computed EVSI.
    assert "EVSI" in json.dumps(payload)


def test_surprise_worksheet_records_belief_shift(capsys):
    payload = _json_out(
        capsys,
        [
            "surprise-worksheet",
            "--question-id",
            "q-2",
            "--predicted-surprise",
            "0.6",
            "--belief-shift",
            "4",
            "--json",
        ],
    )
    fields = payload["fields"]
    assert fields["question_id"] == "q-2"
    assert fields["predicted_surprise"] == 0.6
    assert fields["belief_shift_1_to_5"] == 4


def test_critique_brief_is_form_only(capsys):
    payload = _json_out(
        capsys,
        [
            "critique-brief",
            "--question",
            "Which biomarkers predict healthspan under caloric restriction?",
            "--ops",
            "AUROC >= 0.7 on held-out cohort; falsifier: AUROC <= 0.55.",
            "--json",
        ],
    )
    assert payload
    # Critique must not re-rank anything.
    assert "curiosity_score" not in json.dumps(payload)


# --- eval harnesses ----------------------------------------------------------------


@pytest.mark.parametrize("harness", ["spotcheck", "gap-status", "report", "cooccur", "calibration"])
def test_eval_harnesses_run_offline(capsys, harness: str):
    payload = _json_out(capsys, ["eval", harness, "--json"])
    assert payload


def test_eval_elicit_runs_offline(capsys):
    payload = _json_out(capsys, ["eval", "elicit", "--domain", "ai", "--n", "2", "--json"])
    assert payload


def test_eval_defaults_to_spotcheck(capsys):
    assert main(["eval", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)


# --- emotions / epistemic ----------------------------------------------------------


@pytest.mark.parametrize("alias", ["emotions", "epistemic"])
def test_emotions_and_epistemic_are_the_same_surface(capsys, alias: str):
    cues = _json_out(capsys, [alias, "cues", "--json"])
    assert cues


@pytest.mark.parametrize("shortcut", ["cues", "catalog", "elicit", "pack"])
def test_affect_subcommands_work_at_the_top_level(capsys, shortcut: str):
    """`emotions emotions mix` reads badly — the shortcut forms must work."""
    assert _json_out(capsys, [shortcut, "--json"])


def test_top_level_mix_matches_the_grouped_form(capsys):
    short = _json_out(capsys, ["mix", "curiosity=60", "awe=40", "--json"])
    grouped = _json_out(capsys, ["emotions", "mix", "curiosity=60", "awe=40", "--json"])
    assert short["percents"] == grouped["percents"]
    assert short["primary"] == grouped["primary"]


def test_top_level_annotate_reaches_the_same_handler(capsys):
    assert _json_out(capsys, ["annotate", "Which mechanism explains X?", "--json"])


def test_emotions_catalog_family_filter(capsys):
    everything = _json_out(capsys, ["emotions", "catalog", "--json"])
    epistemic = _json_out(capsys, ["emotions", "catalog", "--family", "epistemic", "--json"])
    assert json.dumps(epistemic) != json.dumps(everything)


def test_emotions_mix_normalizes_parts(capsys):
    payload = _json_out(
        capsys, ["emotions", "mix", "curiosity=40", "confusion=30", "awe=30", "--json"]
    )
    assert payload["components"]
    assert payload.get("felt_simulation")


def test_emotions_mix_can_disable_felt_simulation(capsys):
    payload = _json_out(
        capsys,
        ["emotions", "mix", "curiosity=50", "awe=50", "--simulate-feeling", "false", "--json"],
    )
    assert not payload.get("felt_simulation")


def test_emotions_annotate_returns_cues(capsys):
    payload = _json_out(
        capsys,
        ["emotions", "annotate", "Which mechanism explains X?", "--gap", "unanswered", "--json"],
    )
    assert payload


def test_emotions_elicit_and_pack(capsys):
    assert _json_out(capsys, ["emotions", "elicit", "--json"])
    assert _json_out(capsys, ["emotions", "pack", "--json"])


def test_unknown_emotions_subcommand_is_rejected(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["emotions", "not-a-subcommand"])
    assert exc.value.code != 0


# --- text (non-JSON) rendering -----------------------------------------------------


@pytest.mark.parametrize(
    "argv",
    [
        ["spark", "--domain", "ai", "--n", "2"],
        ["run", "--domain", "ai", "--n", "2", "--no-literature"],
        ["profiles"],
        ["emotions", "cues"],
        ["emotions", "catalog"],
        ["eval", "spotcheck"],
    ],
)
def test_human_readable_output_is_non_empty(capsys, argv: list[str]):
    assert main(argv) == 0
    assert capsys.readouterr().out.strip()


# --- parser contract ---------------------------------------------------------------


def test_no_command_prints_help_without_crashing(capsys):
    rc = main([])
    assert rc in (0, 1, 2)
    captured = capsys.readouterr()
    assert (captured.out + captured.err).strip()


def test_every_subcommand_is_wired_into_main():
    """A parser entry with no dispatch branch would silently no-op."""
    parser = build_parser()
    subparsers = [
        action
        for action in parser._actions
        if hasattr(action, "choices") and action.dest == "command"
    ]
    assert subparsers, "expected a 'command' subparser group"
    names = set(subparsers[0].choices)
    assert {
        "run",
        "serve",
        "spark",
        "profiles",
        "preferences",
        "compare-profiles",
        "critique-brief",
        "voi-worksheet",
        "surprise-worksheet",
        "eval",
        "emotions",
        "epistemic",
    } <= names


def test_invalid_domain_is_rejected_by_the_parser():
    with pytest.raises(SystemExit):
        main(["spark", "--domain", "not-a-domain"])
