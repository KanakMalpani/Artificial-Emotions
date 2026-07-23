"""Shared tool schemas for MCP, OpenAI function-calling, and HTTP agents.

Keep these definitions in one place so Cursor / Claude Desktop / Copilot /
custom agents all see the same contract.
"""

from __future__ import annotations

import json
from typing import Any, Callable

from artificial_curiosity.models import (
    CuriosityConfig,
    Domain,
    VALUE_PROFILE_PRESETS,
    ValueProfile,
    list_profile_names,
    resolve_value_profile,
)
from artificial_curiosity.pipeline import CuriosityEngine
from artificial_curiosity.provoke import provoke

# ---------------------------------------------------------------------------
# JSON Schema fragments (OpenAI `parameters` / MCP `inputSchema`)
# ---------------------------------------------------------------------------

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
            "description": "Ground gaps via OpenAlex (no API key required)",
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


def _parse_value_profile(
    raw: Any,
    *,
    profile_name: str | None = None,
) -> ValueProfile:
    return resolve_value_profile(raw, profile_name=profile_name)


def handle_provoke_curiosity(
    *,
    domain: str = "ai",
    topic: str = "",
    n: int = 5,
    fast: bool = True,
    use_llm: bool = False,
    value_profile: Any = None,
    profile_name: str | None = None,
    judge_model: str | None = None,
    diversity_backend: str = "jaccard",
    **_extra: Any,
) -> dict[str, Any]:
    """Instant ranked unknowns + inject pack for any model."""
    return provoke(
        domain=domain,
        topic=topic,
        n=int(n),
        fast=bool(fast),
        use_llm=bool(use_llm),
        value_profile=_parse_value_profile(value_profile) if value_profile else None,
        profile_name=profile_name,
        judge_model=judge_model,
        diversity_backend=diversity_backend,
    )


def handle_rank_unknowns(
    *,
    domain: str = "ai",
    topic: str = "",
    n_return: int = 8,
    n_candidates: int = 16,
    use_literature: bool = True,
    use_llm: bool = False,
    value_profile: Any = None,
    profile_name: str | None = None,
    judge_model: str | None = None,
    diversity_backend: str = "jaccard",
    **_extra: Any,
) -> dict[str, Any]:
    """Full curiosity pipeline: generate → verify → score → diversify → brief."""
    profile = _parse_value_profile(value_profile, profile_name=profile_name)
    config = CuriosityConfig(
        domain=domain,
        topic=topic,
        n_return=int(n_return),
        n_candidates=int(n_candidates),
        use_llm=bool(use_llm),
        use_literature=bool(use_literature),
        value_profile=profile,
        judge_model=judge_model,
        diversity_backend=diversity_backend
        if diversity_backend in ("jaccard", "embedding")
        else "jaccard",
    )
    results = CuriosityEngine(config).run_dict()
    return {
        "headline": "What should we investigate next?",
        "capability": (
            "Curiosity layer: ranked unanswered questions — not Q&A, "
            "not lab automation, not value-free ranking."
        ),
        "domain": domain,
        "topic": topic,
        "count": len(results),
        "mode": "literature" if use_literature else "offline",
        "value_profile": config.value_profile.model_dump(mode="json"),
        "questions": results,
        "note": (
            "Scores are decision aids with explicit ValueProfile weights — "
            "not oracles. Related literature ≠ answered."
        ),
    }


def handle_list_domains(**_extra: Any) -> dict[str, Any]:
    return {
        "domains": list(_DOMAIN_ENUM),
        "note": "Pass any of these as the `domain` argument to other tools.",
    }


def handle_list_profiles(**_extra: Any) -> dict[str, Any]:
    return {
        "presets": [
            {
                "name": name,
                "description": p.description,
                "time_horizon_years": p.time_horizon_years,
            }
            for name, p in sorted(VALUE_PROFILE_PRESETS.items())
        ],
        "note": (
            "Pass profile_name to provoke_curiosity / rank_unknowns. "
            "There is no value-free / neutral ranking mode."
        ),
    }


# Canonical tool registry: name → (description, schema, handler)
# Aliases (spark / run_curiosity) share handlers with primary names.
ToolHandler = Callable[..., dict[str, Any]]

TOOL_SPECS: list[dict[str, Any]] = [
    {
        "name": "provoke_curiosity",
        "description": (
            "Curiosity spark (NOT Q&A): ranked *unanswered* questions plus an "
            "`inject` pack for any model. Uses an explicit ValueProfile — rankings "
            "are never value-free. Default is fast (no network). Alias: spark."
        ),
        "input_schema": PROVOKE_SCHEMA,
        "handler": handle_provoke_curiosity,
    },
    {
        "name": "spark",
        "description": (
            "Alias of provoke_curiosity — instant ranked unknowns + inject pack."
        ),
        "input_schema": PROVOKE_SCHEMA,
        "handler": handle_provoke_curiosity,
    },
    {
        "name": "rank_unknowns",
        "description": (
            "Full Artificial Curiosity pipeline: generate candidates, optionally "
            "verify gaps in OpenAlex, multi-axis score with an explicit "
            "ValueProfile, diversify, and return investigation briefs. "
            "Alias: run_curiosity. Scores are decision aids, not oracles."
        ),
        "input_schema": RANK_SCHEMA,
        "handler": handle_rank_unknowns,
    },
    {
        "name": "run_curiosity",
        "description": "Alias of rank_unknowns — full curiosity ranking pipeline.",
        "input_schema": RANK_SCHEMA,
        "handler": handle_rank_unknowns,
    },
    {
        "name": "list_domains",
        "description": "List supported research domains for curiosity tools.",
        "input_schema": LIST_DOMAINS_SCHEMA,
        "handler": handle_list_domains,
    },
    {
        "name": "list_profiles",
        "description": (
            "List named ValueProfile presets (funder_10y, alignment_lab, …). "
            "Rankings are never value-free."
        ),
        "input_schema": LIST_PROFILES_SCHEMA,
        "handler": handle_list_profiles,
    },
]

HANDLERS: dict[str, ToolHandler] = {t["name"]: t["handler"] for t in TOOL_SPECS}


def mcp_tool_list() -> list[dict[str, Any]]:
    """MCP `tools/list` payload (name, description, inputSchema)."""
    return [
        {
            "name": t["name"],
            "description": t["description"],
            "inputSchema": t["input_schema"],
        }
        for t in TOOL_SPECS
    ]


def openai_tools() -> list[dict[str, Any]]:
    """OpenAI / compatible function-calling tool definitions."""
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["input_schema"],
            },
        }
        for t in TOOL_SPECS
    ]


def dispatch_tool(name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    """Run a registered tool by name. Raises KeyError if unknown."""
    handler = HANDLERS[name]
    return handler(**(arguments or {}))


def tools_as_json() -> str:
    return json.dumps(openai_tools(), indent=2)
