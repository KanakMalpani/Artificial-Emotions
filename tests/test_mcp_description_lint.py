"""MCP / OpenAI tool-description lint (research/MCP_DESCRIPTION_LINT.md)."""

from __future__ import annotations

import json
from pathlib import Path

from artificial_emotions.agent_tools import mcp_tool_list, openai_tools
from artificial_emotions.mcp_lint import FORBIDDEN_PHRASES, lint_tool_specs


def test_mcp_descriptions_pass_lint():
    errors = lint_tool_specs(mcp_tool_list())
    assert errors == [], errors


def test_openai_tools_pass_lint():
    errors = lint_tool_specs(openai_tools())
    assert errors == [], errors


def test_static_openai_tools_json_pass_lint():
    path = Path(__file__).resolve().parents[1] / "examples" / "openai_tools.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = lint_tool_specs(data)
    assert errors == [], errors


def test_forbidden_phrase_table_covers_spec():
    # Sanity: research table keys present
    for phrase in (
        "always use",
        "you must",
        "emotion recognition",
        "guaranteed breakthrough",
        "feels curiosity",
    ):
        assert phrase in FORBIDDEN_PHRASES
