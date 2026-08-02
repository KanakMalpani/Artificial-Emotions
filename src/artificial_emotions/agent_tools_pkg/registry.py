"""Tool registry: specs, tier filtering, and dispatch.

`TOOL_SPECS` is the single source of truth — MCP list, OpenAI tool list,
and dispatch all derive from it."""

from __future__ import annotations

import json
from typing import Any

from artificial_emotions.agent_tools_pkg.handlers import (
    ToolHandler,
    handle_annotate_epistemic,
    handle_apply_imagination,
    handle_apply_stance,
    handle_compare_profiles,
    handle_constitution_compare,
    handle_critique_brief,
    handle_cross_model_vote,
    handle_decompose_question,
    handle_dream_reanalyze,
    handle_elicit_helpers,
    handle_emotion_catalog,
    handle_emotion_pack,
    handle_explore_curiosity,
    handle_idea_graph,
    handle_imagine_transfer,
    handle_list_domains,
    handle_list_epistemic_cues,
    handle_list_imagination_kinds,
    handle_list_profiles,
    handle_list_stances,
    handle_memory_avoiding,
    handle_memory_forget,
    handle_memory_reset,
    handle_memory_show,
    handle_mix_emotions,
    handle_provoke_curiosity,
    handle_rank_unknowns,
    handle_soundness_pass,
    handle_surprise_worksheet,
    handle_voi_worksheet,
)
from artificial_emotions.agent_tools_pkg.schemas import (
    ANNOTATE_EPISTEMIC_SCHEMA,
    APPLY_IMAGINATION_SCHEMA,
    APPLY_STANCE_SCHEMA,
    COMPARE_PROFILES_SCHEMA,
    CONSTITUTION_COMPARE_SCHEMA,
    CRITIQUE_BRIEF_SCHEMA,
    CROSS_MODEL_VOTE_SCHEMA,
    DECOMPOSE_SCHEMA,
    DREAM_REANALYZE_SCHEMA,
    ELICIT_HELPERS_SCHEMA,
    EMOTION_CATALOG_SCHEMA,
    EMOTION_PACK_SCHEMA,
    EXPLORE_SCHEMA,
    IDEA_GRAPH_SCHEMA,
    IMAGINE_TRANSFER_SCHEMA,
    LIST_DOMAINS_SCHEMA,
    LIST_EPISTEMIC_CUES_SCHEMA,
    LIST_IMAGINATION_KINDS_SCHEMA,
    LIST_PROFILES_SCHEMA,
    LIST_STANCES_SCHEMA,
    MEMORY_AVOIDING_SCHEMA,
    MEMORY_FORGET_SCHEMA,
    MEMORY_RESET_SCHEMA,
    MEMORY_SHOW_SCHEMA,
    MIX_EMOTIONS_SCHEMA,
    PROVOKE_SCHEMA,
    RANK_SCHEMA,
    SOUNDNESS_PASS_SCHEMA,
    SURPRISE_WORKSHEET_SCHEMA,
    VOI_WORKSHEET_SCHEMA,
)

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
        "name": "constitution_compare",
        "description": (
            "Load the example constitution/veto stack, compare primary vs safety "
            "veto profiles side-by-side, then flag items exceeding the stricter "
            "max_risk. Does not invent a consensus score. Decision aids only."
        ),
        "input_schema": CONSTITUTION_COMPARE_SCHEMA,
        "handler": handle_constitution_compare,
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
        "name": "decompose_question",
        "description": (
            "Go one level deeper on a single unknown: expand it into measurement, "
            "baseline, mechanism, confound and boundary sub-questions, name the one "
            "observation worth making first, derive falsifiers from the stated "
            "criteria, and give stop rules. Returns only questions and tests — it "
            "does not answer the question and asserts no hypothesis. Use after "
            "rank_unknowns to plan an investigation, not to conclude one. The "
            "ladder is a decision aid, not a computed information gain; related "
            "literature ≠ answered still applies to every sub-question."
        ),
        "input_schema": DECOMPOSE_SCHEMA,
        "handler": handle_decompose_question,
    },
    {
        "name": "explore_curiosity",
        "description": (
            "Run the curiosity loop rather than a single ranking: each step ranks, "
            "appraises what it found, feels something as a result, lets that change "
            "how it searches next, and remembers where it has been. Returns the full "
            "trajectory — every feeling, its evidence, and what it changed — ending "
            "in a decomposed plan for the best unknown found. Affect moves search "
            "behaviour only; ValueProfile weights stay untouched unless explicitly "
            "allowed, and any delta is bounded and listed. Decision aid, not a "
            "closed-loop scientist; related literature != answered still applies. "
            "MCP never persists memory — persist_memory is refused on this surface."
        ),
        "input_schema": EXPLORE_SCHEMA,
        "handler": handle_explore_curiosity,
    },
    {
        "name": "list_stances",
        "description": (
            "List the stances — different questions to ask of one ranked set, each "
            "driven by a different emotion. Curiosity answers 'what is worth "
            "investigating'; doubt asks 'why might this be wrong', safety asks 'what "
            "could this hurt', focus asks 'what should I stay on', close asks 'what "
            "should I abandon', taste asks 'which is well-formed', wonder asks 'what "
            "is most surprising regardless of value', survey asks 'where is the crowd'. "
            "A stance is a view, never a re-ranking: the ValueProfile ordering is "
            "untouched. Decision aids only — not verdicts."
        ),
        "input_schema": LIST_STANCES_SCHEMA,
        "handler": handle_list_stances,
    },
    {
        "name": "apply_stance",
        "description": (
            "Rank unknowns once, then read the result through one stance instead of "
            "the curiosity ordering. Use when 'what is most valuable' is the wrong "
            "question — e.g. before committing resource (doubt), before touching a "
            "risky area (safety), when deciding what to drop (close), or when you "
            "want to be surprised rather than to optimise (wonder). Returns a view "
            "over the existing ranking: the ValueProfile ordering is unchanged and no "
            "item is rescored. Decision aid, not a verdict."
        ),
        "input_schema": APPLY_STANCE_SCHEMA,
        "handler": handle_apply_stance,
    },
    {
        "name": "list_imagination_kinds",
        "description": (
            "List imagination kinds — generative twins of stances (premortem, "
            "reformulation, counterfactual, …). Transfer is corpus_gated "
            "(imagine_transfer tool; not apply_imagination). Outputs are "
            "quarantined imagined content with honesty imagined_not_retrieved; "
            "never ranked findings, never a confidence score. Decision aids "
            "only — does not feel; computational generation under quarantine. "
            "Related literature ≠ answered still applies."
        ),
        "input_schema": LIST_IMAGINATION_KINDS_SCHEMA,
        "handler": handle_list_imagination_kinds,
    },
    {
        "name": "apply_imagination",
        "description": (
            "Rank unknowns once, then generate quarantined imagined content via a "
            "stance twin (premortem = imagine this failed; reformulation = imagine "
            "a better-posed question; counterfactual = posit an answer and derive "
            "consequences). Offline generators; outputs travel only under the "
            "imagined payload key with honesty imagined_not_retrieved and "
            "confidence=null. Never injects into ranked lists. Transfer is "
            "corpus_gated — use imagine_transfer instead. Decision aid under "
            "an explicit ValueProfile — does not feel; not retrieved literature; "
            "related ≠ answered."
        ),
        "input_schema": APPLY_IMAGINATION_SCHEMA,
        "handler": handle_apply_imagination,
    },
    {
        "name": "imagine_transfer",
        "description": (
            "Corpus-gated analogical transfer: seed concept + local corpus "
            "(path or document list) → quarantined imagined structural analogies. "
            "Refuses when ship status is not cleared. Never ranked injection; "
            "never apply_imagination. Honesty imagined_not_retrieved; "
            "confidence=null. Decision aid under quarantine — does not feel; "
            "related literature ≠ answered."
        ),
        "input_schema": IMAGINE_TRANSFER_SCHEMA,
        "handler": handle_imagine_transfer,
    },
    {
        "name": "memory_show",
        "description": (
            "Read-only dump of local PersistentMemory JSON if present "
            "(privacy_notice fields included). Never creates the file; MCP does "
            "not persist by default. Annotation continuity — does not feel; "
            "decision aid only. Related literature ≠ answered."
        ),
        "input_schema": MEMORY_SHOW_SCHEMA,
        "handler": handle_memory_show,
    },
    {
        "name": "memory_forget",
        "description": (
            "Explicit forget of a session id, question id, or keyword from local "
            "memory. Requires confirm=true. Still no auto-write from "
            "explore_curiosity. Annotation continuity — does not feel; "
            "decision aid only. Related literature ≠ answered."
        ),
        "input_schema": MEMORY_FORGET_SCHEMA,
        "handler": handle_memory_forget,
    },
    {
        "name": "memory_reset",
        "description": (
            "Explicit wipe of local PersistentMemory and delete of the JSON file. "
            "Requires confirm=true. Still no auto-write from explore_curiosity. "
            "Annotation continuity — does not feel; decision aid only. "
            "Related literature ≠ answered."
        ),
        "input_schema": MEMORY_RESET_SCHEMA,
        "handler": handle_memory_reset,
    },
    {
        "name": "memory_avoiding",
        "description": (
            "Surface avoidance patterns from local memory encounters vs selections "
            "(pattern ≠ motive; cannot distinguish avoidance from judgment). "
            "Read-only; never creates the file. Annotation only — does not feel; "
            "decision aid only. Related literature ≠ answered."
        ),
        "input_schema": MEMORY_AVOIDING_SCHEMA,
        "handler": handle_memory_avoiding,
    },
    {
        "name": "dream_reanalyze",
        "description": (
            "Explicit offline reanalysis of stored PersistentMemory history "
            "(CLI may say dream once; payload framing is "
            "offline_reanalysis_of_stored_history — never labeled dream as "
            "evidence). Read-only; invents no literature. Decision aid under "
            "quarantine — does not feel; related literature ≠ answered."
        ),
        "input_schema": DREAM_REANALYZE_SCHEMA,
        "handler": handle_dream_reanalyze,
    },
    {
        "name": "cross_model_vote",
        "description": (
            "Offline HybridQuestion-style keep/drop/rewrite annotations on "
            "candidate unknowns (form/heuristic proxy). Does not re-rank; "
            "agreement is not VOI. Decision aids under an explicit ValueProfile "
            "remain separate."
        ),
        "input_schema": CROSS_MODEL_VOTE_SCHEMA,
        "handler": handle_cross_model_vote,
    },
    {
        "name": "export_idea_graph",
        "description": (
            "Export top-n unknowns as a tiny EIG-inspired idea graph "
            "(similarity/conflict edges). Display/debug only — does not re-rank "
            "or replace ValueProfile scoring. Related literature ≠ answered."
        ),
        "input_schema": IDEA_GRAPH_SCHEMA,
        "handler": handle_idea_graph,
    },
    {
        "name": "soundness_pass",
        "description": (
            "Offline ScholarEval/InnoEval-cousin soundness pass on top-n briefs "
            "(form, gap honesty, feasibility note). Decoupled dimensions — not a "
            "global science judge. Does not re-rank; ValueProfile remains explicit."
        ),
        "input_schema": SOUNDNESS_PASS_SCHEMA,
        "handler": handle_soundness_pass,
    },
    {
        "name": "surprise_worksheet",
        "description": (
            "Fill a Bayesian-surprise closed-loop belief-shift worksheet for a "
            "ranked unknown. Manual logging only — not EVSI, does not rename "
            "ScoreAxes.surprise. Decision aids under an explicit ValueProfile."
        ),
        "input_schema": SURPRISE_WORKSHEET_SCHEMA,
        "handler": handle_surprise_worksheet,
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
            "blend profile, felt_simulation (PAD mood + intensity + inner monologue) "
            "— computational affect as close to feeling as this CME blend allows; "
            "not biological consciousness."
        ),
        "input_schema": MIX_EMOTIONS_SCHEMA,
        "handler": handle_mix_emotions,
    },
]

