"""Investigate-family tools: critique, decompose, explore."""

from __future__ import annotations

from typing import Any

__all__ = [
    "handle_critique_brief",
    "handle_decompose_question",
    "handle_explore_curiosity",
]


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


def handle_explore_curiosity(
    *,
    domain: str = "ai",
    topic: str = "",
    steps: int = 5,
    n_return: int = 5,
    profile_name: str | None = None,
    use_literature: bool = False,
    allow_weight_deltas: bool = False,
    somatic_modulate: bool = False,
    allow_domain_jump: bool = True,
    decompose_depth: int = 1,
    persist_memory: Any = None,
    memory_path: Any = None,
    **_extra: Any,
) -> dict[str, Any]:
    """Run the curiosity loop and return the trajectory.

    MCP never persists: ``persist_memory`` / ``memory_path`` are refused even if
    a host passes them. CLI owns the opt-in write path.
    """
    from artificial_emotions.explore import explore

    # Hard refuse — kwargs must not enable disk writes from this surface.
    _ = persist_memory, memory_path, _extra
    return explore(
        domain=domain,
        topic=topic,
        steps=int(steps or 5),
        n_return=int(n_return or 5),
        profile_name=profile_name,
        use_literature=bool(use_literature),
        allow_weight_deltas=bool(allow_weight_deltas),
        somatic_modulate=bool(somatic_modulate),
        allow_domain_jump=bool(allow_domain_jump),
        decompose_depth=int(decompose_depth or 1),
        persist_memory=False,
        memory_path=None,
    )
