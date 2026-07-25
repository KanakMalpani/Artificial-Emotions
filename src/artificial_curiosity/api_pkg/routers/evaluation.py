"""Offline eval, critique, and worksheet endpoints.

Common contract across this router: nothing here re-ranks. These are
annotation, critique, and template-fill surfaces. Heavy imports stay inside the
handlers so importing the app does not pull in every eval module.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from artificial_curiosity.api_pkg.schemas import (
    CritiqueBriefRequest,
    CrossModelVoteRequest,
    IdeaGraphRequest,
    SoundnessPassRequest,
    SurpriseWorksheetRequest,
    VoiWorksheetRequest,
)

router = APIRouter()


@router.post("/v1/evals/cross-model-vote")
def evals_cross_model_vote(req: CrossModelVoteRequest) -> dict[str, Any]:
    """Offline keep/drop/rewrite annotations — does not re-rank."""
    from artificial_curiosity.hybrid_vote import cross_model_vote

    return cross_model_vote(req.candidates, judges=req.judges)


@router.post("/v1/evals/idea-graph")
def evals_idea_graph(req: IdeaGraphRequest) -> dict[str, Any]:
    """EIG-inspired idea graph export — display only."""
    from artificial_curiosity.idea_graph import export_idea_graph

    return export_idea_graph(
        req.candidates,
        similarity_threshold=req.similarity_threshold,
    )


@router.post("/v1/evals/soundness")
def evals_soundness(req: SoundnessPassRequest) -> dict[str, Any]:
    """Offline soundness pass on briefs — does not re-rank."""
    from artificial_curiosity.soundness import soundness_pass

    return soundness_pass(req.candidates)


@router.post("/v1/surprise/worksheet")
def surprise_worksheet(req: SurpriseWorksheetRequest) -> dict[str, Any]:
    """Belief-shift worksheet fill — not EVSI, not axis rename."""
    from artificial_curiosity.bayesian import fill_surprise_worksheet

    return fill_surprise_worksheet(
        question_id=req.question_id,
        profile_name=req.profile_name,
        predicted_surprise=req.predicted_surprise,
        pilot_result=req.pilot_result,
        belief_shift_1_to_5=req.belief_shift_1_to_5,
        crude_update_note=req.crude_update_note,
    )


@router.post("/v1/briefs/critique")
def briefs_critique(req: CritiqueBriefRequest) -> dict[str, Any]:
    """Form-only brief critic — does not change ranks or strip dual-use."""
    from artificial_curiosity.critique import critique_brief

    return critique_brief(
        question=req.question,
        operationalization=req.operationalization,
        brief=req.brief,
        why_it_matters=req.why_it_matters,
    )


@router.post("/v1/voi/worksheet")
def voi_worksheet(req: VoiWorksheetRequest) -> dict[str, Any]:
    """Fill VOI worksheet metadata — not computed EVSI/ENBS."""
    from artificial_curiosity.voi import fill_voi_worksheet

    return fill_voi_worksheet(
        question_id=req.question_id,
        question=req.question,
        operationalization=req.operationalization,
        profile_name=req.profile_name,
        domain=req.domain,
    )
