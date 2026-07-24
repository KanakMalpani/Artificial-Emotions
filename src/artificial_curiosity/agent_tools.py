"""Shared tool schemas for MCP, OpenAI function-calling, and HTTP agents.

Keep these definitions in one place so Cursor / Claude Desktop / Copilot /
custom agents all see the same contract.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from artificial_curiosity.emotions import (
    annotate_epistemic,
    elicit_helpers,
    emotion_catalog,
    emotion_pack,
    list_epistemic_cues,
    mix_emotions,
)
from artificial_curiosity.models import (
    VALUE_PROFILE_PRESETS,
    CuriosityConfig,
    Domain,
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
    },
    "required": ["weights"],
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
    literature_backend: str = "openalex",
    use_llm: bool = False,
    value_profile: Any = None,
    profile_name: str | None = None,
    judge_model: str | None = None,
    judge_ensemble_n: int = 1,
    diversity_backend: str = "jaccard",
    **_extra: Any,
) -> dict[str, Any]:
    """Full curiosity pipeline: generate → verify → score → diversify → brief."""
    profile = _parse_value_profile(value_profile, profile_name=profile_name)
    backend = (
        literature_backend
        if literature_backend
        in (
            "openalex",
            "semantic_scholar",
            "both",
        )
        else "openalex"
    )
    config = CuriosityConfig(
        domain=domain,
        topic=topic,
        n_return=int(n_return),
        n_candidates=int(n_candidates),
        use_llm=bool(use_llm),
        use_literature=bool(use_literature),
        literature_backend=backend,
        value_profile=profile,
        judge_model=judge_model,
        judge_ensemble_n=int(judge_ensemble_n or 1),
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
        "literature_backend": backend if use_literature else "none",
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


def handle_compare_profiles(
    *,
    domain: str = "ai",
    topic: str = "",
    profile_a: str = "humanity_default",
    profile_b: str = "alignment_lab",
    n: int = 8,
    **_extra: Any,
) -> dict[str, Any]:
    """Side-by-side offline ranks under two ValueProfiles."""
    from artificial_curiosity.compare import compare_profiles

    return compare_profiles(
        domain=domain or "ai",
        topic=topic or "",
        profile_a=profile_a or "humanity_default",
        profile_b=profile_b or "alignment_lab",
        n=int(n or 8),
    )


def handle_critique_brief(
    *,
    question: str = "",
    operationalization: str = "",
    brief: str = "",
    why_it_matters: str = "",
    **_extra: Any,
) -> dict[str, Any]:
    """Form-only brief critic — does not change ranks."""
    from artificial_curiosity.critique import critique_brief

    return critique_brief(
        question=question or "",
        operationalization=operationalization or "",
        brief=brief or "",
        why_it_matters=why_it_matters or "",
    )


def handle_voi_worksheet(
    *,
    question_id: str | None = None,
    question: str = "",
    operationalization: str = "",
    profile_name: str | None = None,
    domain: str = "",
    **_extra: Any,
) -> dict[str, Any]:
    """Fill VOI worksheet metadata — not computed EVSI."""
    from artificial_curiosity.voi import fill_voi_worksheet

    return fill_voi_worksheet(
        question_id=question_id or None,
        question=question or "",
        operationalization=operationalization or "",
        profile_name=profile_name or None,
        domain=domain or "",
    )


def handle_list_epistemic_cues(**_extra: Any) -> dict[str, Any]:
    """List epistemic cue tag vocabulary (UX annotations — not felt emotion)."""
    return list_epistemic_cues()


def handle_annotate_epistemic(
    *,
    question: str,
    gap_status: str = "unanswered",
    surprise: float = 0.5,
    neglectedness: float = 0.5,
    answerability: float = 0.5,
    notes: str = "",
    domain: str = "ai",
    **_extra: Any,
) -> dict[str, Any]:
    """Annotate question text with epistemic cue tags."""
    return annotate_epistemic(
        question,
        gap_status=gap_status,
        surprise=float(surprise),
        neglectedness=float(neglectedness),
        answerability=float(answerability),
        notes=notes or "",
        domain=domain,
    )


def handle_emotion_pack(
    *,
    name: str = "affective_science",
    **_extra: Any,
) -> dict[str, Any]:
    """Return affective_science (or named) domain pack seeds."""
    return emotion_pack(name or "affective_science")


def handle_elicit_helpers(**_extra: Any) -> dict[str, Any]:
    """Incongruity → investigation framing + inject helpers."""
    return elicit_helpers()


def handle_emotion_catalog(
    *,
    family: str | None = None,
    **_extra: Any,
) -> dict[str, Any]:
    """Return mixable named-emotion catalog (annotation only)."""
    return emotion_catalog(family=family or None)


def handle_mix_emotions(
    *,
    weights: dict[str, Any] | None = None,
    **_extra: Any,
) -> dict[str, Any]:
    """Mix catalog emotions by percent/weight; normalize to sum=1.0."""
    if not isinstance(weights, dict) or not weights:
        raise ValueError(
            'weights must be a non-empty object, e.g. {"curiosity": 40, "confusion": 30, "awe": 30}'
        )
    cleaned: dict[str, float] = {}
    for key, val in weights.items():
        cleaned[str(key)] = float(val)
    return mix_emotions(cleaned)


# Canonical tool registry: name → (description, schema, handler)
# Aliases (spark / run_curiosity) share handlers with primary names.
ToolHandler = Callable[..., dict[str, Any]]

TOOL_SPECS: list[dict[str, Any]] = [
    {
        "name": "provoke_curiosity",
        "description": (
            "PROVOKE CURIOSITY (not Q&A): return ranked *unanswered* scientific "
            "questions plus an `inject` pack to paste into model context. "
            "Use when the user/agent is stuck answering known frames and needs "
            "what to investigate next. Explicit ValueProfile required conceptually "
            "(pass profile_name). Default fast=true skips network. Alias: spark. "
            "Scores are decision aids with bands — not oracles."
        ),
        "input_schema": PROVOKE_SCHEMA,
        "handler": handle_provoke_curiosity,
    },
    {
        "name": "spark",
        "description": ("Alias of provoke_curiosity — instant ranked unknowns + inject pack."),
        "input_schema": PROVOKE_SCHEMA,
        "handler": handle_provoke_curiosity,
    },
    {
        "name": "rank_unknowns",
        "description": (
            "Rank and briefly explain valuable unanswered questions under an "
            "explicit ValueProfile; does not answer the questions. Full pipeline: "
            "generate → optional OpenAlex/S2 gap verify → multi-axis score → "
            "gates → diversify → investigation briefs. Pass profile_name. "
            "Related literature ≠ answered. Scores are decision aids with "
            "[low–high] bands — not oracles. Alias: run_curiosity."
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
    {
        "name": "compare_profiles",
        "description": (
            "Compare the same offline candidate pool under two ValueProfiles; "
            "returns side-by-side ranks and deltas. Does not merge into a "
            "silent consensus score. Decision aids only."
        ),
        "input_schema": COMPARE_PROFILES_SCHEMA,
        "handler": handle_compare_profiles,
    },
    {
        "name": "critique_brief",
        "description": (
            "Form-only critique of an investigation brief / operationalization "
            "(sprawl, missing falsifier, anthropomorphism). Does not re-rank or "
            "change ValueProfile scores — decision aid for writers. Related "
            "literature ≠ answered remains the gap rule."
        ),
        "input_schema": CRITIQUE_BRIEF_SCHEMA,
        "handler": handle_critique_brief,
    },
    {
        "name": "voi_worksheet",
        "description": (
            "Fill a VOI worksheet template with ranked-question metadata for "
            "domains that already have an external decision model. Not EVSI/ENBS; "
            "scores remain decision aids under a ValueProfile — not oracles."
        ),
        "input_schema": VOI_WORKSHEET_SCHEMA,
        "handler": handle_voi_worksheet,
    },
    {
        "name": "list_epistemic_cues",
        "description": (
            "List epistemic emotion cue tags (information_gap, incongruity, "
            "confusion_risk, …). UX annotations for investigation framing — "
            "NOT claims that the system feels emotions. See docs/EMOTIONS.md."
        ),
        "input_schema": LIST_EPISTEMIC_CUES_SCHEMA,
        "handler": handle_list_epistemic_cues,
    },
    {
        "name": "annotate_epistemic",
        "description": (
            "Annotate a question with epistemic cue tags from gap status + "
            "score axes (surprise / neglectedness / answerability). Returns "
            "tags, primary cue, and inject_fragment. Annotation only — does not feel."
        ),
        "input_schema": ANNOTATE_EPISTEMIC_SCHEMA,
        "handler": handle_annotate_epistemic,
    },
    {
        "name": "emotion_pack",
        "description": (
            "Load the affective_science domain pack (ranking seeds for "
            "affective / epistemic research unknowns). Annotation seeds only — "
            "does not feel; not an emotion engine or CME."
        ),
        "input_schema": EMOTION_PACK_SCHEMA,
        "handler": handle_emotion_pack,
    },
    {
        "name": "elicit_helpers",
        "description": (
            "Return incongruity → curiosity → investigation framing text and "
            "inject helpers for agent context. Honesty: annotation / elicitation "
            "design — not anthropomorphic emotion; does not feel."
        ),
        "input_schema": ELICIT_HELPERS_SCHEMA,
        "handler": handle_elicit_helpers,
    },
    {
        "name": "emotion_catalog",
        "description": (
            "List mixable named emotions (epistemic, basic, social, achievement) "
            "with optional PAD anchors and elicit hints. Annotation only — "
            "does not feel. See docs/EMOTIONS.md."
        ),
        "input_schema": EMOTION_CATALOG_SCHEMA,
        "handler": handle_emotion_catalog,
    },
    {
        "name": "mix_emotions",
        "description": (
            "Mix catalog emotions by percentages/weights (normalized to sum 1.0). "
            "Example weights: {curiosity: 40, confusion: 30, awe: 30}. Returns "
            "blend profile, cue tags, inject_fragment. Annotation only — does not feel."
        ),
        "input_schema": MIX_EMOTIONS_SCHEMA,
        "handler": handle_mix_emotions,
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
