"""Stdlib MCP server for Artificial Emotions (JSON-RPC 2.0 over stdio).

No MCP SDK dependency — newline-delimited JSON on stdin/stdout per the
MCP stdio transport. Logging goes to stderr only.

Entry points:
  curiosity-mcp
  python -m artificial_emotions.mcp_server
"""

from __future__ import annotations

import json
import sys
import traceback
from typing import Any, TextIO

from artificial_emotions import __version__
from artificial_emotions.agent_tools import (
    dispatch_tool,
    mcp_resource_list,
    mcp_resource_read,
    mcp_tool_list,
)

PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "artificial-emotions"

PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603


def _log(msg: str) -> None:
    sys.stderr.write(msg + "\n")
    sys.stderr.flush()


def _ok(id_: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": id_, "result": result}


def _err(id_: Any, code: int, message: str, data: Any = None) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": "2.0", "id": id_, "error": error}


def _tool_result(payload: Any, *, is_error: bool = False) -> dict[str, Any]:
    if isinstance(payload, str):
        text = payload
    else:
        text = json.dumps(payload, indent=2, default=str)
    return {
        "content": [{"type": "text", "text": text}],
        "isError": is_error,
    }


def handle_message(msg: dict[str, Any]) -> dict[str, Any] | None:
    """Dispatch one JSON-RPC message. Returns None for notifications."""
    if msg.get("jsonrpc") != "2.0":
        return _err(msg.get("id"), INVALID_REQUEST, "jsonrpc must be '2.0'")

    method = msg.get("method")
    id_ = msg.get("id")
    params = msg.get("params") or {}

    # Notifications have no id — never respond.
    is_notification = "id" not in msg

    if method == "notifications/initialized" or (
        isinstance(method, str) and method.startswith("notifications/")
    ):
        return None

    if is_notification:
        return None

    if method == "initialize":
        return _ok(
            id_,
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {
                    "tools": {},
                    "resources": {},
                },
                "serverInfo": {
                    "name": SERVER_NAME,
                    "version": __version__,
                },
                "instructions": (
                    "Artificial Emotions ranks valuable *unanswered* questions. "
                    "Use provoke_curiosity/spark for an instant inject pack; "
                    "rank_unknowns/run_curiosity for the full pipeline; "
                    "list_domains for supported domains. Scores are decision aids "
                    "with an explicit ValueProfile — not oracles. "
                    "Resources: curiosity://domains, curiosity://profiles, "
                    "curiosity://limits."
                ),
            },
        )

    if method == "ping":
        return _ok(id_, {})

    if method == "tools/list":
        return _ok(id_, {"tools": mcp_tool_list()})

    if method == "resources/list":
        return _ok(id_, {"resources": mcp_resource_list()})

    if method == "resources/read":
        if not isinstance(params, dict):
            return _err(id_, INVALID_PARAMS, "params must be an object")
        uri = params.get("uri")
        if not isinstance(uri, str) or not uri:
            return _err(id_, INVALID_PARAMS, "uri is required")
        try:
            return _ok(id_, mcp_resource_read(uri))
        except KeyError:
            return _err(id_, INVALID_PARAMS, f"Unknown resource: {uri}")
        except Exception as exc:  # noqa: BLE001
            return _err(id_, INTERNAL_ERROR, str(exc))

    if method == "tools/call":
        if not isinstance(params, dict):
            return _err(id_, INVALID_PARAMS, "params must be an object")
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if not isinstance(name, str) or not name:
            return _err(id_, INVALID_PARAMS, "tool name is required")
        if not isinstance(arguments, dict):
            return _err(id_, INVALID_PARAMS, "arguments must be an object")
        try:
            result = dispatch_tool(name, arguments)
            return _ok(id_, _tool_result(result, is_error=False))
        except KeyError:
            return _ok(
                id_,
                _tool_result(f"Unknown tool: {name}", is_error=True),
            )
        except Exception as exc:  # noqa: BLE001 — surface to the model
            _log(f"tool error ({name}): {exc}")
            return _ok(
                id_,
                _tool_result(f"Tool error: {exc}", is_error=True),
            )

    return _err(id_, METHOD_NOT_FOUND, f"Method not found: {method}")


def process_line(line: str) -> dict[str, Any] | None:
    """Parse one stdin line and return a response dict (or None)."""
    line = line.strip()
    if not line:
        return None
    try:
        msg = json.loads(line)
    except json.JSONDecodeError as exc:
        return _err(None, PARSE_ERROR, f"Parse error: {exc}")
    if not isinstance(msg, dict):
        return _err(None, INVALID_REQUEST, "Message must be a JSON object")
    try:
        return handle_message(msg)
    except Exception as exc:  # noqa: BLE001
        _log(traceback.format_exc())
        return _err(msg.get("id"), INTERNAL_ERROR, f"Internal error: {exc}")


def run_stdio(
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
) -> None:
    """Read newline-delimited JSON-RPC from stdin until EOF."""
    in_stream = stdin if stdin is not None else sys.stdin
    out_stream = stdout if stdout is not None else sys.stdout
    # Prefer binary-backed UTF-8 on Windows to avoid console encoding issues.
    if stdin is None and hasattr(sys.stdin, "buffer"):
        import io

        in_stream = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8", errors="replace")
    if stdout is None and hasattr(sys.stdout, "buffer"):
        import io

        out_stream = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    _log(f"{SERVER_NAME} MCP v{__version__} ready (stdio)")
    while True:
        line = in_stream.readline()
        if line == "":
            return
        response = process_line(line)
        if response is not None:
            out_stream.write(json.dumps(response, ensure_ascii=False) + "\n")
            out_stream.flush()


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in ("-h", "--help"):
        print(
            "Artificial Emotions MCP server (stdio).\n"
            "  curiosity-mcp\n"
            "  python -m artificial_emotions.mcp_server\n\n"
            "Wire into Cursor / Claude Desktop / VS Code Copilot MCP config.\n"
            "Tools: provoke_curiosity, spark, rank_unknowns, run_curiosity, "
            "list_domains, list_profiles",
            file=sys.stderr,
        )
        return 0
    if argv and argv[0] == "--list-tools":
        print(json.dumps(mcp_tool_list(), indent=2))
        return 0
    if argv and argv[0] == "--list-resources":
        print(json.dumps(mcp_resource_list(), indent=2))
        return 0
    run_stdio()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