HANDLERS: dict[str, ToolHandler] = {t["name"]: t["handler"] for t in TOOL_SPECS}

# Progressive disclosure tiers (private local notes; not in the public tree).
# Default CURIOSITY_MCP_TIER=full keeps current host behavior.
_TOOL_TIER: dict[str, str] = {
    "provoke_curiosity": "core",
    "spark": "core",
    "rank_unknowns": "core",
    "run_curiosity": "core",
    "list_domains": "core",
    "list_profiles": "core",
    "compare_profiles": "investigate",
    "constitution_compare": "investigate",
    "critique_brief": "investigate",
    "decompose_question": "investigate",
    "explore_curiosity": "research",
    "list_stances": "core",
    "apply_stance": "investigate",
    "list_imagination_kinds": "core",
    "apply_imagination": "investigate",
    "imagine_transfer": "investigate",
    "memory_show": "research",
    "memory_forget": "research",
    "memory_reset": "research",
    "memory_avoiding": "research",
    "dream_reanalyze": "research",
    "soundness_pass": "investigate",
    "cross_model_vote": "research",
    "export_idea_graph": "research",
    "surprise_worksheet": "research",
    "voi_worksheet": "research",
    "list_epistemic_cues": "affect",
    "annotate_epistemic": "affect",
    "emotion_pack": "affect",
    "elicit_helpers": "affect",
    "emotion_catalog": "affect",
    "mix_emotions": "affect",
}
_TIER_INCLUDES: dict[str, set[str]] = {
    "core": {"core"},
    "investigate": {"core", "investigate"},
    "affect": {"core", "investigate", "affect"},
    "research": {"core", "investigate", "research"},
    "full": {"core", "investigate", "affect", "research"},
}


