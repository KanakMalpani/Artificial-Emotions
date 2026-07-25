"""Preference feedback endpoints.

All three take events inline — no filesystem paths are accepted over HTTP
(path injection). These produce hints, not calibrated learning.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from artificial_curiosity.api_pkg.schemas import (
    PreferenceHintsRequest,
    PreferenceSummarizeRequest,
    SuggestPairRequest,
    safe_profile,
)
from artificial_curiosity.preferences import learn_profile_weight_hints, summarize_preferences

router = APIRouter()


@router.post("/v1/preferences/hints")
def preference_weight_hints(req: PreferenceHintsRequest) -> dict[str, Any]:
    """Suggest tiny ValueProfile weight deltas from inline labeled events.

    No filesystem paths accepted (path injection). Not calibrated learning.
    """
    profile = safe_profile(req.value_profile, req.profile_name)
    return learn_profile_weight_hints(
        req.events,
        profile_name=req.profile_name or profile.name,
        base_profile=profile,
        max_delta=req.max_delta,
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
    from artificial_curiosity.preferences import suggest_next_pair

    return suggest_next_pair(
        req.candidates,
        req.events,
        profile_name=req.profile_name,
    )
