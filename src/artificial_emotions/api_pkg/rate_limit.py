"""In-process sliding-window rate limit and optional per-key quota.

A local soft guard for ``emotions serve`` — not a distributed WAF. Limits are
per process; multi-instance deployments need an external limiter.

Rate limit (``CURIOSITY_API_RATE_LIMIT_PER_MINUTE``) is keyed by client host.
Quota (``CURIOSITY_API_QUOTA_REQUESTS``) is keyed by a matched API key. Unset
quota keeps the current local DX (no per-key budget).
"""

from __future__ import annotations

import hashlib
import math
import threading
import time
from collections import defaultdict, deque

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from artificial_emotions.api_pkg.security import (
    is_auth_open_path,
    matching_configured_key,
    provided_api_key,
)
from artificial_emotions.config import (
    api_quota_requests,
    api_quota_window_s,
    api_rate_limit_per_minute,
    configured_api_keys,
)
from artificial_emotions.errors import ERR_QUOTA_EXCEEDED, ERR_RATE_LIMITED, error_payload

__all__ = ["RateLimitMiddleware"]

_WINDOW_S = 60.0
_QUOTA_BUCKET_PREFIX = b"curiosity-quota:"


def _quota_bucket(api_key: str) -> str:
    """Stable in-process bucket id — never store the raw key."""
    return hashlib.sha256(_QUOTA_BUCKET_PREFIX + api_key.encode("utf-8")).hexdigest()


def _retry_if_limited(
    hits: dict[str, deque[float]],
    bucket: str,
    now: float,
    window_s: float,
    limit: int,
) -> int | None:
    """Prune ``bucket`` and return Retry-After seconds if it is already at ``limit``."""
    q = hits[bucket]
    cutoff = now - window_s
    while q and q[0] <= cutoff:
        q.popleft()
    if len(q) >= limit:
        return max(1, math.ceil(window_s - (now - q[0])))
    return None


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Reject excess host bursts (429 ``rate_limited``) and per-key budgets (429 ``quota_exceeded``)."""

    def __init__(
        self,
        app,
        *,
        limit: int | None = None,
        window_s: float = _WINDOW_S,
        quota_requests: int | None = None,
        quota_window_s: float | None = None,
    ) -> None:
        super().__init__(app)
        self._limit = api_rate_limit_per_minute() if limit is None else int(limit)
        self._window_s = float(window_s)
        self._quota_requests = (
            api_quota_requests() if quota_requests is None else max(0, int(quota_requests))
        )
        self._quota_window_s = float(
            api_quota_window_s() if quota_window_s is None else quota_window_s
        )
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._quota_hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _limited_response(
        self,
        *,
        code: str,
        message: str,
        limit: int,
        window_s: float,
        retry_after: int,
        scope: str,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=429,
            headers={"Retry-After": str(retry_after)},
            content=error_payload(
                code,
                message,
                details={
                    "limit": limit,
                    "window_s": int(window_s),
                    "retry_after": retry_after,
                    "scope": scope,
                },
            ),
        )

    async def dispatch(self, request: Request, call_next):
        # Match auth open list: probes and docs must stay reachable under load.
        if is_auth_open_path(request.url.path):
            return await call_next(request)

        rate_on = self._limit > 0
        quota_on = self._quota_requests > 0
        if not rate_on and not quota_on:
            return await call_next(request)

        matched_key: str | None = None
        if quota_on:
            keys = configured_api_keys()
            if keys:
                matched_key = matching_configured_key(provided_api_key(request), keys)

        host = request.client.host if request.client else "unknown"
        now = time.monotonic()
        with self._lock:
            if rate_on:
                retry_after = _retry_if_limited(self._hits, host, now, self._window_s, self._limit)
                if retry_after is not None:
                    return self._limited_response(
                        code=ERR_RATE_LIMITED,
                        message=(
                            f"Rate limit exceeded ({self._limit} requests per "
                            f"{int(self._window_s)}s). Retry after "
                            f"{retry_after}s, or set "
                            "CURIOSITY_API_RATE_LIMIT_PER_MINUTE=0 to disable."
                        ),
                        limit=self._limit,
                        window_s=self._window_s,
                        retry_after=retry_after,
                        scope="client_host",
                    )
            if matched_key is not None:
                bucket = _quota_bucket(matched_key)
                retry_after = _retry_if_limited(
                    self._quota_hits,
                    bucket,
                    now,
                    self._quota_window_s,
                    self._quota_requests,
                )
                if retry_after is not None:
                    return self._limited_response(
                        code=ERR_QUOTA_EXCEEDED,
                        message=(
                            f"Per-key quota exceeded ({self._quota_requests} requests per "
                            f"{int(self._quota_window_s)}s). Retry after "
                            f"{retry_after}s, or unset CURIOSITY_API_QUOTA_REQUESTS "
                            "to disable."
                        ),
                        limit=self._quota_requests,
                        window_s=self._quota_window_s,
                        retry_after=retry_after,
                        scope="api_key",
                    )
            if rate_on:
                self._hits[host].append(now)
            if matched_key is not None:
                self._quota_hits[_quota_bucket(matched_key)].append(now)

        return await call_next(request)
