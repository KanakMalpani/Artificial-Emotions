"""Tool implementations. Each returns a JSON-serializable dict."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from artificial_emotions.agent_tools_pkg.schemas import _DOMAIN_ENUM
from artificial_emotions.emotions import (
    annotate_epistemic,
    elicit_helpers,
    emotion_catalog,
    emotion_pack,
    list_epistemic_cues,
    mix_emotions,
)
from artificial_emotions.models import (
    VALUE_PROFILE_PRESETS,
    CuriosityConfig,
    ValueProfile,
    resolve_value_profile,
)
from artificial_emotions.pipeline import CuriosityEngine
from artificial_emotions.provoke import provoke


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


def handle_critique_brief(
    *,
    question: str = "",
    operationalization: str = "",
    brief: str = "",
    why_it_matters: str = "",
    **_extra: Any,
) -> dict[str, Any]:
    """Form-only brief critic — does not change ranks."""
    from artificial_emotions.critique import critique_brief

    return critique_brief(
        question=question or "",
        operationalization=operationalization or "",
        brief=brief or "",
        why_it_matters=why_it_matters or "",
    )


def handle_decompose_question(
    *,
    question: str = "",
    operationalization: str = "",
    domain: str = "ai",
    depth: int = 1,
    answerability: float | None = None,
    tractability: float | None = None,
    risk: float | None = None,
    **_extra: Any,
) -> dict[str, Any]:
    """Expand one unknown into sub-questions, a first step, and stop rules."""
    from artificial_emotions.decompose import decompose_question
    from artificial_emotions.models import UnansweredQuestion

    q = UnansweredQuestion(
        id="decompose-request",
        question=question or "",
        domain=domain or "ai",
        operationalization=operationalization or "",
        why_it_matters="Supplied for decomposition.",
    )
    return decompose_question(
        q,
        depth=int(depth or 1),
        answerability=answerability,
        tractability=tractability,
        risk=risk,
    )


def handle_cross_model_vote(
    *,
    candidates: list[dict[str, Any]] | None = None,
    judges: int = 1,
    **_extra: Any,
) -> dict[str, Any]:
    """Offline HybridQuestion-style vote proxy — does not re-rank."""
    from artificial_emotions.hybrid_vote import cross_model_vote

    return cross_model_vote(list(candidates or []), judges=int(judges or 1))


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
    from artificial_emotions.voi import fill_voi_worksheet

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
    """Return mixable named-emotion catalog (computational affect simulation)."""
    return emotion_catalog(family=family or None)


def handle_mix_emotions(
    *,
    weights: dict[str, Any] | None = None,
    profile_name: str | None = None,
    mix_intensity_cap: float | None = None,
    simulate_feeling: bool = True,
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
    return mix_emotions(
        cleaned,
        profile_name=profile_name,
        mix_intensity_cap=mix_intensity_cap,
        simulate_feeling=simulate_feeling,
    )


def handle_idea_graph(
    *,
    candidates: list[dict[str, Any]] | None = None,
    similarity_threshold: float = 0.28,
    **_extra: Any,
) -> dict[str, Any]:
    """EIG-inspired idea graph export — display only."""
    from artificial_emotions.idea_graph import export_idea_graph

    return export_idea_graph(
        list(candidates or []),
        similarity_threshold=float(similarity_threshold or 0.28),
    )


def handle_soundness_pass(
    *,
    candidates: list[dict[str, Any]] | None = None,
    **_extra: Any,
) -> dict[str, Any]:
    """Offline soundness pass — does not re-rank."""
    from artificial_emotions.soundness import soundness_pass

    return soundness_pass(list(candidates or []))


def handle_surprise_worksheet(
    *,
    question_id: str | None = None,
    profile_name: str | None = None,
    predicted_surprise: float | None = None,
    pilot_result: str = "",
    belief_shift_1_to_5: int | None = None,
    crude_update_note: str = "",
    **_extra: Any,
) -> dict[str, Any]:
    """Belief-shift worksheet — not EVSI / not axis rename."""
    from artificial_emotions.bayesian import fill_surprise_worksheet

    return fill_surprise_worksheet(
        question_id=question_id,
        profile_name=profile_name,
        predicted_surprise=predicted_surprise,
        pilot_result=pilot_result or "",
        belief_shift_1_to_5=belief_shift_1_to_5,
        crude_update_note=crude_update_note or "",
    )


# Canonical tool registry: name → (description, schema, handler)
# Aliases (spark / run_curiosity) share handlers with primary names.
ToolHandler = Callable[..., dict[str, Any]]