def resolve_mcp_tier(tier: str | None = None) -> str:
    import os

    raw = (tier or os.environ.get("CURIOSITY_MCP_TIER") or "full").strip().lower()
    return raw if raw in _TIER_INCLUDES else "full"


def mcp_tool_tiers() -> dict[str, Any]:
    by_tier: dict[str, list[str]] = {
        "core": [],
        "investigate": [],
        "affect": [],
        "research": [],
    }
    for name in HANDLERS:
        by_tier.setdefault(_TOOL_TIER.get(name, "core"), []).append(name)
    return {
        "active": resolve_mcp_tier(),
        "env": "CURIOSITY_MCP_TIER",
        "tiers": by_tier,
        "note": (
            "Fewer tools ≠ safer if remaining tools overclaim. "
            "curiosity://limits stays discoverable. Lint still applies."
        ),
    }


def mcp_tool_list(*, tier: str | None = None) -> list[dict[str, Any]]:
    """MCP `tools/list` payload (name, description, inputSchema)."""
    allowed = _TIER_INCLUDES[resolve_mcp_tier(tier)]
    out = []
    for t in TOOL_SPECS:
        if _TOOL_TIER.get(t["name"], "core") not in allowed:
            continue
        out.append(
            {
                "name": t["name"],
                "description": t["description"],
                "inputSchema": t["input_schema"],
            }
        )
    return out


def openai_tools(*, tier: str | None = None) -> list[dict[str, Any]]:
    """OpenAI / compatible function-calling tool definitions."""
    allowed = _TIER_INCLUDES[resolve_mcp_tier(tier)]
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
        if _TOOL_TIER.get(t["name"], "core") in allowed
    ]


def dispatch_tool(name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    """Run a registered tool by name. Raises KeyError if unknown."""
    handler = HANDLERS[name]
    return handler(**(arguments or {}))


def tools_as_json() -> str:
    return json.dumps(openai_tools(), indent=2)
