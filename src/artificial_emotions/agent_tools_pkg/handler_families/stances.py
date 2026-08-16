"""Stance tools: list and apply a view over an existing ranking."""

from __future__ import annotations

from typing import Any

__all__ = [
    "handle_apply_stance",
    "handle_list_stances",
]


def handle_list_stances(**_extra: Any) -> dict[str, Any]:
    """List the available stances and what each one is for."""
    from artificial_emotions.stances import list_stances

    return list_stances()


def handle_apply_stance(
    *,
    stance: str,
    domain: str = "ai",
    topic: str = "",
    n_return: int = 6,
    profile_name: str | None = None,
    use_literature: bool = False,
    **_extra: Any,
) -> dict[str, Any]:
    """Rank once, then look at the result through one emotional stance."""
    from artificial_emotions.models import CuriosityConfig, resolve_value_profile
    from artificial_emotions.pipeline import CuriosityEngine
    from artificial_emotions.stances import apply_stance

    items = CuriosityEngine(
        CuriosityConfig(
            domain=domain,
            topic=topic,
            n_return=int(n_return or 6),
            use_llm=False,
            use_literature=bool(use_literature),
            value_profile=resolve_value_profile(profile_name=profile_name),
        )
    ).run()
    return apply_stance(stance, items)
