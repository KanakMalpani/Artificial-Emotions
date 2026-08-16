"""UTC clock and ISO-8601 parse helpers.

Shared by mood carryover, scars, persistent memory, preference-event
stamps, and surprise-worksheet ``logged_at`` so decay math does not fork.
Missing / unparseable stamps return ``None`` — callers treat that as fresh
(decay factor 1.0). Audit JSONL ``ts`` stays Z-strftime, not this helper.
"""

from __future__ import annotations

from datetime import UTC, datetime

__all__ = ["parse_iso", "utc_now", "utc_now_iso"]


def utc_now() -> datetime:
    """Timezone-aware UTC now."""
    return datetime.now(UTC)


def utc_now_iso() -> str:
    """ISO-8601 UTC timestamp (``datetime.isoformat``)."""
    return utc_now().isoformat()


def parse_iso(stamp: str | None) -> datetime | None:
    """Parse an ISO-8601 stamp to UTC, or ``None`` if missing/unparseable."""
    if not stamp:
        return None
    text = str(stamp).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)
