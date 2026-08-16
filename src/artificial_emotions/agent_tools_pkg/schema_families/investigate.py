"""Investigate-family tool schemas: critique, decompose, explore."""

from __future__ import annotations

from typing import Any

from artificial_emotions.agent_tools_pkg.schema_families.common import (
    _DOMAIN_ENUM,
    _PROFILE_ENUM,
)

CRITIQUE_BRIEF_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "question": {"type": "string", "default": ""},
        "operationalization": {"type": "string", "default": ""},
        "brief": {"type": "string", "default": ""},
        "why_it_matters": {"type": "string", "default": ""},
    },
    "additionalProperties": False,
}

DECOMPOSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "question": {
            "type": "string",
            "description": "The unknown to open up. Required.",
        },
        "operationalization": {
            "type": "string",
            "default": "",
            "description": "How you would know it was answered. Numeric criteria here become falsifiers.",
        },
        "domain": {"type": "string", "enum": _DOMAIN_ENUM, "default": "ai"},
        "depth": {
            "type": "integer",
            "minimum": 1,
            "maximum": 3,
            "default": 1,
            "description": "1 = one layer of sub-questions; 2-3 also split mechanism and confound.",
        },
        "answerability": {"type": "number", "minimum": 0, "maximum": 1},
        "tractability": {"type": "number", "minimum": 0, "maximum": 1},
        "risk": {"type": "number", "minimum": 0, "maximum": 1},
    },
    "required": ["question"],
    "additionalProperties": False,
}


EXPLORE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "domain": {"type": "string", "enum": _DOMAIN_ENUM, "default": "ai"},
        "topic": {"type": "string", "default": ""},
        "steps": {"type": "integer", "minimum": 1, "maximum": 12, "default": 5},
        "n_return": {"type": "integer", "minimum": 1, "maximum": 16, "default": 5},
        "profile_name": {"type": "string", "enum": _PROFILE_ENUM},
        "use_literature": {"type": "boolean", "default": False},
        "allow_weight_deltas": {
            "type": "boolean",
            "default": False,
            "description": "Let affect nudge ValueProfile weights (bounded, logged).",
        },
        "somatic_modulate": {
            "type": "boolean",
            "default": False,
            "description": (
                "Let high-coercion affect (fear, anger, disgust, joy, sadness) "
                "change search knobs. Off by default; those ids still appraise "
                "and surface. Never raises the risk ceiling."
            ),
        },
        "allow_domain_jump": {"type": "boolean", "default": True},
        "decompose_depth": {"type": "integer", "minimum": 1, "maximum": 3, "default": 1},
    },
    "additionalProperties": False,
}

__all__ = [
    "CRITIQUE_BRIEF_SCHEMA",
    "DECOMPOSE_SCHEMA",
    "EXPLORE_SCHEMA",
]
