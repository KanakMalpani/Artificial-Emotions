"""Stance-view tool schemas — views, never re-rankings."""

from __future__ import annotations

from typing import Any

from artificial_emotions.agent_tools_pkg.schema_families.common import (
    _DOMAIN_ENUM,
    _PROFILE_ENUM,
)

LIST_STANCES_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {},
    "additionalProperties": False,
}

APPLY_STANCE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "stance": {
            "type": "string",
            "enum": ["doubt", "safety", "focus", "close", "taste", "wonder", "survey"],
            "description": "Which question to ask of the ranked set.",
        },
        "domain": {"type": "string", "enum": _DOMAIN_ENUM, "default": "ai"},
        "topic": {"type": "string", "default": ""},
        "n_return": {"type": "integer", "minimum": 1, "maximum": 16, "default": 6},
        "profile_name": {"type": "string", "enum": _PROFILE_ENUM},
        "use_literature": {"type": "boolean", "default": False},
    },
    "required": ["stance"],
    "additionalProperties": False,
}

__all__ = [
    "APPLY_STANCE_SCHEMA",
    "LIST_STANCES_SCHEMA",
]
