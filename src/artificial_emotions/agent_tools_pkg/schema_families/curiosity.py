"""Core ranking and profile tool schemas: provoke, rank, list, compare."""

from __future__ import annotations

from typing import Any

from artificial_emotions.agent_tools_pkg.schema_families.common import (
    _DOMAIN_ENUM,
    _PROFILE_ENUM,
    _VALUE_PROFILE_SCHEMA,
)

PROVOKE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "domain": {
            "type": "string",
            "enum": _DOMAIN_ENUM,
            "default": "ai",
            "description": "Scientific / research domain",
        },
        "topic": {
            "type": "string",
            "default": "",
            "description": "Optional topic focus within the domain",
        },
        "n": {
            "type": "integer",
            "minimum": 1,
            "maximum": 16,
            "default": 5,
            "description": "How many ranked unknowns to return",
        },
        "fast": {
            "type": "boolean",
            "default": True,
            "description": (
                "If true (default), skip OpenAlex for an instant local spark. "
                "Set false for literature-grounded gap checks."
            ),
        },
        "use_llm": {
            "type": "boolean",
            "default": False,
            "description": "Use configured OpenAI-compatible LLM if available",
        },
        "profile_name": {
            "type": "string",
            "enum": _PROFILE_ENUM,
            "description": "Named ValueProfile preset (F11). Prefer over inventing weights.",
        },
        "value_profile": _VALUE_PROFILE_SCHEMA,
        "judge_model": {
            "type": "string",
            "description": "Optional judge/gap-reader model distinct from generator",
        },
        "diversity_backend": {
            "type": "string",
            "enum": ["jaccard", "embedding"],
            "default": "jaccard",
            "description": "Near-dup backend; embedding needs optional extras",
        },
    },
    "additionalProperties": False,
}

RANK_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "domain": {
            "type": "string",
            "enum": _DOMAIN_ENUM,
            "default": "ai",
        },
        "topic": {"type": "string", "default": ""},
        "n_return": {
            "type": "integer",
            "minimum": 1,
            "maximum": 32,
            "default": 8,
        },
        "n_candidates": {
            "type": "integer",
            "minimum": 4,
            "maximum": 64,
            "default": 16,
        },
        "use_literature": {
            "type": "boolean",
            "default": True,
            "description": "Ground gaps via literature adapters (OpenAlex / Semantic Scholar)",
        },
        "literature_backend": {
            "type": "string",
            "enum": ["openalex", "semantic_scholar", "both"],
            "default": "openalex",
            "description": "Literature backend (W11). Offline path ignores this.",
        },
        "use_llm": {
            "type": "boolean",
            "default": False,
        },
        "profile_name": {
            "type": "string",
            "enum": _PROFILE_ENUM,
        },
        "value_profile": _VALUE_PROFILE_SCHEMA,
        "judge_model": {"type": "string"},
        "judge_ensemble_n": {
            "type": "integer",
            "minimum": 1,
            "maximum": 5,
            "default": 1,
            "description": "Multi-judge ensemble size; disagreement widens bands (W15)",
        },
        "diversity_backend": {
            "type": "string",
            "enum": ["jaccard", "embedding"],
            "default": "jaccard",
        },
    },
    "additionalProperties": False,
}

LIST_DOMAINS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {},
    "additionalProperties": False,
}

LIST_PROFILES_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {},
    "additionalProperties": False,
}

COMPARE_PROFILES_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "domain": {
            "type": "string",
            "enum": list(_DOMAIN_ENUM),
            "default": "ai",
        },
        "topic": {"type": "string", "default": ""},
        "profile_a": {
            "type": "string",
            "default": "humanity_default",
            "description": "Primary ValueProfile preset name",
        },
        "profile_b": {
            "type": "string",
            "default": "alignment_lab",
            "description": "Comparison ValueProfile preset name",
        },
        "n": {"type": "integer", "minimum": 1, "maximum": 32, "default": 8},
    },
    "additionalProperties": False,
}

CONSTITUTION_COMPARE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "domain": {
            "type": "string",
            "enum": list(_DOMAIN_ENUM),
            "default": "ai",
        },
        "topic": {"type": "string", "default": ""},
        "primary_profile": {
            "type": "string",
            "description": "Override constitution primary profile",
        },
        "veto_profile": {
            "type": "string",
            "description": "Override safety veto profile (e.g. public_demo_strict_risk)",
        },
        "n": {"type": "integer", "minimum": 1, "maximum": 32, "default": 8},
    },
    "additionalProperties": False,
}

__all__ = [
    "COMPARE_PROFILES_SCHEMA",
    "CONSTITUTION_COMPARE_SCHEMA",
    "LIST_DOMAINS_SCHEMA",
    "LIST_PROFILES_SCHEMA",
    "PROVOKE_SCHEMA",
    "RANK_SCHEMA",
]
