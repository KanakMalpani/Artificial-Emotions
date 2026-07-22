"""FastAPI surface for the curiosity layer."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from artificial_curiosity.models import CuriosityConfig, Domain, ValueProfile
from artificial_curiosity.pipeline import CuriosityEngine

app = FastAPI(
    title="Artificial Curiosity",
    description="Generate and rank valuable unanswered questions.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RunRequest(BaseModel):
    domain: str = Domain.AI.value
    topic: str = ""
    n_return: int = Field(8, ge=1, le=32)
    n_candidates: int = Field(16, ge=4, le=64)
    use_llm: bool = False
    use_literature: bool = True
    value_profile: ValueProfile | None = None


@app.get("/health")
def health() -> dict:
    return {"ok": True, "service": "artificial-curiosity"}


@app.post("/v1/curiosity/run")
def run_curiosity(req: RunRequest) -> dict:
    config = CuriosityConfig(
        domain=req.domain,
        topic=req.topic,
        n_return=req.n_return,
        n_candidates=req.n_candidates,
        use_llm=req.use_llm,
        use_literature=req.use_literature,
        value_profile=req.value_profile or ValueProfile(),
    )
    results = CuriosityEngine(config).run_dict()
    return {
        "query": req.model_dump(),
        "count": len(results),
        "questions": results,
    }


@app.get("/v1/domains")
def domains() -> dict:
    return {"domains": [d.value for d in Domain]}
