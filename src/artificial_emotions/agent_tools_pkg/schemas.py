"""JSON Schema fragments shared by MCP `inputSchema` and OpenAI `parameters`.

Family modules live in ``schema_families/``. This module is the stable
re-export so MCP / HTTP / registry callers do not churn. One definition per
tool so Cursor / Claude Desktop / Copilot / custom agents all see the same
contract.
"""

from __future__ import annotations

from artificial_emotions.agent_tools_pkg.schema_families.common import (
    _DOMAIN_ENUM,
    _PROFILE_ENUM,
    _VALUE_PROFILE_SCHEMA,
)
from artificial_emotions.agent_tools_pkg.schema_families.curiosity import (
    COMPARE_PROFILES_SCHEMA,
    CONSTITUTION_COMPARE_SCHEMA,
    LIST_DOMAINS_SCHEMA,
    LIST_PROFILES_SCHEMA,
    PROVOKE_SCHEMA,
    RANK_SCHEMA,
)
from artificial_emotions.agent_tools_pkg.schema_families.emotions import (
    ANNOTATE_EPISTEMIC_SCHEMA,
    ELICIT_HELPERS_SCHEMA,
    EMOTION_CATALOG_SCHEMA,
    EMOTION_PACK_SCHEMA,
    LIST_EPISTEMIC_CUES_SCHEMA,
    MIX_EMOTIONS_SCHEMA,
)
from artificial_emotions.agent_tools_pkg.schema_families.eval_tools import (
    CROSS_MODEL_VOTE_SCHEMA,
    EXPORT_UNKNOWNS_SCHEMA,
    IDEA_GRAPH_SCHEMA,
    PREFERENCE_WEIGHT_HINTS_SCHEMA,
    SOUNDNESS_PASS_SCHEMA,
    SURPRISE_WORKSHEET_SCHEMA,
    VOI_WORKSHEET_SCHEMA,
)
from artificial_emotions.agent_tools_pkg.schema_families.imagine import (
    APPLY_IMAGINATION_SCHEMA,
    IMAGINE_TRANSFER_SCHEMA,
    LIST_IMAGINATION_KINDS_SCHEMA,
)
from artificial_emotions.agent_tools_pkg.schema_families.investigate import (
    CRITIQUE_BRIEF_SCHEMA,
    DECOMPOSE_SCHEMA,
    EXPLORE_SCHEMA,
)
from artificial_emotions.agent_tools_pkg.schema_families.memory import (
    DREAM_REANALYZE_SCHEMA,
    MEMORY_AVOIDING_SCHEMA,
    MEMORY_FORGET_SCHEMA,
    MEMORY_RESET_SCHEMA,
    MEMORY_SHOW_SCHEMA,
)
from artificial_emotions.agent_tools_pkg.schema_families.stances import (
    APPLY_STANCE_SCHEMA,
    LIST_STANCES_SCHEMA,
)

__all__ = [
    "ANNOTATE_EPISTEMIC_SCHEMA",
    "APPLY_IMAGINATION_SCHEMA",
    "APPLY_STANCE_SCHEMA",
    "COMPARE_PROFILES_SCHEMA",
    "CONSTITUTION_COMPARE_SCHEMA",
    "CRITIQUE_BRIEF_SCHEMA",
    "CROSS_MODEL_VOTE_SCHEMA",
    "DECOMPOSE_SCHEMA",
    "DREAM_REANALYZE_SCHEMA",
    "ELICIT_HELPERS_SCHEMA",
    "EMOTION_CATALOG_SCHEMA",
    "EMOTION_PACK_SCHEMA",
    "EXPLORE_SCHEMA",
    "EXPORT_UNKNOWNS_SCHEMA",
    "IDEA_GRAPH_SCHEMA",
    "IMAGINE_TRANSFER_SCHEMA",
    "LIST_DOMAINS_SCHEMA",
    "LIST_EPISTEMIC_CUES_SCHEMA",
    "LIST_IMAGINATION_KINDS_SCHEMA",
    "LIST_PROFILES_SCHEMA",
    "LIST_STANCES_SCHEMA",
    "MEMORY_AVOIDING_SCHEMA",
    "MEMORY_FORGET_SCHEMA",
    "MEMORY_RESET_SCHEMA",
    "MEMORY_SHOW_SCHEMA",
    "MIX_EMOTIONS_SCHEMA",
    "PREFERENCE_WEIGHT_HINTS_SCHEMA",
    "PROVOKE_SCHEMA",
    "RANK_SCHEMA",
    "SOUNDNESS_PASS_SCHEMA",
    "SURPRISE_WORKSHEET_SCHEMA",
    "VOI_WORKSHEET_SCHEMA",
    "_DOMAIN_ENUM",
    "_PROFILE_ENUM",
    "_VALUE_PROFILE_SCHEMA",
]
