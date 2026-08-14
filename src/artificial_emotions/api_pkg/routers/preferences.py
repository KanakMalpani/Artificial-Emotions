"""Preference feedback endpoints.

All three take events inline — no filesystem paths are accepted over HTTP
(path injection). These produce hints, not calibrated learning.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from artificial_emotions.api_pkg.schemas import (
    PreferenceHintsRequest,
    PreferenceSummarizeRequest,
    SuggestPairRequest,
    safe_profile,
)
from artificial_emotions.preferences import (
    preview_or_apply_weight_hints,
    summarize_preferences,
)

router = APIRouter()


@router.post("/v1/preferences/hints")
def preference_weight_hints(req: PreferenceHintsRequest) -> dict[str, Any]:
    """Preview (default) or apply tiny ValueProfile weight deltas from inline events.

    No filesystem paths accepted (path injection). Not calibrated learning.
    apply=false returns a preview; apply=true returns an applied profile copy.
    """
    profile = safe_profile(req.value_profile, req.profile_name)
    return preview_or_apply_weight_hints(
        req.events,
        profile_name=req.profile_name or profile.name,
        base_profile=profile,
        max_delta=req.max_delta,
        apply=bool(req.apply),
    )


@router.post("/v1/preferences/summarize")
def preference_summarize(req: PreferenceSummarizeRequest) -> dict[str, Any]:
    """Counts, pairwise wins, and weight hints from inline events (no paths)."""
    return summarize_preferences(
        req.events,
        profile_name=req.profile_name,
        top_k=req.top_k,
    )


@router.post("/v1/preferences/suggest-pair")
def preference_suggest_pair(req: SuggestPairRequest) -> dict[str, Any]:
    """Propose next pairwise duel among top-k — not BT weight overwrite."""
    from artificial_emotions.preferences import suggest_next_pair

    return suggest_next_pair(
        req.candidates,
        req.events,
        profile_name=req.profile_name,
    )
