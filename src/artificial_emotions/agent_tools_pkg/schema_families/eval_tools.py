"""Eval / export / worksheet tool schemas — display and templates, not re-rank."""

from __future__ import annotations

from typing import Any

from artificial_emotions.agent_tools_pkg.schema_families.common import _PROFILE_ENUM

CROSS_MODEL_VOTE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "candidates": {
            "type": "array",
            "minItems": 1,
            "items": {"type": "object"},
            "description": "Candidate unknowns with question / operationalization",
        },
        "judges": {"type": "integer", "minimum": 1, "maximum": 6, "default": 1},
    },
    "required": ["candidates"],
    "additionalProperties": False,
}

VOI_WORKSHEET_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "question_id": {"type": "string", "default": ""},
        "question": {"type": "string", "default": ""},
        "operationalization": {"type": "string", "default": ""},
        "profile_name": {"type": "string", "default": ""},
        "domain": {"type": "string", "default": ""},
    },
    "additionalProperties": False,
}

PREFERENCE_WEIGHT_HINTS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "events": {
            "type": "array",
            "minItems": 1,
            "maxItems": 500,
            "items": {"type": "object"},
            "description": (
                "Inline labeled prefer/reject/outcome events with score_axes. "
                "Filesystem paths are not accepted."
            ),
        },
        "profile_name": {
            "type": "string",
            "enum": _PROFILE_ENUM,
            "description": "Named ValueProfile preset. Rankings are never value-free.",
        },
        "max_delta": {
            "type": "number",
            "minimum": 0.01,
            "maximum": 0.2,
            "default": 0.08,
            "description": "Cap on each axis weight nudge (tiny hints, not calibrated).",
        },
        "apply": {
            "type": "boolean",
            "default": False,
            "description": (
                "If true, return applied_profile (a copy). Default false = preview. "
                "Never overwrites a named preset."
            ),
        },
    },
    "required": ["events"],
    "additionalProperties": False,
}

IDEA_GRAPH_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "candidates": {
            "type": "array",
            "minItems": 1,
            "items": {"type": "object"},
        },
        "similarity_threshold": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "default": 0.28,
        },
    },
    "required": ["candidates"],
    "additionalProperties": False,
}

EXPORT_UNKNOWNS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "questions": {
            "type": "array",
            "minItems": 1,
            "maxItems": 64,
            "items": {"type": "object"},
            "description": (
                "Ranked unknowns from rank_unknowns / POST /v1/curiosity/run. "
                "Reused as-is; this tool does not re-rank."
            ),
        },
        "domain": {"type": "string", "default": ""},
        "topic": {"type": "string", "default": ""},
        "profile_name": {"type": "string"},
        "literature_backend": {"type": "string", "default": "none"},
    },
    "required": ["questions"],
    "additionalProperties": False,
}

SOUNDNESS_PASS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "candidates": {
            "type": "array",
            "minItems": 1,
            "items": {"type": "object"},
            "description": "Top-n unknowns with question / operationalization / brief",
        },
    },
    "required": ["candidates"],
    "additionalProperties": False,
}

SURPRISE_WORKSHEET_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "question_id": {"type": "string"},
        "profile_name": {"type": "string"},
        "predicted_surprise": {"type": "number", "minimum": 0, "maximum": 1},
        "pilot_result": {"type": "string"},
        "belief_shift_1_to_5": {"type": "integer", "minimum": 1, "maximum": 5},
        "crude_update_note": {"type": "string"},
    },
    "additionalProperties": False,
}

__all__ = [
    "CROSS_MODEL_VOTE_SCHEMA",
    "EXPORT_UNKNOWNS_SCHEMA",
    "IDEA_GRAPH_SCHEMA",
    "PREFERENCE_WEIGHT_HINTS_SCHEMA",
    "SOUNDNESS_PASS_SCHEMA",
    "SURPRISE_WORKSHEET_SCHEMA",
    "VOI_WORKSHEET_SCHEMA",
]
