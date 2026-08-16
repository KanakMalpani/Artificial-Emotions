"""Handler family split: stable re-export, no schema/contract churn."""

from __future__ import annotations

import ast
from pathlib import Path

from artificial_emotions.agent_tools import dispatch_tool, mcp_tool_list
from artificial_emotions.agent_tools_pkg import handlers as handlers_mod
from artificial_emotions.agent_tools_pkg.handler_families import (
    curiosity,
    emotions,
    eval_tools,
    imagine,
    investigate,
    memory,
    stances,
)
from artificial_emotions.agent_tools_pkg.registry import HANDLERS, TOOL_SPECS
from artificial_emotions.mcp_lint import lint_tool_specs
from artificial_emotions.timeutil import parse_iso

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
    "handle_annotate_epistemic",
    "handle_apply_imagination",
    "handle_apply_stance",
    "handle_compare_profiles",
    "handle_constitution_compare",
    "handle_critique_brief",
    "handle_cross_model_vote",
    "handle_decompose_question",
    "handle_dream_reanalyze",
    "handle_elicit_helpers",
    "handle_emotion_catalog",
    "handle_emotion_pack",
    "handle_explore_curiosity",
    "handle_export_unknowns",
    "handle_idea_graph",
    "handle_imagine_transfer",
    "handle_list_domains",
    "handle_list_epistemic_cues",
    "handle_list_imagination_kinds",
    "handle_list_profiles",
    "handle_list_stances",
    "handle_memory_avoiding",
    "handle_memory_forget",
    "handle_memory_reset",
    "handle_memory_show",
    "handle_mix_emotions",
    "handle_preference_weight_hints",
    "handle_provoke_curiosity",
    "handle_rank_unknowns",
    "handle_soundness_pass",
    "handle_surprise_worksheet",
    "handle_voi_worksheet",
)


def test_handlers_reexport_same_objects_as_families():
    """Stable import path must be the same objects as the family modules."""
    by_name: dict[str, object] = {}
    for mod in _FAMILY_MODULES:
        for name in getattr(mod, "__all__", ()):
            by_name[name] = getattr(mod, name)
    assert set(by_name) == set(_REEXPORT_NAMES)
    for name in _REEXPORT_NAMES:
        assert getattr(handlers_mod, name) is by_name[name]


def test_handlers_all_matches_reexport_names():
    public = [n for n in handlers_mod.__all__ if n != "ToolHandler"]
    assert public == list(_REEXPORT_NAMES)


def test_callers_import_handlers_not_families():
    """Callers stay on the stable re-export — no family-module churn."""
    for rel in ("registry.py", "mcp_resources.py"):
        src = (_PKG / rel).read_text(encoding="utf-8")
        tree = ast.parse(src)
        imported: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)
        assert "artificial_emotions.agent_tools_pkg.handlers" in imported, rel
        assert not any("handler_families" in m for m in imported), rel


def test_mcp_tool_names_and_lint_unchanged():
    names = {t["name"] for t in mcp_tool_list()}
    spec_names = {t["name"] for t in TOOL_SPECS}
    assert names == spec_names
    assert names == set(HANDLERS)
    assert "provoke_curiosity" in names
    assert "preference_weight_hints" in names
    assert "imagine_transfer" in names
    errors = lint_tool_specs(mcp_tool_list())
    assert errors == [], errors


def test_dispatch_one_tool_per_family():
    domains = dispatch_tool("list_domains", {})
    assert "ai" in domains["domains"]

    cues = dispatch_tool("list_epistemic_cues", {})
    assert isinstance(cues, dict)

    voi = dispatch_tool("voi_worksheet", {"question": "q", "domain": "ai"})
    assert voi["honesty"] == "not_evsi"

    st = dispatch_tool("list_stances", {})
    assert st["stances"]

    kinds = dispatch_tool("list_imagination_kinds", {})
    assert kinds["transfer"]["tool"] == "imagine_transfer"

    mem = dispatch_tool("memory_forget", {"what": "mood", "confirm": False})
    assert mem["refused"] is True

    critique = dispatch_tool("critique_brief", {"question": "why is this unknown?"})
    assert isinstance(critique, dict)


def test_preference_hints_still_refuse_filesystem_paths(tmp_path: Path):
    out = dispatch_tool(
        "preference_weight_hints",
        {"path": str(tmp_path / "events.jsonl"), "events": []},
    )
    assert out["ok"] is False
    assert out["reason"] == "filesystem_paths_not_accepted"
    assert out["applied"] is False


def test_surprise_worksheet_logged_at_is_iso_utc():
    out = dispatch_tool("surprise_worksheet", {"question_id": "q-iso"})
    stamp = out["fields"]["logged_at"]
    parsed = parse_iso(stamp)
    assert parsed is not None
    assert parsed.tzinfo is not None
    assert "+00:00" in stamp
    assert not stamp.endswith("Z")
    assert "EVSI" in (out.get("honesty") or "")
