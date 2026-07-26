"""The ranking surfaces: full pipeline run and instant provoke pack."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from artificial_emotions.api_pkg.schemas import ProvokeRequest, RunRequest, safe_profile
from artificial_emotions.config import get_config
from artificial_emotions.models import CuriosityConfig
from artificial_emotions.pipeline import CuriosityEngine
from artificial_emotions.provoke import provoke

router = APIRouter()


@router.post("/v1/curiosity/run")
def run_curiosity(req: RunRequest) -> dict[str, Any]:
    profile = safe_profile(req.value_profile, req.profile_name)
    cfg = get_config()
    config = CuriosityConfig(
        domain=req.domain,
        topic=req.topic,
        n_return=req.n_return,
        n_candidates=req.n_candidates,
        use_llm=req.use_llm,
        use_literature=req.use_literature,
        literature_backend=req.literature_backend,
        literature_timeout_s=cfg.literature_timeout_s,
        literature_workers=req.literature_workers,
        value_profile=profile,
        llm_model=req.llm_model or "gpt-4o-mini",
        judge_model=req.judge_model,
        judge_ensemble_n=req.judge_ensemble_n,
        # LLM base URL from env only — never from HTTP body (SSRF / key leak).
        diversity_backend=req.diversity_backend,
    )
    results = CuriosityEngine(config).run_dict()
    return {
        "query": req.model_dump(),
        "value_profile": profile.model_dump(mode="json"),
        "literature_backend": req.literature_backend if req.use_literature else "none",
        "count": len(results),
        "questions": results,
        "note": "Scores are decision aids with explicit ValueProfile weights — not oracles.",
    }


@router.post("/v1/curiosity/provoke")
def provoke_post(req: ProvokeRequest) -> dict[str, Any]:
    """Instant curiosity pack — paste `inject` into any model."""
    return provoke(
        domain=req.domain,
        topic=req.topic,
        n=req.n,
        fast=req.fast,
        use_llm=req.use_llm,
        use_literature=req.use_literature,
        value_profile=req.value_profile,
        profile_name=req.profile_name,
        llm_model=req.llm_model,
        judge_model=req.judge_model,
        diversity_backend=req.diversity_backend,
    )


@router.get("/v1/curiosity/provoke")
def provoke_get(
    domain: str = Query("ai"),
    topic: str = Query(""),
    n: int = Query(5, ge=1, le=16),
    fast: bool = Query(True),
    use_llm: bool = Query(False),
    use_literature: bool | None = Query(None),
    llm_model: str | None = Query(None),
    judge_model: str | None = Query(None),
    profile_name: str | None = Query(None),
    diversity_backend: str = Query("jaccard"),
) -> dict[str, Any]:
    """Instant GET spark for curl, browsers, and agents."""
    return provoke(
        domain=domain,
        topic=topic,
        n=n,
        fast=fast,
        use_llm=use_llm,
        use_literature=use_literature,
        profile_name=profile_name,
        llm_model=llm_model,
        judge_model=judge_model,
        diversity_backend=diversity_backend,
    )
