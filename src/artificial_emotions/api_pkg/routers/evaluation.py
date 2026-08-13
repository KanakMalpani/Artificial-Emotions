"""Offline eval, critique, and worksheet endpoints.

Common contract across this router: nothing here re-ranks. These are
annotation, critique, and template-fill surfaces. Heavy imports stay inside the
handlers so importing the app does not pull in every eval module.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from artificial_emotions.api_pkg.schemas import (
    CritiqueBriefRequest,
    CrossModelVoteRequest,
    DecomposeRequest,
    ExploreRequest,
    IdeaGraphRequest,
    SoundnessPassRequest,
    SurpriseWorksheetRequest,
    VoiWorksheetRequest,
)

router = APIRouter()


@router.post("/v1/evals/cross-model-vote")
def evals_cross_model_vote(req: CrossModelVoteRequest) -> dict[str, Any]:
    """Offline keep/drop/rewrite annotations — does not re-rank."""
    from artificial_emotions.hybrid_vote import cross_model_vote

    return cross_model_vote(req.candidates, judges=req.judges)


@router.post("/v1/evals/idea-graph")
def evals_idea_graph(req: IdeaGraphRequest) -> dict[str, Any]:
    """EIG-inspired idea graph export — display only."""
    from artificial_emotions.idea_graph import export_idea_graph

    return export_idea_graph(
        req.candidates,
        similarity_threshold=req.similarity_threshold,
    )


@router.post("/v1/evals/soundness")
def evals_soundness(req: SoundnessPassRequest) -> dict[str, Any]:
    """Offline soundness pass on briefs — does not re-rank."""
    from artificial_emotions.soundness import soundness_pass

    return soundness_pass(req.candidates)


@router.post("/v1/surprise/worksheet")
def surprise_worksheet(req: SurpriseWorksheetRequest) -> dict[str, Any]:
    """Belief-shift worksheet fill — not EVSI, not axis rename."""
    from artificial_emotions.bayesian import fill_surprise_worksheet

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
    from artificial_emotions.critique import critique_brief

    return critique_brief(
        question=req.question,
        operationalization=req.operationalization,
        brief=req.brief,
        why_it_matters=req.why_it_matters,
    )


@router.post("/v1/voi/worksheet")
def voi_worksheet(req: VoiWorksheetRequest) -> dict[str, Any]:
    """Fill VOI worksheet metadata — not computed EVSI/ENBS."""
    from artificial_emotions.voi import fill_voi_worksheet

    return fill_voi_worksheet(
        question_id=req.question_id,
        question=req.question,
        operationalization=req.operationalization,
        profile_name=req.profile_name,
        domain=req.domain,
    )


@router.post("/v1/curiosity/decompose")
def curiosity_decompose(req: DecomposeRequest) -> dict[str, Any]:
    """Open one unknown into sub-questions, a first step, falsifiers, and stop rules.

    Returns questions and tests only — it does not answer the question and
    asserts no hypothesis.
    """
    from artificial_emotions.decompose import decompose_question
    from artificial_emotions.models import UnansweredQuestion

    q = UnansweredQuestion(
        id="decompose-request",
        question=req.question,
        domain=req.domain,
        operationalization=req.operationalization,
        why_it_matters="Supplied for decomposition.",
    )
    return decompose_question(
        q,
        depth=req.depth,
        answerability=req.answerability,
        tractability=req.tractability,
        risk=req.risk,
    )


@router.post("/v1/curiosity/explore")
def curiosity_explore(req: ExploreRequest) -> dict[str, Any]:
    """Run the curiosity loop and return the full trajectory.

    Each step appraises what it found, feels something because of it, lets that
    change how it searches next, and remembers where it has been. Everything it
    felt and everything that feeling changed is in the response.
    """
    from artificial_emotions.explore import explore

    return explore(
        domain=req.domain,
        topic=req.topic,
        steps=req.steps,
        n_return=req.n_return,
        profile_name=req.profile_name,
        use_literature=req.use_literature,
        allow_weight_deltas=req.allow_weight_deltas,
        somatic_modulate=req.somatic_modulate,
        allow_domain_jump=req.allow_domain_jump,
        decompose_depth=req.decompose_depth,
    )
