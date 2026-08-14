"""HTTP auth middleware and the small helpers it depends on.

Auth is opt-in: with no ``CURIOSITY_API_KEY`` configured the API is open, which
is what local demos want. Once keys exist, everything outside the open list
requires a Bearer token or ``X-API-Key``.
"""

from __future__ import annotations

import posixpath
import secrets
from urllib.parse import unquote, urlparse

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from artificial_emotions.config import configured_api_keys
from artificial_emotions.errors import ERR_AUTH_REQUIRED, error_payload

__all__ = [
    "AUTH_OPEN_PATHS",
    "OptionalApiKeyMiddleware",
    "api_key_matches",
    "is_auth_open_path",
    "matching_configured_key",
    "normalize_request_path",
    "provided_api_key",
    "redact_base_url",
]

AUTH_OPEN_PATHS = frozenset({"/", "/health", "/ready", "/docs", "/openapi.json", "/redoc"})


def normalize_request_path(path: str) -> str:
    """Normalize path for auth open-list checks (decode, collapse ``..`` / ``//``)."""
    raw = unquote(path or "/")
    if not raw.startswith("/"):
        raw = "/" + raw
    norm = posixpath.normpath(raw)
    if not norm.startswith("/"):
        norm = "/" + norm
    return norm


def is_auth_open_path(path: str) -> bool:
    """Exact open paths, plus safe ``/docs/`` and ``/redoc/`` prefixes only."""
    p = normalize_request_path(path)
    if p in AUTH_OPEN_PATHS:
        return True
    # Trailing-slash prefixes avoid ``startswith("/docs")`` matching ``/docsEvil``.
    return p.startswith("/docs/") or p.startswith("/redoc/")


def provided_api_key(request: Request) -> str:
    """Bearer token or ``X-API-Key``; empty if neither is present."""
    auth = request.headers.get("authorization") or ""
    if auth.lower().startswith("bearer "):
        token = auth[7:].strip()
        if token:
            return token
    return (request.headers.get("x-api-key") or "").strip()


def matching_configured_key(provided: str, keys: set[str]) -> str | None:
    """Return the configured key that matches ``provided``, or ``None`` (fail closed)."""
    if not provided or not isinstance(provided, str):
        return None
    for key in keys:
        if not isinstance(key, str):
            continue
        try:
            if secrets.compare_digest(provided, key):
                return key
        except (TypeError, ValueError):
            continue
    return None


def api_key_matches(provided: str, keys: set[str]) -> bool:
    """Constant-time key check; never raises on length/type mismatch (always → fail closed)."""
    return matching_configured_key(provided, keys) is not None


def redact_base_url(url: str | None) -> str | None:
    """Expose scheme only — never leak host/path from unauthenticated ``/health``."""
    if not url:
        return None
    parsed = urlparse(url)
    if parsed.scheme:
        return f"{parsed.scheme}://[redacted]"
    return "[redacted]"


class OptionalApiKeyMiddleware(BaseHTTPMiddleware):
    """When API keys are configured, require Bearer or X-API-Key on protected routes."""

    async def dispatch(self, request: Request, call_next):
        keys = configured_api_keys()
        if not keys:
            return await call_next(request)
        if is_auth_open_path(request.url.path):
            return await call_next(request)
        provided = provided_api_key(request)
        if not api_key_matches(provided, keys):
            return JSONResponse(
                status_code=401,
                content=error_payload(
                    ERR_AUTH_REQUIRED,
                    (
                        "API key required. Set Authorization: Bearer <key> or "
                        "X-API-Key. Local demos: unset CURIOSITY_API_KEY."
                    ),
                ),
            )
        return await call_next(request)
