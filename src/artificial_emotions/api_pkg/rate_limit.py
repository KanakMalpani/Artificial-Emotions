"""In-process sliding-window rate limit keyed by client host.

A local soft guard for ``emotions serve`` — not a distributed WAF. Limits are
per process; multi-instance deployments need an external limiter.
"""

from __future__ import annotations

import math
import threading
import time
from collections import defaultdict, deque

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from artificial_emotions.config import api_rate_limit_per_minute
from artificial_emotions.errors import ERR_RATE_LIMITED, error_payload

__all__ = ["RateLimitMiddleware"]

_WINDOW_S = 60.0


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Reject excess requests from the same client host with 429 + Retry-After."""

    def __init__(
        self,
        app,
        *,
        limit: int | None = None,
        window_s: float = _WINDOW_S,
    ) -> None:
        super().__init__(app)
        self._limit = api_rate_limit_per_minute() if limit is None else int(limit)
        self._window_s = float(window_s)
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    async def dispatch(self, request: Request, call_next):
        if self._limit <= 0:
            return await call_next(request)

        host = request.client.host if request.client else "unknown"
        now = time.monotonic()
        with self._lock:
            q = self._hits[host]
            cutoff = now - self._window_s
            while q and q[0] <= cutoff:
                q.popleft()
            if len(q) >= self._limit:
                retry_after = max(1, math.ceil(self._window_s - (now - q[0])))
                return JSONResponse(
                    status_code=429,
                    headers={"Retry-After": str(retry_after)},
                    content=error_payload(
                        ERR_RATE_LIMITED,
                        (
                            f"Rate limit exceeded ({self._limit} requests per "
                            f"{int(self._window_s)}s). Retry after "
                            f"{retry_after}s, or set "
                            "CURIOSITY_API_RATE_LIMIT_PER_MINUTE=0 to disable."
                        ),
                        details={
                            "limit": self._limit,
                            "window_s": int(self._window_s),
                            "retry_after": retry_after,
                        },
                    ),
                )
            q.append(now)

        return await call_next(request)
