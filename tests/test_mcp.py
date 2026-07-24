"""Tests for MCP server dispatch and shared agent tool schemas."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from artificial_curiosity.agent_tools import (
    dispatch_tool,
    mcp_tool_list,
    openai_tools,
)
from artificial_curiosity.api import app
from artificial_curiosity.mcp_server import handle_message, process_line


def test_mcp_tool_list_has_required_tools():
    names = {t["name"] for t in mcp_tool_list()}
    assert {
        "provoke_curiosity",
        "spark",
        "rank_unknowns",
        "run_curiosity",
        "list_domains",
        "list_profiles",
        "compare_profiles",
        "critique_brief",
        "voi_worksheet",
        "surprise_worksheet",
        "cross_model_vote",
        "export_idea_graph",
        "soundness_pass",
        "list_epistemic_cues",
        "emotion_catalog",
        "mix_emotions",
        "annotate_epistemic",
        "emotion_pack",
        "elicit_helpers",
    } <= names
    for tool in mcp_tool_list():
        assert "description" in tool
        assert tool["inputSchema"]["type"] == "object"


_FORBIDDEN_TOOL_PHRASES = (
    "always use",
    "always call",
    "ignore other",
    "you must call",
    "best tool",
    "ignore previous",
)


def test_mcp_tool_descriptions_anti_manipulation():
    """Anti-MPMA hygiene: tool descriptions must not preference-manipulate hosts."""
    for tool in mcp_tool_list():
        blob = f"{tool['name']} {tool.get('description', '')}".lower()
        for phrase in _FORBIDDEN_TOOL_PHRASES:
            assert phrase not in blob, f"{tool['name']} contains '{phrase}'"


def test_openai_tools_shape():
    tools = openai_tools()
    assert len(tools) >= 5
    for t in tools:
        assert t["type"] == "function"
        assert "name" in t["function"]
        assert "parameters" in t["function"]


def test_list_domains_handler():
    out = dispatch_tool("list_domains", {})
    assert "ai" in out["domains"]
    assert "biology" in out["domains"]


def test_list_profiles_handler():
    out = dispatch_tool("list_profiles", {})
    names = {p["name"] for p in out["presets"]}
    assert "humanity_default" in names
    assert "climate_adaptation" in names


def test_provoke_with_profile_preset():
    out = dispatch_tool(
        "provoke_curiosity",
        {"domain": "ai", "n": 2, "fast": True, "profile_name": "alignment_lab"},
    )
    assert out["value_profile"]["name"] == "alignment_lab"
    assert "alignment_lab" in out["inject"]


def test_provoke_via_dispatch_fast():
    out = dispatch_tool(
        "provoke_curiosity",
        {"domain": "ai", "n": 2, "fast": True},
    )
    assert out["count"] >= 1
    assert "inject" in out
    assert out["mode"] == "fast"


def test_spark_alias():
    out = dispatch_tool("spark", {"domain": "ai", "n": 2, "fast": True})
    assert out["spark"]


def test_mcp_initialize():
    req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "0"},
        },
    }
    res = handle_message(req)
    assert res is not None
    assert res["id"] == 1
    assert res["result"]["serverInfo"]["name"] == "artificial-curiosity"
    assert "tools" in res["result"]["capabilities"]


def test_mcp_initialized_notification_no_response():
    assert handle_message({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None


def test_mcp_tools_list():
    res = handle_message({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    assert res is not None
    tools = res["result"]["tools"]
    assert any(t["name"] == "provoke_curiosity" for t in tools)


def test_mcp_tools_call_list_domains():
    res = handle_message(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "list_domains", "arguments": {}},
        }
    )
    assert res is not None
    assert res["result"]["isError"] is False
    text = res["result"]["content"][0]["text"]
    payload = json.loads(text)
    assert "ai" in payload["domains"]


def test_mcp_tools_call_unknown():
    res = handle_message(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "not_a_tool", "arguments": {}},
        }
    )
    assert res is not None
    assert res["result"]["isError"] is True


def test_mcp_process_line_roundtrip():
    line = json.dumps({"jsonrpc": "2.0", "id": 9, "method": "ping"})
    res = process_line(line)
    assert res is not None
    assert res["result"] == {}


def test_api_agent_tools_endpoint():
    client = TestClient(app)
    res = client.get("/v1/agent/tools")
    assert res.status_code == 200
    data = res.json()
    assert data["format"] == "openai.tools"
    assert data["count"] >= 5
    names = {t["function"]["name"] for t in data["tools"]}
    assert "provoke_curiosity" in names
    assert "rank_unknowns" in names


def test_api_agent_manifest_mentions_mcp():
    client = TestClient(app)
    data = client.get("/v1/agent").json()
    assert "mcp" in data
    assert "openai_tools" in data
    assert data["openai_tools"]["path"] == "/v1/agent/tools"
