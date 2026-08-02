"""JSON Schema fragments shared by MCP `inputSchema` and OpenAI `parameters`.

One definition per tool so Cursor / Claude Desktop / Copilot / custom agents
all see the same contract."""

from __future__ import annotations

from typing import Any

from artificial_emotions.models import (
    Domain,
    list_profile_names,
)

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
        "allow_domain_jump": {"type": "boolean", "default": True},
        "decompose_depth": {"type": "integer", "minimum": 1, "maximum": 3, "default": 1},
    },
    "additionalProperties": False,
}


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
            "enum": ["premortem", "reformulation", "counterfactual"],
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
