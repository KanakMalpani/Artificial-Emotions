"""Export a ranked unknowns set as a JSON document.

v1 delivery is a file (CLI ``--out``) or the HTTP/CLI JSON body. Arbitrary
webhook URLs are not accepted (SSRF). Does not re-rank: pipeline output is
reused as-is.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from artificial_emotions.models import RankedQuestion

FORMAT_ID = "artificial_emotions.ranked_unknowns"
FORMAT_VERSION = 1

DELIVERY_STDOUT = "stdout"
DELIVERY_FILE = "file"
DELIVERY_HTTP_BODY = "http_body"
_DELIVERIES = frozenset({DELIVERY_STDOUT, DELIVERY_FILE, DELIVERY_HTTP_BODY})

WEBHOOK_KEYS = ("webhook_url", "callback_url", "notify_url", "hook_url")

HONESTY = (
    "File export is the v1 path. Arbitrary webhook URLs are not accepted (SSRF). "
    "Scores are decision aids with an explicit ValueProfile — not oracles. "
    "Related literature ≠ answered. This document does not re-rank."
)

__all__ = [
    "DELIVERY_FILE",
    "DELIVERY_HTTP_BODY",
    "DELIVERY_STDOUT",
    "FORMAT_ID",
    "FORMAT_VERSION",
    "HONESTY",
    "WEBHOOK_KEYS",
    "coerce_ranked_questions",
    "export_unknowns",
    "reject_webhook_fields",
    "write_unknowns_export",
]


def reject_webhook_fields(payload: Mapping[str, Any] | None) -> None:
    """Fail closed if a caller tries to push the document to a URL."""
    if not payload:
        return
    for key in WEBHOOK_KEYS:
        val = payload.get(key)
        if val not in (None, "", False):
            raise ValueError(
                "Webhook URLs are not supported (SSRF). "
                "File export is the v1 path; return or write the JSON document instead."
            )


def coerce_ranked_questions(raw: Any) -> list[Any]:
    """Accept ``run --json`` lists, HTTP run envelopes, or a prior export."""
    if isinstance(raw, list):
        return list(raw)
    if isinstance(raw, Mapping):
        for key in ("questions", "unknowns"):
            value = raw.get(key)
            if isinstance(value, list):
                return list(value)
    raise ValueError(
        "Expected a ranked-question list, or an object with a questions array "
        "(reuse pipeline / provoke output)."
    )


def _as_question_dict(item: RankedQuestion | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(item, RankedQuestion):
        return item.model_dump(mode="json")
    if isinstance(item, Mapping):
        return dict(item)
    raise ValueError("Each ranked unknown must be a RankedQuestion or object")


def _has_question_text(row: Mapping[str, Any]) -> bool:
    q = row.get("question")
    if isinstance(q, str) and q.strip():
        return True
    if isinstance(q, Mapping):
        text = q.get("question")
        return isinstance(text, str) and bool(text.strip())
    return False


def export_unknowns(
    questions: Sequence[RankedQuestion | Mapping[str, Any]],
    *,
    domain: str = "",
    topic: str = "",
    profile_name: str | None = None,
    value_profile: Mapping[str, Any] | None = None,
    literature_backend: str = "none",
    delivery: str = DELIVERY_STDOUT,
) -> dict[str, Any]:
    """Wrap pipeline output in a stable interop document. Does not re-rank."""
    from artificial_emotions import __version__

    if delivery not in _DELIVERIES:
        raise ValueError(f"delivery must be one of {sorted(_DELIVERIES)}, got {delivery!r}")
    rows = [_as_question_dict(item) for item in questions]
    if not rows:
        raise ValueError("questions must contain at least one ranked unknown")
    for i, row in enumerate(rows):
        if not _has_question_text(row):
            raise ValueError(f"questions[{i}] is missing question text")

    profile = dict(value_profile) if isinstance(value_profile, Mapping) else None
    return {
        "format": FORMAT_ID,
        "format_version": FORMAT_VERSION,
        "package_version": __version__,
        "kind": "ranked_unknowns",
        "delivery": delivery,
        "webhooks": False,
        "changes_ranks": False,
        "count": len(rows),
        "domain": domain,
        "topic": topic,
        "profile_name": profile_name,
        "value_profile": profile,
        "literature_backend": literature_backend,
        "questions": rows,
        "honesty": HONESTY,
    }


def write_unknowns_export(document: Mapping[str, Any], path: str | Path) -> Path:
    """Write the export document to a local file (CLI v1 path)."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(dict(document), indent=2, ensure_ascii=False)
    target.write_text(text + "\n", encoding="utf-8")
    return target
