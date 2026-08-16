"""Imagination-quarantine tool schemas — ranked twins plus corpus-gated transfer."""

from __future__ import annotations

from typing import Any

from artificial_emotions.agent_tools_pkg.schema_families.common import (
    _DOMAIN_ENUM,
    _PROFILE_ENUM,
)

LIST_IMAGINATION_KINDS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {},
    "additionalProperties": False,
}

APPLY_IMAGINATION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "kind": {
            "type": "string",
            "enum": [
                "premortem",
                "harm_scenario",
                "rehearsal",
                "eulogy",
                "reformulation",
                "counterfactual",
            ],
            "description": (
                "Which generative twin to run. Outputs are quarantined imagined "
                "content — not ranked findings. Use imagine_transfer for corpus-gated "
                "transfer (not this tool)."
            ),
        },
        "domain": {"type": "string", "enum": _DOMAIN_ENUM, "default": "ai"},
        "topic": {"type": "string", "default": ""},
        "n_return": {"type": "integer", "minimum": 1, "maximum": 16, "default": 6},
        "profile_name": {"type": "string", "enum": _PROFILE_ENUM},
        "use_literature": {
            "type": "boolean",
            "default": False,
            "description": "Literature for the ranking step only; generators stay offline.",
        },
    },
    "required": ["kind"],
    "additionalProperties": False,
}

IMAGINE_TRANSFER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "seed": {
            "type": "string",
            "minLength": 1,
            "description": "Seed concept A for structural analogy (corpus-gated transfer).",
        },
        "corpus": {
            "description": (
                "Local corpus: filesystem path to JSON, or an inline list of "
                "{year, title, concepts} documents. Never ranked injection."
            ),
            "oneOf": [
                {"type": "string", "minLength": 1},
                {
                    "type": "array",
                    "minItems": 1,
                    "items": {"type": "object"},
                },
            ],
        },
        "max_bridges": {
            "type": "integer",
            "minimum": 1,
            "maximum": 16,
            "default": 4,
        },
        "max_links": {
            "type": "integer",
            "minimum": 1,
            "maximum": 32,
            "default": 8,
        },
    },
    "required": ["seed", "corpus"],
    "additionalProperties": False,
}

__all__ = [
    "APPLY_IMAGINATION_SCHEMA",
    "IMAGINE_TRANSFER_SCHEMA",
    "LIST_IMAGINATION_KINDS_SCHEMA",
]
