"""Shared tool definitions for MCP, OpenAI function-calling, and HTTP agents.

Public surface stays ``artificial_emotions.agent_tools`` — this package is the
implementation behind it, layered so each file has one job:

    schemas.py            stable re-export of JSON Schema fragments
    schema_families/      schemas split by tool family (mirrors handler_families)
    handlers.py           stable re-export of tool implementations
    handler_families/     implementations split by tool family
    registry.py           TOOL_SPECS, tier filtering, dispatch
    mcp_resources.py      curiosity:// resource list and read

The dependency direction is strictly schemas → handlers → registry →
mcp_resources; nothing imports backwards. Callers import handlers from
``handlers.py``, not from family modules.
"""

from __future__ import annotations

from artificial_emotions.agent_tools_pkg.handlers import (
    ToolHandler,
    handle_annotate_epistemic,
    handle_compare_profiles,
    handle_constitution_compare,
    handle_critique_brief,
    handle_cross_model_vote,
    handle_decompose_question,
    handle_elicit_helpers,
    handle_emotion_catalog,
    handle_emotion_pack,
    handle_explore_curiosity,
    handle_export_unknowns,
    handle_idea_graph,
    handle_list_domains,
    handle_list_epistemic_cues,
    handle_list_profiles,
    handle_mix_emotions,
    handle_preference_weight_hints,
    handle_provoke_curiosity,
    handle_rank_unknowns,
    handle_soundness_pass,
    handle_surprise_worksheet,
    handle_voi_worksheet,
)
from artificial_emotions.agent_tools_pkg.mcp_resources import (
    mcp_resource_list,
    mcp_resource_read,
)
from artificial_emotions.agent_tools_pkg.registry import (
    HANDLERS,
    TOOL_SPECS,
    dispatch_tool,
    mcp_tool_list,
    mcp_tool_tiers,
    openai_tools,
    resolve_mcp_tier,
    tools_as_json,
)
from artificial_emotions.agent_tools_pkg.schemas import (
    ANNOTATE_EPISTEMIC_SCHEMA,
    COMPARE_PROFILES_SCHEMA,
    CONSTITUTION_COMPARE_SCHEMA,
    CRITIQUE_BRIEF_SCHEMA,
    CROSS_MODEL_VOTE_SCHEMA,
    DECOMPOSE_SCHEMA,
    ELICIT_HELPERS_SCHEMA,
    EMOTION_CATALOG_SCHEMA,
    EMOTION_PACK_SCHEMA,
    EXPLORE_SCHEMA,
    EXPORT_UNKNOWNS_SCHEMA,
    IDEA_GRAPH_SCHEMA,
    LIST_DOMAINS_SCHEMA,
    LIST_EPISTEMIC_CUES_SCHEMA,
    LIST_PROFILES_SCHEMA,
    MIX_EMOTIONS_SCHEMA,
    PREFERENCE_WEIGHT_HINTS_SCHEMA,
    PROVOKE_SCHEMA,
    RANK_SCHEMA,
    SOUNDNESS_PASS_SCHEMA,
    SURPRISE_WORKSHEET_SCHEMA,
    VOI_WORKSHEET_SCHEMA,
)

__all__ = [
    "ANNOTATE_EPISTEMIC_SCHEMA",
    "COMPARE_PROFILES_SCHEMA",
    "CONSTITUTION_COMPARE_SCHEMA",
    "CRITIQUE_BRIEF_SCHEMA",
    "CROSS_MODEL_VOTE_SCHEMA",
    "DECOMPOSE_SCHEMA",
    "ELICIT_HELPERS_SCHEMA",
    "EXPLORE_SCHEMA",
    "EXPORT_UNKNOWNS_SCHEMA",
    "EMOTION_CATALOG_SCHEMA",
    "EMOTION_PACK_SCHEMA",
    "HANDLERS",
    "IDEA_GRAPH_SCHEMA",
    "LIST_DOMAINS_SCHEMA",
    "LIST_EPISTEMIC_CUES_SCHEMA",
    "LIST_PROFILES_SCHEMA",
    "MIX_EMOTIONS_SCHEMA",
    "PREFERENCE_WEIGHT_HINTS_SCHEMA",
    "PROVOKE_SCHEMA",
    "RANK_SCHEMA",
    "SOUNDNESS_PASS_SCHEMA",
    "SURPRISE_WORKSHEET_SCHEMA",
    "TOOL_SPECS",
    "ToolHandler",
    "VOI_WORKSHEET_SCHEMA",
    "dispatch_tool",
    "handle_annotate_epistemic",
    "handle_compare_profiles",
    "handle_constitution_compare",
    "handle_critique_brief",
    "handle_cross_model_vote",
    "handle_decompose_question",
    "handle_elicit_helpers",
    "handle_explore_curiosity",
    "handle_export_unknowns",
    "handle_emotion_catalog",
    "handle_emotion_pack",
    "handle_idea_graph",
    "handle_list_domains",
    "handle_list_epistemic_cues",
    "handle_list_profiles",
    "handle_mix_emotions",
    "handle_preference_weight_hints",
    "handle_provoke_curiosity",
    "handle_rank_unknowns",
    "handle_soundness_pass",
    "handle_surprise_worksheet",
    "handle_voi_worksheet",
    "mcp_resource_list",
    "mcp_resource_read",
    "mcp_tool_list",
    "mcp_tool_tiers",
    "openai_tools",
    "resolve_mcp_tier",
    "tools_as_json",
]
