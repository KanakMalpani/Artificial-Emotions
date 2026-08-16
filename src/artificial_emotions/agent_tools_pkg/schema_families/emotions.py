"""Emotion / epistemic-cue tool schemas."""

from __future__ import annotations

from typing import Any

from artificial_emotions.agent_tools_pkg.schema_families.common import _DOMAIN_ENUM

LIST_EPISTEMIC_CUES_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {},
    "additionalProperties": False,
}

ANNOTATE_EPISTEMIC_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "question": {
            "type": "string",
            "minLength": 12,
            "description": "Question text to annotate with epistemic cue tags",
        },
        "gap_status": {
            "type": "string",
            "enum": [
                "unanswered",
                "partially_answered",
                "likely_answered",
                "unknown_with_caveat",
            ],
            "default": "unanswered",
        },
        "surprise": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "default": 0.5,
        },
        "neglectedness": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "default": 0.5,
        },
        "answerability": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "default": 0.5,
        },
        "notes": {
            "type": "string",
            "default": "",
            "description": "Optional gap notes (e.g. related literature ≠ answered)",
        },
        "domain": {
            "type": "string",
            "enum": _DOMAIN_ENUM,
            "default": "ai",
        },
    },
    "required": ["question"],
    "additionalProperties": False,
}

EMOTION_PACK_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "name": {
            "type": "string",
            "default": "affective_science",
            "description": (
                "Bundled pack id. Default affective_science — ranking seeds for "
                "affective / epistemic research, not an emotion engine."
            ),
        },
    },
    "additionalProperties": False,
}

ELICIT_HELPERS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {},
    "additionalProperties": False,
}

EMOTION_CATALOG_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "family": {
            "type": "string",
            "description": ("Optional filter: epistemic | basic | social | achievement"),
        },
    },
    "additionalProperties": False,
}

MIX_EMOTIONS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "weights": {
            "type": "object",
            "description": (
                "Map emotion_id → percent (e.g. 40) or weight (e.g. 0.4). "
                "Normalized to sum 1.0. Example: "
                '{"curiosity": 40, "confusion": 30, "awe": 30}'
            ),
            "additionalProperties": {"type": "number"},
        },
        "profile_name": {
            "type": "string",
            "description": "Optional ValueProfile for mix_intensity_cap",
        },
        "mix_intensity_cap": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "description": "Override non-epistemic mix mass cap",
        },
        "simulate_feeling": {
            "type": "boolean",
            "description": "Include felt_simulation in response",
        },
    },
    "required": ["weights"],
    "additionalProperties": False,
}

__all__ = [
    "ANNOTATE_EPISTEMIC_SCHEMA",
    "ELICIT_HELPERS_SCHEMA",
    "EMOTION_CATALOG_SCHEMA",
    "EMOTION_PACK_SCHEMA",
    "LIST_EPISTEMIC_CUES_SCHEMA",
    "MIX_EMOTIONS_SCHEMA",
]
