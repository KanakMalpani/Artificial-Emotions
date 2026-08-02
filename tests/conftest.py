"""Pytest defaults for the suite.

The HTTP API enables an in-process rate limit by default (60/min). The shared
``artificial_emotions.api:app`` would otherwise accumulate TestClient hits and
fail unrelated API tests with 429. Security tests that need a limiter set
``CURIOSITY_API_RATE_LIMIT_PER_MINUTE`` explicitly and call ``create_app()``.
"""

from __future__ import annotations

import os

os.environ.setdefault("CURIOSITY_API_RATE_LIMIT_PER_MINUTE", "0")
