"""CLI parser split: stable facade, unchanged flags, argparse-only groups."""

from __future__ import annotations

import argparse
import ast
from pathlib import Path

from artificial_emotions import cli as cli_mod
from artificial_emotions.cli import build_parser as cli_build_parser
from artificial_emotions.cli_pkg import build_parser as pkg_build_parser
from artificial_emotions.cli_pkg.parser import build_parser as parser_build_parser

_CLI_PKG = Path(__file__).resolve().parents[1] / "src" / "artificial_emotions" / "cli_pkg"

_TOP_LEVEL = frozenset(
    {
        "run",
        "serve",
        "spark",
        "profiles",
        "preferences",
        "compare-profiles",
        "critique-brief",
        "stance",
        "imagine",
        "validate",
        "discover",
        "explore",
        "loop",
        "decompose",
        "voi-worksheet",
        "surprise-worksheet",
        "eval",
        "emotions",
        "epistemic",
        "memory",
        "dream",
        "export",
    }
)


def _subparsers(parser: argparse.ArgumentParser) -> argparse._SubParsersAction:
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction) and action.dest == "command":
            return action
    raise AssertionError("expected a 'command' subparser group")


def test_build_parser_facade_is_one_function():
    assert cli_build_parser is pkg_build_parser is parser_build_parser
    assert cli_mod.build_parser is parser_build_parser


def test_parser_is_a_package_not_a_module_file():
    assert (_CLI_PKG / "parser" / "__init__.py").is_file()
    assert not (_CLI_PKG / "parser.py").exists()


def test_top_level_subcommand_set_unchanged():
    names = set(_subparsers(parser_build_parser()).choices)
    assert names == _TOP_LEVEL


def test_run_spark_serve_defaults_and_dests():
    parser = parser_build_parser()
    run = parser.parse_args(["run"])
    assert run.command == "run"
    assert run.domain == "ai"
    assert run.topic == ""
    assert run.n == 8
    assert run.candidates == 16
    assert run.llm is False
    assert run.no_literature is False
    assert run.literature_backend == "openalex"
    assert run.json is False
    assert run.model == "gpt-4o-mini"
    assert run.judge_model is None
    assert run.judge_ensemble == 1
    assert run.base_url is None
    assert run.profile == "humanity_default"
    assert run.diversity == "jaccard"
    assert run.preference_log is None
    assert run.preference_rerank is None
    assert run.preference_learn is None
    assert run.preference_learn_apply is False
    assert run.lit_cache is None
    assert run.lit_workers == 4

    spark = parser.parse_args(["spark"])
    assert spark.n == 5
    assert spark.literature is False
    assert spark.compact is False
    assert spark.model is None
    assert spark.profile == "humanity_default"
    assert spark.diversity == "jaccard"

    serve = parser.parse_args(["serve"])
    assert serve.host is None
    assert serve.port is None
    assert serve.reload is False


def test_serve_help_keeps_nonlocal_bind_opt_in():
    """Bind refuse is the serve handler; parser help must still name the env var."""
    parser = parser_build_parser()
    parent = " ".join(parser.format_help().split())
    assert "CURIOSITY_API_KEY" in parent
    assert "non-loopback bind requires CURIOSITY_ALLOW_NONLOCAL_BIND=1" in parent
    serve = _subparsers(parser).choices["serve"]
    text = " ".join(serve.format_help().split())
    assert "CURIOSITY_ALLOW_NONLOCAL_BIND=1" in text
    assert "CURIOSITY_HOST" in text
    assert "CURIOSITY_PORT" in text


def test_eval_alive_worksheet_defaults():
    parser = parser_build_parser()

    ev = parser.parse_args(["eval"])
    assert ev.eval_cmd == "spotcheck"
    assert ev.fixtures is None
    assert ev.path is None
    assert ev.n == 3
    assert ev.profile == "humanity_default"
    assert ev.domain == "ai"

    explore = parser.parse_args(["explore"])
    assert explore.steps == 5
    assert explore.n == 5
    assert explore.affect_weights is False
    assert explore.somatic_modulate is False
    assert explore.no_jump is False
    assert explore.no_memory is False
    assert explore.preference_log is None

    loop = parser.parse_args(["loop", "--outcomes", "x.jsonl"])
    assert loop.outcomes == "x.jsonl"
    assert loop.profile is None

    voi = parser.parse_args(["voi-worksheet"])
    assert voi.question_id is None
    assert voi.operationalization == ""
    assert voi.profile is None
    assert voi.domain == ""

    surprise = parser.parse_args(["surprise-worksheet"])
    assert surprise.profile_name is None
    assert surprise.predicted_surprise is None
    assert surprise.belief_shift is None
    assert surprise.crude_update_note == ""


def test_nested_preference_export_emotion_dests():
    parser = parser_build_parser()
    hints = parser.parse_args(["preferences", "hints", "--path", "p.jsonl", "--apply", "--json"])
    assert hints.preferences_cmd == "hints"
    assert hints.path == "p.jsonl"
    assert hints.apply is True
    assert hints.profile == "humanity_default"

    pair = parser.parse_args(["preferences", "suggest-pair", "--candidates", "a,b"])
    assert pair.candidates == "a,b"
    assert pair.path is None

    unk = parser.parse_args(["export", "unknowns", "--from", "prev.json", "--out", "out.json"])
    assert unk.export_cmd == "unknowns"
    assert unk.from_path == "prev.json"
    assert unk.out == "out.json"
    assert unk.n == 8
    assert unk.lit_workers == 4

    mix = parser.parse_args(["emotions", "mix", "curiosity=40", "awe=60"])
    assert mix.emotions_cmd == "mix"
    assert mix.parts == ["curiosity=40", "awe=60"]
    assert mix.simulate_feeling == "true"

    mem = parser.parse_args(["memory", "show"])
    assert mem.memory_cmd == "show"
    assert mem.path is None

    dream = parser.parse_args(["dream", "--json"])
    assert dream.json is True
    assert dream.path is None


def test_compare_critique_decompose_dest_aliases():
    parser = parser_build_parser()
    cmp_ = parser.parse_args(["compare-profiles"])
    assert cmp_.profile_a == "humanity_default"
    assert cmp_.profile_b == "alignment_lab"
    assert cmp_.n == 8

    critique = parser.parse_args(["critique-brief", "--ops", "o", "--why", "w"])
    assert critique.operationalization == "o"
    assert critique.why_it_matters == "w"

    decomp = parser.parse_args(["decompose", "why?"])
    assert decomp.question == "why?"
    assert decomp.depth == 1
    assert decomp.answerability is None
    assert decomp.operationalization == ""


def test_parser_group_modules_do_not_import_handlers():
    imported: list[str] = []
    for path in (_CLI_PKG / "parser").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)
            elif isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
    assert all(not m.startswith("artificial_emotions.cli_pkg.commands") for m in imported)
    assert "uvicorn" not in imported
    assert "artificial_emotions.pipeline" not in imported
    assert "artificial_emotions.api" not in imported
