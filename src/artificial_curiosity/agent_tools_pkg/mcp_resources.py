"""MCP resource list / read (`curiosity://…`)."""

from __future__ import annotations

import json
from typing import Any

from artificial_curiosity.agent_tools_pkg.handlers import (
    handle_list_domains,
    handle_list_epistemic_cues,
    handle_list_profiles,
)

# ---------------------------------------------------------------------------
# MCP resources (WO-0.3.7): domains, presets, LIMITS snippet
# ---------------------------------------------------------------------------

_LIMITS_SNIPPET = (
    "Scores are decision aids with explicit ValueProfile weights — not oracles. "
    "Related literature ≠ answered. Gap reading is phrase/overlap (optional grounded "
    "LLM reader). Dual-use uses weighted_heuristic_v1 — residual risk remains. "
    "Default literature backend: OpenAlex; Semantic Scholar optional. "
    "Offline demos work without LLM keys. See docs/LIMITS.md."
)


def mcp_resource_list() -> list[dict[str, Any]]:
    return [
        {
            "uri": "curiosity://domains",
            "name": "domains",
            "description": "Supported research domains",
            "mimeType": "application/json",
        },
        {
            "uri": "curiosity://profiles",
            "name": "profiles",
            "description": "Named ValueProfile presets (never value-free)",
            "mimeType": "application/json",
        },
        {
            "uri": "curiosity://limits",
            "name": "limits",
            "description": "Honesty bounds / confidence caps (snippet)",
            "mimeType": "text/plain",
        },
        {
            "uri": "curiosity://emotions",
            "name": "emotions",
            "description": "Epistemic cue catalog (annotation only — does not feel)",
            "mimeType": "application/json",
        },
    ]


def mcp_resource_read(uri: str) -> dict[str, Any]:
    if uri == "curiosity://domains":
        text = json.dumps(handle_list_domains(), indent=2)
    elif uri == "curiosity://profiles":
        text = json.dumps(handle_list_profiles(), indent=2)
    elif uri == "curiosity://limits":
        text = _LIMITS_SNIPPET
    elif uri == "curiosity://emotions":
        text = json.dumps(handle_list_epistemic_cues(), indent=2)
    else:
        raise KeyError(uri)
    return {
        "contents": [
            {
                "uri": uri,
                "mimeType": "application/json" if uri != "curiosity://limits" else "text/plain",
                "text": text,
            }
        ]
    }
