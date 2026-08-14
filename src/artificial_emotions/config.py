"""Central environment / runtime configuration.

All public env knobs live here so operators and agents have one place to look.
Sensitive values are never logged.

Env reference (see also ``.env.example``)::

    LLM_API_KEY / OPENAI_API_KEY
    LLM_BASE_URL / OPENAI_BASE_URL
    LLM_MODEL / OPENAI_MODEL
    LLM_JUDGE_MODEL / LLM_JUDGE_MODELS
    LLM_JSON_MODE
    LLM_TIMEOUT_S          — chat completion timeout (default 90)
    CURIOSITY_API_KEY / ARTIFICIAL_CURIOSITY_API_KEY / CURIOSITY_API_KEYS
    CURIOSITY_CORS_ORIGINS — comma list; default empty (deny). Opt-in e.g. http://127.0.0.1:3000
    CURIOSITY_API_RATE_LIMIT_PER_MINUTE — HTTP soft limit per client host (default 60; 0 disables)
    CURIOSITY_API_QUOTA_REQUESTS — per-key HTTP budget (unset/0 = no quota, local DX)
    CURIOSITY_API_QUOTA_WINDOW_S — quota sliding window seconds (default 86400; ignored when quota off)
    CURIOSITY_AUDIT_LOG — opt-in JSONL path (HTTP/MCP names + status; default off; never bodies)
    CURIOSITY_HOST / CURIOSITY_PORT — serve defaults
    CURIOSITY_MCP_TIER     — MCP tool tier (core|investigate|affect|research|full)
    CURIOSITY_NO_MEMORY    — set to 1 to disable PersistentMemory read/write
    CURIOSITY_MEMORY_PATH  — optional override for ~/.artificial_emotions/memory.json
    CURIOSITY_TEMPERAMENT_PATH — optional override for ~/.artificial_emotions/temperament.toml
    OPENALEX_MAILTO
    S2_API_KEY / SEMANTIC_SCHOLAR_API_KEY
    LITERATURE_TIMEOUT_S   — literature HTTP timeout (default 12)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


def _env(name: str, default: str = "") -> str:
    return (os.environ.get(name) or default).strip()


def _env_float(name: str, default: float) -> float:
    raw = _env(name)
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    raw = _env(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def configured_api_keys() -> set[str]:
    """Opt-in HTTP API keys. Empty → auth disabled (local demos)."""
    keys: set[str] = set()
    for name in ("CURIOSITY_API_KEY", "ARTIFICIAL_CURIOSITY_API_KEY"):
        v = _env(name)
        if v:
            keys.add(v)
    multi = _env("CURIOSITY_API_KEYS")
    if multi:
        keys.update(k.strip() for k in multi.split(",") if k.strip())
    return keys


def cors_origins() -> list[str]:
    """CORS allow list. Default empty (deny). Opt-in via ``CURIOSITY_CORS_ORIGINS``."""
    raw = _env("CURIOSITY_CORS_ORIGINS", "")
    if not raw:
        return []
    if raw == "*":
        return ["*"]
    return [o.strip() for o in raw.split(",") if o.strip()]


def api_rate_limit_per_minute() -> int:
    """Per-client HTTP requests per 60s window. ``0`` disables. Default 60."""
    return max(0, _env_int("CURIOSITY_API_RATE_LIMIT_PER_MINUTE", 60))


def audit_log_path() -> str | None:
    """Opt-in JSONL path for HTTP/MCP name+status audit. Unset/empty → off."""
    raw = _env("CURIOSITY_AUDIT_LOG")
    return raw or None


def api_quota_requests() -> int:
    """Per-key HTTP request budget. ``0`` / unset disables (local DX unchanged)."""
    return max(0, _env_int("CURIOSITY_API_QUOTA_REQUESTS", 0))


def api_quota_window_s() -> int:
    """Sliding window for ``CURIOSITY_API_QUOTA_REQUESTS``. Default 86400s.

    ``0`` or invalid values fall back to 86400. Ignored when the quota is off.
    """
    raw = max(0, _env_int("CURIOSITY_API_QUOTA_WINDOW_S", 86400))
    return raw if raw > 0 else 86400


@dataclass(frozen=True)
class AppConfig:
    """Resolved runtime settings (non-secret summary safe to expose in /health)."""

    api_keys_configured: bool = False
    cors_origins: tuple[str, ...] = ()
    api_rate_limit_per_minute: int = 60
    api_quota_requests: int = 0
    api_quota_window_s: int = 86400
    audit_log_enabled: bool = False
    host: str = "127.0.0.1"
    port: int = 8000
    llm_timeout_s: float = 90.0
    literature_timeout_s: float = 12.0
    openalex_mailto: str = "curiosity@localhost"
    s2_configured: bool = False
    version: str = "1.0.0"  # mirrored from package __version__ via get_config()

    @property
    def api_auth_required(self) -> bool:
        return self.api_keys_configured


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    """Cached snapshot of env-backed settings. Call ``clear_config_cache`` in tests."""
    from artificial_emotions import __version__

    keys = configured_api_keys()
    return AppConfig(
        api_keys_configured=bool(keys),
        cors_origins=tuple(cors_origins()),
        api_rate_limit_per_minute=api_rate_limit_per_minute(),
        api_quota_requests=api_quota_requests(),
        api_quota_window_s=api_quota_window_s(),
        audit_log_enabled=bool(audit_log_path()),
        host=_env("CURIOSITY_HOST", "127.0.0.1") or "127.0.0.1",
        port=int(_env_float("CURIOSITY_PORT", 8000)),
        llm_timeout_s=_env_float("LLM_TIMEOUT_S", 90.0),
        literature_timeout_s=_env_float("LITERATURE_TIMEOUT_S", 12.0),
        openalex_mailto=_env("OPENALEX_MAILTO", "curiosity@localhost") or "curiosity@localhost",
        s2_configured=bool(_env("S2_API_KEY") or _env("SEMANTIC_SCHOLAR_API_KEY")),
        version=__version__,
    )


def clear_config_cache() -> None:
    """Drop cached config (tests that mutate env)."""
    get_config.cache_clear()


def llm_timeout_s() -> float:
    return get_config().llm_timeout_s


def literature_timeout_s() -> float:
    return get_config().literature_timeout_s


__all__ = [
    "AppConfig",
    "api_quota_requests",
    "api_quota_window_s",
    "api_rate_limit_per_minute",
    "audit_log_path",
    "clear_config_cache",
    "configured_api_keys",
    "cors_origins",
    "get_config",
    "llm_timeout_s",
    "literature_timeout_s",
]
