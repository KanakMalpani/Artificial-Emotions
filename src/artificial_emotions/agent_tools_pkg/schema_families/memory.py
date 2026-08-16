"""Persistent-memory and dream-reanalysis tool schemas."""

from __future__ import annotations

from typing import Any

MEMORY_SHOW_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": (
                "Optional path to local memory JSON. Default: "
                "~/.artificial_emotions/memory.json (or CURIOSITY_MEMORY_PATH)."
            ),
        },
    },
    "additionalProperties": False,
}

MEMORY_FORGET_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "what": {
            "type": "string",
            "description": (
                "Session id, question id, or keyword "
                "(sessions|encounters|selections|mood|scars|affinities)."
            ),
        },
        "confirm": {
            "type": "boolean",
            "description": "Must be true — explicit destructive confirm. No silent wipe.",
        },
        "path": {
            "type": "string",
            "description": "Optional memory JSON path override.",
        },
    },
    "required": ["what", "confirm"],
    "additionalProperties": False,
}

MEMORY_RESET_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "confirm": {
            "type": "boolean",
            "description": "Must be true — wipes remembered state and deletes the file.",
        },
        "path": {
            "type": "string",
            "description": "Optional memory JSON path override.",
        },
    },
    "required": ["confirm"],
    "additionalProperties": False,
}

MEMORY_AVOIDING_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": "Optional memory JSON path override.",
        },
        "min_encounters": {
            "type": "integer",
            "minimum": 2,
            "maximum": 100,
            "description": "Minimum encounters before a non-selection counts as a pattern.",
        },
    },
    "additionalProperties": False,
}

DREAM_REANALYZE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": "Optional PersistentMemory JSON path to reanalyze.",
        },
    },
    "additionalProperties": False,
}

__all__ = [
    "DREAM_REANALYZE_SCHEMA",
    "MEMORY_AVOIDING_SCHEMA",
    "MEMORY_FORGET_SCHEMA",
    "MEMORY_RESET_SCHEMA",
    "MEMORY_SHOW_SCHEMA",
]
