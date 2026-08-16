"""Schema family split: stable re-export, no MCP/OpenAI contract churn."""

from __future__ import annotations

import ast
from pathlib import Path

from artificial_emotions.agent_tools import mcp_tool_list
from artificial_emotions.agent_tools_pkg import schemas as schemas_mod
from artificial_emotions.agent_tools_pkg.registry import TOOL_SPECS
from artificial_emotions.agent_tools_pkg.schema_families import (
    curiosity,
    emotions,
    eval_tools,
    imagine,
    investigate,
    memory,
    stances,
)
from artificial_emotions.mcp_lint import lint_tool_specs

_PKG = Path(__file__).resolve().parents[1] / "src" / "artificial_emotions" / "agent_tools_pkg"

_FAMILY_MODULES = (
    curiosity,
    emotions,
    eval_tools,
    imagine,
    investigate,
    memory,
    stances,
)

_REEXPORT_NAMES = (
    "ANNOTATE_EPISTEMIC_SCHEMA",
    "APPLY_IMAGINATION_SCHEMA",
    "APPLY_STANCE_SCHEMA",
    "COMPARE_PROFILES_SCHEMA",
    "CONSTITUTION_COMPARE_SCHEMA",
    "CRITIQUE_BRIEF_SCHEMA",
    "CROSS_MODEL_VOTE_SCHEMA",
    "DECOMPOSE_SCHEMA",
    "DREAM_REANALYZE_SCHEMA",
    "ELICIT_HELPERS_SCHEMA",
    "EMOTION_CATALOG_SCHEMA",
    "EMOTION_PACK_SCHEMA",
    "EXPLORE_SCHEMA",
    "EXPORT_UNKNOWNS_SCHEMA",
    "IDEA_GRAPH_SCHEMA",
    "IMAGINE_TRANSFER_SCHEMA",
    "LIST_DOMAINS_SCHEMA",
    "LIST_EPISTEMIC_CUES_SCHEMA",
    "LIST_IMAGINATION_KINDS_SCHEMA",
    "LIST_PROFILES_SCHEMA",
    "LIST_STANCES_SCHEMA",
    "MEMORY_AVOIDING_SCHEMA",
    "MEMORY_FORGET_SCHEMA",
    "MEMORY_RESET_SCHEMA",
    "MEMORY_SHOW_SCHEMA",
    "MIX_EMOTIONS_SCHEMA",
    "PREFERENCE_WEIGHT_HINTS_SCHEMA",
    "PROVOKE_SCHEMA",
    "RANK_SCHEMA",
    "SOUNDNESS_PASS_SCHEMA",
    "SURPRISE_WORKSHEET_SCHEMA",
    "VOI_WORKSHEET_SCHEMA",
)


def test_schemas_reexport_same_objects_as_families():
    """Stable import path must be the same objects as the family modules."""
    by_name: dict[str, object] = {}
    for mod in _FAMILY_MODULES:
        for name in getattr(mod, "__all__", ()):
            by_name[name] = getattr(mod, name)
    assert set(by_name) == set(_REEXPORT_NAMES)
    for name in _REEXPORT_NAMES:
        assert getattr(schemas_mod, name) is by_name[name]


def test_schemas_all_includes_reexport_names():
    public = [n for n in schemas_mod.__all__ if not n.startswith("_")]
    assert public == list(_REEXPORT_NAMES)


def test_callers_import_schemas_not_families():
    """Callers stay on the stable re-export — no family-module churn."""
    for rel in ("registry.py", "handlers.py", "__init__.py"):
        src = (_PKG / rel).read_text(encoding="utf-8")
        tree = ast.parse(src)
        imported: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)
        if rel == "handlers.py":
            assert not any("schema_families" in m for m in imported), rel
            continue
        assert "artificial_emotions.agent_tools_pkg.schemas" in imported, rel
        assert not any("schema_families" in m for m in imported), rel


def test_curiosity_handler_imports_domain_enum_from_schemas():
    src = (_PKG / "handler_families" / "curiosity.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    imported: list[str] = []
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
            names.extend(a.name for a in (node.names or []))
    assert "artificial_emotions.agent_tools_pkg.schemas" in imported
    assert "_DOMAIN_ENUM" in names
    assert not any("schema_families" in m for m in imported)
    from artificial_emotions.models import Domain

    assert schemas_mod._DOMAIN_ENUM == [d.value for d in Domain]


def test_mcp_schema_lint_unchanged():
    errors = lint_tool_specs(mcp_tool_list())
    assert errors == [], errors
    spec_names = {t["name"] for t in TOOL_SPECS}
    list_names = {t["name"] for t in mcp_tool_list()}
    assert spec_names == list_names
