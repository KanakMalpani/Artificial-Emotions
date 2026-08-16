"""Tool implementations. Each returns a JSON-serializable dict.

Family modules live in ``handler_families/``. This module is the stable
re-export so MCP / HTTP / registry callers do not churn.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from artificial_emotions.agent_tools_pkg.handler_families.curiosity import (
    handle_compare_profiles,
    handle_constitution_compare,
    handle_list_domains,
    handle_list_profiles,
    handle_provoke_curiosity,
    handle_rank_unknowns,
)
from artificial_emotions.agent_tools_pkg.handler_families.emotions import (
    handle_annotate_epistemic,
    handle_elicit_helpers,
    handle_emotion_catalog,
    handle_emotion_pack,
    handle_list_epistemic_cues,
    handle_mix_emotions,
)
from artificial_emotions.agent_tools_pkg.handler_families.eval_tools import (
    handle_cross_model_vote,
    handle_export_unknowns,
    handle_idea_graph,
    handle_preference_weight_hints,
    handle_soundness_pass,
    handle_surprise_worksheet,
    handle_voi_worksheet,
)
from artificial_emotions.agent_tools_pkg.handler_families.imagine import (
    handle_apply_imagination,
    handle_imagine_transfer,
    handle_list_imagination_kinds,
)
from artificial_emotions.agent_tools_pkg.handler_families.investigate import (
    handle_critique_brief,
    handle_decompose_question,
    handle_explore_curiosity,
)
from artificial_emotions.agent_tools_pkg.handler_families.memory import (
    handle_dream_reanalyze,
    handle_memory_avoiding,
    handle_memory_forget,
    handle_memory_reset,
    handle_memory_show,
)
from artificial_emotions.agent_tools_pkg.handler_families.stances import (
    handle_apply_stance,
    handle_list_stances,
)

# Canonical tool registry: name → (description, schema, handler)
# Aliases (spark / run_curiosity) share handlers with primary names.
ToolHandler = Callable[..., dict[str, Any]]

__all__ = [
    "ToolHandler",
    "handle_annotate_epistemic",
    "handle_apply_imagination",
    "handle_apply_stance",
    "handle_compare_profiles",
    "handle_constitution_compare",
    "handle_critique_brief",
    "handle_cross_model_vote",
    "handle_decompose_question",
    "handle_dream_reanalyze",
    "handle_elicit_helpers",
    "handle_emotion_catalog",
    "handle_emotion_pack",
    "handle_explore_curiosity",
    "handle_export_unknowns",
    "handle_idea_graph",
    "handle_imagine_transfer",
    "handle_list_domains",
    "handle_list_epistemic_cues",
    "handle_list_imagination_kinds",
    "handle_list_profiles",
    "handle_list_stances",
    "handle_memory_avoiding",
    "handle_memory_forget",
    "handle_memory_reset",
    "handle_memory_show",
    "handle_mix_emotions",
    "handle_preference_weight_hints",
    "handle_provoke_curiosity",
    "handle_rank_unknowns",
    "handle_soundness_pass",
    "handle_surprise_worksheet",
    "handle_voi_worksheet",
]
