"""Opt-in JSONL audit of HTTP/MCP tool names + status.

Default **off**. Set ``CURIOSITY_AUDIT_LOG`` to a file path to append one JSON
object per line. Records are an allowlist (``ts``, ``channel``, ``name``,
``status``) — never request/response bodies, headers, query strings, or keys.

A local operator log for ``emotions serve`` / ``emotions-mcp``, not a SIEM.
"""

from __future__ import annotations

import json
import threading
from datetime import UTC, datetime
from pathlib import Path

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from artificial_emotions.api_pkg.security import is_auth_open_path, normalize_request_path
from artificial_emotions.config import audit_log_path

__all__ = ["AuditMiddleware", "record_audit"]

_LOCK = threading.Lock()
_NAME_MAX = 256
_CHANNELS = frozenset({"http", "mcp"})
_MCP_STATUS = frozenset({"ok", "error"})


def record_audit(*, channel: str, name: str, status: int | str) -> None:
    """Append one allowlisted JSONL event. No-op when unset or on I/O failure."""
    dest = audit_log_path()
    if not dest:
        return
    if channel not in _CHANNELS:
        return
    name_s = str(name).replace("\n", " ").replace("\r", "").strip()
    if not name_s:
        return
    if len(name_s) > _NAME_MAX:
        name_s = name_s[:_NAME_MAX]
    if isinstance(status, bool) or not isinstance(status, int | str):
        return
    if isinstance(status, int):
        status_out: int | str = status
    elif status in _MCP_STATUS:
        status_out = status
    else:
        return
    event = {
        "ts": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "channel": channel,
        "name": name_s,
        "status": status_out,
    }
    line = json.dumps(event, separators=(",", ":"), ensure_ascii=True) + "\n"
    try:
        path = Path(dest)
        path.parent.mkdir(parents=True, exist_ok=True)
        with _LOCK:
            with path.open("a", encoding="utf-8", newline="\n") as fh:
                fh.write(line)
                fh.flush()
    except OSError:
        return


class AuditMiddleware(BaseHTTPMiddleware):
    """Log HTTP method+path and status when ``CURIOSITY_AUDIT_LOG`` is set.

    Probe/open paths match the auth open list and are skipped. Query strings
    and bodies are never recorded. Outermost so 401/429 still appear.
    """

    async def dispatch(self, request: Request, call_next):
        if not audit_log_path():
            return await call_next(request)
        if is_auth_open_path(request.url.path):
            return await call_next(request)
        path = normalize_request_path(request.url.path)
        name = f"{request.method} {path}"
        try:
            response = await call_next(request)
        except Exception:
            record_audit(channel="http", name=name, status=500)
            raise
        record_audit(channel="http", name=name, status=int(response.status_code))
        return response
