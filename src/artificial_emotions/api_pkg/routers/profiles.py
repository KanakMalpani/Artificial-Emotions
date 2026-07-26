"""ValueProfile listing and side-by-side comparison.

Comparison never merges two profiles into a consensus score — it shows both
rank orders and their disagreement.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from artificial_emotions.api_pkg.schemas import (
    CompareProfilesRequest,
    ConstitutionCompareRequest,
)
from artificial_emotions.compare import compare_constitution as compare_constitution_fn
from artificial_emotions.compare import compare_profiles as compare_profiles_fn
from artificial_emotions.models import VALUE_PROFILE_PRESETS

router = APIRouter()


@router.get("/v1/profiles")
def profiles() -> dict[str, Any]:
    """List named ValueProfile presets (F11 — no value-free ranking)."""
    return {
        "presets": [
            {
                "name": name,
                "description": p.description,
                "time_horizon_years": p.time_horizon_years,
                "max_risk": p.max_risk,
                "min_answerability": p.min_answerability,
                "weights": {
                    "impact": p.weight_impact,
                    "neglectedness": p.weight_neglectedness,
                    "tractability": p.weight_tractability,
                    "surprise": p.weight_surprise,
                },
            }
            for name, p in sorted(VALUE_PROFILE_PRESETS.items())
        ],
        "note": (
            "Pass profile_name to provoke/run, or a full value_profile object. "
            "There is no neutral / value-free ranking mode."
        ),
    }


@router.post("/v1/profiles/compare")
def profiles_compare(req: CompareProfilesRequest) -> dict[str, Any]:
    """Side-by-side offline ranks under two ValueProfiles — no silent merge."""
    return compare_profiles_fn(
        domain=req.domain,
        topic=req.topic,
        profile_a=req.profile_a,
        profile_b=req.profile_b,
        n=req.n,
        n_candidates=req.n_candidates,
    )


@router.post("/v1/profiles/constitution-compare")
def profiles_constitution_compare(req: ConstitutionCompareRequest) -> dict[str, Any]:
    """Constitution stack compare + hard risk veto — no consensus merge."""
    return compare_constitution_fn(
        domain=req.domain,
        topic=req.topic,
        primary_profile=req.primary_profile,
        veto_profile=req.veto_profile,
        n=req.n,
        n_candidates=req.n_candidates,
    )
