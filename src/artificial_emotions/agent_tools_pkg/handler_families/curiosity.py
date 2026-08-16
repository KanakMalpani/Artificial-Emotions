"""Core ranking and profile tools: provoke, rank, list, compare."""

from __future__ import annotations

from typing import Any

from artificial_emotions.agent_tools_pkg.schemas import _DOMAIN_ENUM
from artificial_emotions.models import (
    VALUE_PROFILE_PRESETS,
    CuriosityConfig,
    ValueProfile,
    resolve_value_profile,
)
from artificial_emotions.pipeline import CuriosityEngine
from artificial_emotions.provoke import provoke

__all__ = [
    "handle_compare_profiles",
    "handle_constitution_compare",
    "handle_list_domains",
    "handle_list_profiles",
    "handle_provoke_curiosity",
    "handle_rank_unknowns",
]


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
    from artificial_emotions.compare import compare_profiles

    return compare_profiles(
        domain=domain or "ai",
        topic=topic or "",
        profile_a=profile_a or "humanity_default",
        profile_b=profile_b or "alignment_lab",
        n=int(n or 8),
    )


def handle_constitution_compare(
    *,
    domain: str = "ai",
    topic: str = "",
    primary_profile: str | None = None,
    veto_profile: str | None = None,
    n: int = 8,
    **_extra: Any,
) -> dict[str, Any]:
    """Constitution stack compare + hard risk veto — no consensus merge."""
    from artificial_emotions.compare import compare_constitution

    return compare_constitution(
        domain=domain or "ai",
        topic=topic or "",
        primary_profile=primary_profile,
        veto_profile=veto_profile,
        n=int(n or 8),
    )
