"""Shared JSON Schema pieces: domain/profile enums and ValueProfile object."""

from __future__ import annotations

from typing import Any

from artificial_emotions.models import Domain, list_profile_names

_DOMAIN_ENUM = [d.value for d in Domain]
_PROFILE_ENUM = list_profile_names()

_VALUE_PROFILE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": (
        "Explicit stakeholder values — rankings are never value-free. "
        "Prefer profile_name for named presets; or pass a full object."
    ),
    "properties": {
        "name": {"type": "string"},
        "description": {"type": "string"},
        "weight_impact": {"type": "number", "minimum": 0, "maximum": 3},
        "weight_neglectedness": {"type": "number", "minimum": 0, "maximum": 3},
        "weight_tractability": {"type": "number", "minimum": 0, "maximum": 3},
        "weight_surprise": {"type": "number", "minimum": 0, "maximum": 3},
        "max_risk": {"type": "number", "minimum": 0, "maximum": 1},
        "min_answerability": {"type": "number", "minimum": 0, "maximum": 1},
        "prefer_interdisciplinary": {"type": "boolean"},
        "time_horizon_years": {"type": "integer", "minimum": 1, "maximum": 100},
    },
    "additionalProperties": False,
}

__all__ = ["_DOMAIN_ENUM", "_PROFILE_ENUM", "_VALUE_PROFILE_SCHEMA"]
