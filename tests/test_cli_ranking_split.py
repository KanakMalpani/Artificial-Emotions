"""CLI ranking / lenses split: stable re-export, no parser or flag churn."""

from __future__ import annotations

import ast
from pathlib import Path

from artificial_emotions.cli_pkg.commands import explore as explore_cmd
from artificial_emotions.cli_pkg.commands import lenses, ranking

_CLI_PKG = Path(__file__).resolve().parents[1] / "src" / "artificial_emotions" / "cli_pkg"

_LENS_HANDLERS = ("_discover", "_imagine", "_stance")
_RANKING_OWNED = ("_run_engine", "_spark", "_serve")
_EXPLORE_HANDLER = "_explore"


def test_ranking_reexports_same_lens_handlers():
    """Dispatch stays on ranking.py; implementations live in lenses.py."""
    assert set(lenses.__all__) == set(_LENS_HANDLERS)
    for name in _LENS_HANDLERS:
        assert getattr(ranking, name) is getattr(lenses, name)
        assert name in ranking.__all__


def test_ranking_reexports_explore_handler():
    """Dispatch stays on ranking.py; implementation lives in commands/explore.py."""
    assert set(explore_cmd.__all__) == {_EXPLORE_HANDLER}
    assert getattr(ranking, _EXPLORE_HANDLER) is getattr(explore_cmd, _EXPLORE_HANDLER)
    assert _EXPLORE_HANDLER in ranking.__all__
    assert _EXPLORE_HANDLER not in lenses.__all__


def test_lenses_do_not_define_run_spark_serve():
    for name in _RANKING_OWNED:
        assert name not in lenses.__all__
        assert name in ranking.__all__
        assert callable(getattr(ranking, name))
    assert _EXPLORE_HANDLER in ranking.__all__
    assert callable(getattr(ranking, _EXPLORE_HANDLER))


def test_parser_does_not_import_command_handlers():
    """Parser package stays argparse-only — not coupled to handlers."""
    parser_dir = _CLI_PKG / "parser"
    imported: list[str] = []
    for path in parser_dir.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)
            elif isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
    assert not any("commands" in m for m in imported)
    assert not any(
        m.endswith(".lenses") or m.endswith(".ranking") or m.endswith(".explore") for m in imported
    )


def test_dispatch_table_still_imports_from_commands_package():
    src = (_CLI_PKG / "__init__.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    assert "artificial_emotions.cli_pkg.commands" in imported
    assert not any("commands.lenses" in m for m in imported)
    assert not any("commands.ranking" in m for m in imported)
    assert not any("commands.explore" in m for m in imported)
