"""Drive the MCP stdio transport the way a real host does (offline).

`handle_message` is covered in test_mcp.py. This file covers the layer hosts
actually run: the `run_stdio` read loop, the `curiosity-mcp` argv handling, and
the malformed-input paths a misbehaving client can produce.
"""

from __future__ import annotations

import io
import json

import pytest

from artificial_emotions import __version__
from artificial_emotions.mcp_server import (
    INTERNAL_ERROR,
    INVALID_PARAMS,
    INVALID_REQUEST,
    METHOD_NOT_FOUND,
    PARSE_ERROR,
    main,
    process_line,
    run_stdio,
)


def _drive(*messages: dict) -> list[dict]:
    """Feed newline-delimited JSON-RPC through run_stdio and collect responses."""
    stdin = io.StringIO("".join(json.dumps(m) + "\n" for m in messages))
    stdout = io.StringIO()
    run_stdio(stdin=stdin, stdout=stdout)
    return [json.loads(line) for line in stdout.getvalue().splitlines() if line.strip()]


def test_stdio_handshake_then_tools_list():
    responses = _drive(
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
    )
    # The notification must not produce a response.
    assert [r["id"] for r in responses] == [1, 2]

    init = responses[0]["result"]
    assert init["serverInfo"]["version"] == __version__
    assert "tools" in init["capabilities"]

    tools = responses[1]["result"]["tools"]
    assert tools
    names = {t["name"] for t in tools}
    assert "provoke_curiosity" in names
    for tool in tools:
        assert tool["description"]
        assert tool["inputSchema"]["type"] == "object"


def test_stdio_stops_at_eof_and_ignores_blank_lines():
    stdin = io.StringIO('\n\n{"jsonrpc": "2.0", "id": 9, "method": "ping"}\n\n')
    stdout = io.StringIO()
    run_stdio(stdin=stdin, stdout=stdout)
    lines = [ln for ln in stdout.getvalue().splitlines() if ln.strip()]
    assert len(lines) == 1
    assert json.loads(lines[0]) == {"jsonrpc": "2.0", "id": 9, "result": {}}


def test_stdio_tool_call_roundtrip():
    responses = _drive(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "list_domains", "arguments": {}},
        }
    )
    result = responses[0]["result"]
    assert result["isError"] is False
    payload = json.loads(result["content"][0]["text"])
    assert payload


def test_stdio_tool_errors_are_reported_in_band_not_as_rpc_errors():
    """A failing tool must reach the model as isError content, not kill the session."""
    responses = _drive(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "definitely_not_a_tool", "arguments": {}},
        }
    )
    assert "error" not in responses[0]
    result = responses[0]["result"]
    assert result["isError"] is True
    assert "definitely_not_a_tool" in result["content"][0]["text"]


def test_stdio_survives_a_bad_line_and_keeps_serving():
    stdin = io.StringIO(
        "{not json at all\n" + json.dumps({"jsonrpc": "2.0", "id": 5, "method": "ping"}) + "\n"
    )
    stdout = io.StringIO()
    run_stdio(stdin=stdin, stdout=stdout)
    responses = [json.loads(ln) for ln in stdout.getvalue().splitlines() if ln.strip()]
    assert responses[0]["error"]["code"] == PARSE_ERROR
    assert responses[1]["result"] == {}


def test_stdio_writes_valid_utf8_json_for_non_ascii_arguments():
    responses = _drive(
        {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {"name": "provoke_curiosity", "arguments": {"topic": "café — naïve 🎯"}},
        }
    )
    assert responses[0]["id"] == 6
    assert responses[0]["result"]["content"][0]["text"]


@pytest.mark.parametrize(
    ("message", "code"),
    [
        ({"jsonrpc": "1.0", "id": 1, "method": "ping"}, INVALID_REQUEST),
        ({"jsonrpc": "2.0", "id": 1, "method": "nope/nope"}, METHOD_NOT_FOUND),
        ({"jsonrpc": "2.0", "id": 1, "method": "resources/read", "params": {}}, INVALID_PARAMS),
        (
            {"jsonrpc": "2.0", "id": 1, "method": "resources/read", "params": {"uri": ""}},
            INVALID_PARAMS,
        ),
        (
            {"jsonrpc": "2.0", "id": 1, "method": "resources/read", "params": {"uri": "bogus://x"}},
            INVALID_PARAMS,
        ),
        ({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {}}, INVALID_PARAMS),
        (
            {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": 42}},
            INVALID_PARAMS,
        ),
        (
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "list_domains", "arguments": "not-an-object"},
            },
            INVALID_PARAMS,
        ),
    ],
)
def test_protocol_errors_use_expected_codes(message: dict, code: int):
    response = process_line(json.dumps(message))
    assert response is not None
    assert response["error"]["code"] == code


def test_non_object_message_is_an_invalid_request():
    response = process_line("[1, 2, 3]")
    assert response is not None
    assert response["error"]["code"] == INVALID_REQUEST


def test_process_line_ignores_whitespace_only_input():
    assert process_line("   \n") is None


def test_process_line_converts_an_unexpected_crash_into_an_rpc_error(monkeypatch):
    import artificial_emotions.mcp_server as srv

    def boom(_msg):
        raise RuntimeError("kaboom")

    monkeypatch.setattr(srv, "handle_message", boom)
    response = srv.process_line(json.dumps({"jsonrpc": "2.0", "id": 7, "method": "ping"}))
    assert response is not None
    assert response["error"]["code"] == INTERNAL_ERROR
    assert response["id"] == 7


def test_resources_read_returns_contents():
    response = process_line(
        json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 8,
                "method": "resources/read",
                "params": {"uri": "curiosity://domains"},
            }
        )
    )
    assert response is not None
    assert "error" not in response
    assert response["result"]


def test_cli_help_exits_zero_and_names_the_entry_points(capsys):
    assert main(["--help"]) == 0
    assert "curiosity-mcp" in capsys.readouterr().err


def test_cli_list_tools_emits_parseable_json(capsys):
    assert main(["--list-tools"]) == 0
    tools = json.loads(capsys.readouterr().out)
    assert isinstance(tools, list) and tools
    assert all("name" in t and "inputSchema" in t for t in tools)


def test_cli_list_resources_emits_parseable_json(capsys):
    assert main(["--list-resources"]) == 0
    resources = json.loads(capsys.readouterr().out)
    assert isinstance(resources, list) and resources
    assert all("uri" in r for r in resources)


def test_cli_with_no_args_runs_the_stdio_loop(monkeypatch):
    called: list[bool] = []
    import artificial_emotions.mcp_server as srv

    monkeypatch.setattr(srv, "run_stdio", lambda: called.append(True))
    assert srv.main([]) == 0
    assert called == [True]
