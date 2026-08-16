"""Eval / export / worksheet tools — display and templates, not re-rank."""

from __future__ import annotations

from typing import Any

__all__ = [
    "handle_cross_model_vote",
    "handle_export_unknowns",
    "handle_idea_graph",
    "handle_preference_weight_hints",
    "handle_soundness_pass",
    "handle_surprise_worksheet",
    "handle_voi_worksheet",
]


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
    """Fill VOI worksheet metadata — evsi is null, honesty=not_evsi."""
    from artificial_emotions.voi import fill_voi_worksheet

    return fill_voi_worksheet(
        question_id=question_id or None,
        question=question or "",
        operationalization=operationalization or "",
        profile_name=profile_name or None,
        domain=domain or "",
    )


def handle_preference_weight_hints(
    *,
    events: list[dict[str, Any]] | None = None,
    profile_name: str | None = "humanity_default",
    max_delta: float = 0.08,
    apply: bool = False,
    path: Any = None,
    events_path: Any = None,
    **_extra: Any,
) -> dict[str, Any]:
    """Preview (default) or apply tiny ValueProfile weight hints from inline events."""
    from artificial_emotions.preferences import preview_or_apply_weight_hints

    if path is not None or events_path is not None or "preference_learn_path" in _extra:
        return {
            "ok": False,
            "reason": "filesystem_paths_not_accepted",
            "mode": "preview",
            "applied": False,
            "deltas": {},
            "honesty": (
                "Inline events only — filesystem paths are not accepted on MCP. "
                "Weight hints are tiny profile-scoped deltas, not calibrated "
                "learning. Decision aids under an explicit ValueProfile — not oracles."
            ),
        }
    if not events:
        return {
            "ok": False,
            "reason": "need_inline_events",
            "mode": "preview" if not apply else "apply",
            "applied": False,
            "deltas": {},
            "honesty": (
                "Pass inline labeled events with score_axes. "
                "Not calibrated learning. Decision aids under an explicit "
                "ValueProfile — not oracles."
            ),
        }
    return preview_or_apply_weight_hints(
        events,
        profile_name=profile_name,
        max_delta=float(max_delta or 0.08),
        apply=bool(apply),
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


def handle_export_unknowns(
    *,
    questions: list[dict[str, Any]] | None = None,
    domain: str = "",
    topic: str = "",
    profile_name: str | None = None,
    literature_backend: str = "none",
    **extra: Any,
) -> dict[str, Any]:
    """Wrap an already-ranked set as a JSON document. No webhook URLs (SSRF)."""
    from artificial_emotions.export_unknowns import (
        DELIVERY_HTTP_BODY,
        export_unknowns,
        reject_webhook_fields,
    )

    reject_webhook_fields(extra)
    return export_unknowns(
        list(questions or []),
        domain=domain,
        topic=topic,
        profile_name=profile_name,
        literature_backend=literature_backend or "none",
        delivery=DELIVERY_HTTP_BODY,
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
