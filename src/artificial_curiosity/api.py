"""FastAPI surface for the curiosity layer — usable by humans and any AI agent."""

from __future__ import annotations

import os
import secrets

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware

from artificial_curiosity.agent_tools import openai_tools
from artificial_curiosity.llm import resolve_llm_settings
from artificial_curiosity.models import (
    CuriosityConfig,
    Domain,
    VALUE_PROFILE_PRESETS,
    ValueProfile,
    list_profile_names,
    resolve_value_profile,
)
from artificial_curiosity.pipeline import CuriosityEngine
from artificial_curiosity.provoke import provoke

app = FastAPI(
    title="Artificial Curiosity",
    description=(
        "Curiosity layer API: generate and rank valuable *unanswered* scientific "
        "questions. Designed so any human or AI model/provider can download this "
        "repo, start the server, and instantly ask: what should we investigate next?"
    ),
    version="0.3.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _configured_api_keys() -> set[str]:
    """
    Opt-in HTTP API keys (WO-0.4.6).

    Env (any of):
      CURIOSITY_API_KEY / ARTIFICIAL_CURIOSITY_API_KEY — single key
      CURIOSITY_API_KEYS — comma-separated list

    Empty → auth disabled (local offline demos unchanged).
    """
    keys: set[str] = set()
    for name in ("CURIOSITY_API_KEY", "ARTIFICIAL_CURIOSITY_API_KEY"):
        v = (os.environ.get(name) or "").strip()
        if v:
            keys.add(v)
    multi = (os.environ.get("CURIOSITY_API_KEYS") or "").strip()
    if multi:
        keys.update(k.strip() for k in multi.split(",") if k.strip())
    return keys


_AUTH_OPEN_PATHS = frozenset({"/", "/health", "/docs", "/openapi.json", "/redoc"})


class OptionalApiKeyMiddleware(BaseHTTPMiddleware):
    """When API keys are configured, require Bearer or X-API-Key on protected routes."""

    async def dispatch(self, request: Request, call_next):
        keys = _configured_api_keys()
        if not keys:
            return await call_next(request)
        path = request.url.path
        if path in _AUTH_OPEN_PATHS or path.startswith("/docs") or path.startswith("/redoc"):
            return await call_next(request)
        provided = ""
        auth = request.headers.get("authorization") or ""
        if auth.lower().startswith("bearer "):
            provided = auth[7:].strip()
        if not provided:
            provided = (request.headers.get("x-api-key") or "").strip()
        if not provided or not any(secrets.compare_digest(provided, k) for k in keys):
            return JSONResponse(
                status_code=401,
                content={
                    "detail": (
                        "API key required. Set Authorization: Bearer <key> or "
                        "X-API-Key. Local demos: unset CURIOSITY_API_KEY."
                    )
                },
            )
        return await call_next(request)


app.add_middleware(OptionalApiKeyMiddleware)


class RunRequest(BaseModel):
    domain: str = Domain.AI.value
    topic: str = ""
    n_return: int = Field(8, ge=1, le=32)
    n_candidates: int = Field(16, ge=4, le=64)
    use_llm: bool = False
    use_literature: bool = True
    literature_backend: str = Field(
        "openalex",
        pattern="^(openalex|semantic_scholar|both)$",
        description="Literature adapter (W11)",
    )
    llm_model: str | None = None
    judge_model: str | None = None
    judge_ensemble_n: int = Field(1, ge=1, le=5)
    llm_base_url: str | None = None
    profile_name: str | None = Field(
        None,
        description=f"Named ValueProfile preset: {', '.join(list_profile_names())}",
    )
    value_profile: ValueProfile | None = None
    diversity_backend: str = Field("jaccard", pattern="^(jaccard|embedding)$")
    # Preference JSONL paths are CLI/config-only — not accepted over HTTP (path injection).
    literature_cache_dir: str | None = None


class ProvokeRequest(BaseModel):
    domain: str = Domain.AI.value
    topic: str = ""
    n: int = Field(5, ge=1, le=16)
    fast: bool = Field(
        True,
        description="Skip literature for instant local spark (default). Set false for OpenAlex grounding.",
    )
    use_llm: bool = False
    use_literature: bool | None = None
    llm_model: str | None = None
    judge_model: str | None = None
    llm_base_url: str | None = None
    profile_name: str | None = None
    value_profile: ValueProfile | None = None
    diversity_backend: str = "jaccard"


def _safe_profile(
    value_profile: ValueProfile | None,
    profile_name: str | None,
) -> ValueProfile:
    try:
        return resolve_value_profile(value_profile, profile_name=profile_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/health")
def health() -> dict:
    llm = resolve_llm_settings()
    judge = resolve_llm_settings(judge=True)
    return {
        "ok": True,
        "service": "artificial-curiosity",
        "llm_configured": llm is not None,
        "llm_model": llm.model if llm else None,
        "judge_model": judge.model if judge else None,
        "llm_base_url": llm.base_url if llm else None,
        "profiles": list_profile_names(),
        "api_auth_required": bool(_configured_api_keys()),
    }


@app.get("/")
def root() -> dict:
    return {
        "service": "Artificial Curiosity",
        "tagline": "What should we investigate next?",
        "docs": "/docs",
        "provoke": "GET or POST /v1/curiosity/provoke",
        "run": "POST /v1/curiosity/run",
        "agent": "GET /v1/agent",
        "tools": "GET /v1/agent/tools",
        "profiles": "GET /v1/profiles",
        "mcp": "curiosity-mcp (stdio) or python -m artificial_curiosity.mcp_server",
    }


@app.get("/v1/agent")
def agent_manifest() -> dict:
    """Machine-readable guide for any AI agent or model provider."""
    return {
        "name": "artificial-curiosity",
        "purpose": "Provoke and rank valuable unanswered scientific questions.",
        "not": "A Q&A or search engine. Returns unknowns, not answers.",
        "instant_spark": {
            "method": "GET",
            "path": "/v1/curiosity/provoke",
            "example": "/v1/curiosity/provoke?domain=ai&n=5&fast=true&profile_name=alignment_lab",
            "use": "Paste response.inject into any model context to provoke curiosity.",
        },
        "full_run": {
            "method": "POST",
            "path": "/v1/curiosity/run",
            "body": {
                "domain": "ai",
                "topic": "",
                "n_return": 8,
                "use_literature": True,
                "use_llm": False,
                "profile_name": "humanity_default",
            },
        },
        "openai_tools": {
            "method": "GET",
            "path": "/v1/agent/tools",
            "static_file": "examples/openai_tools.json",
            "use": "Load as function/tool definitions for any OpenAI-compatible agent.",
        },
        "mcp": {
            "transport": "stdio",
            "commands": [
                "curiosity-mcp",
                "python -m artificial_curiosity.mcp_server",
            ],
            "tools": [
                "provoke_curiosity",
                "spark",
                "rank_unknowns",
                "run_curiosity",
                "list_domains",
                "list_profiles",
            ],
            "docs": "docs/PLUGINS.md",
        },
        "value_profiles": {
            "path": "/v1/profiles",
            "presets": list_profile_names(),
            "note": "Rankings are never value-free — pick a named preset or pass value_profile.",
        },
        "any_provider": {
            "protocol": "OpenAI-compatible Chat Completions",
            "env": ["LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL", "LLM_JUDGE_MODEL"],
            "examples": {
                "openai": {
                    "LLM_BASE_URL": "https://api.openai.com/v1",
                    "LLM_MODEL": "gpt-4o-mini",
                    "LLM_JUDGE_MODEL": "gpt-4o-mini",
                },
                "openrouter": {
                    "LLM_BASE_URL": "https://openrouter.ai/api/v1",
                    "LLM_MODEL": "anthropic/claude-sonnet-4",
                },
                "groq": {
                    "LLM_BASE_URL": "https://api.groq.com/openai/v1",
                    "LLM_MODEL": "llama-3.3-70b-versatile",
                },
                "ollama": {
                    "LLM_BASE_URL": "http://localhost:11434/v1",
                    "LLM_MODEL": "llama3.2",
                    "LLM_API_KEY": "local",
                },
            },
        },
        "invariants": [
            "Explicit ValueProfile — no value-free ranking",
            "Related literature ≠ answered",
            "Scores are decision aids, not oracles",
            "Jaccard diversity is default; embedding is optional extras",
        ],
    }


@app.get("/v1/agent/tools")
def agent_tools() -> dict:
    """OpenAI-compatible function-calling tool definitions for any agent."""
    tools = openai_tools()
    return {
        "format": "openai.tools",
        "count": len(tools),
        "tools": tools,
        "note": (
            "Pass `tools` to an OpenAI-compatible chat.completions call. "
            "Implement handlers by calling this API or the Python package "
            "(provoke / CuriosityEngine). Scores are decision aids, not oracles."
        ),
        "http_fallbacks": {
            "provoke_curiosity": "GET|POST /v1/curiosity/provoke",
            "rank_unknowns": "POST /v1/curiosity/run",
            "list_domains": "GET /v1/domains",
            "list_profiles": "GET /v1/profiles",
        },
    }


@app.get("/v1/domains")
def domains() -> dict:
    return {"domains": [d.value for d in Domain]}


@app.get("/v1/profiles")
def profiles() -> dict:
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


@app.post("/v1/curiosity/run")
def run_curiosity(req: RunRequest) -> dict:
    profile = _safe_profile(req.value_profile, req.profile_name)
    config = CuriosityConfig(
        domain=req.domain,
        topic=req.topic,
        n_return=req.n_return,
        n_candidates=req.n_candidates,
        use_llm=req.use_llm,
        use_literature=req.use_literature,
        literature_backend=req.literature_backend,
        literature_cache_dir=req.literature_cache_dir,
        value_profile=profile,
        llm_model=req.llm_model or "gpt-4o-mini",
        judge_model=req.judge_model,
        judge_ensemble_n=req.judge_ensemble_n,
        llm_base_url=req.llm_base_url,
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


@app.post("/v1/curiosity/provoke")
def provoke_post(req: ProvokeRequest) -> dict:
    """Instant curiosity pack — paste `inject` into any model."""
    try:
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
            llm_base_url=req.llm_base_url,
            diversity_backend=req.diversity_backend,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/v1/curiosity/provoke")
def provoke_get(
    domain: str = Query("ai"),
    topic: str = Query(""),
    n: int = Query(5, ge=1, le=16),
    fast: bool = Query(True),
    use_llm: bool = Query(False),
    use_literature: bool | None = Query(None),
    llm_model: str | None = Query(None),
    judge_model: str | None = Query(None),
    llm_base_url: str | None = Query(None),
    profile_name: str | None = Query(None),
    diversity_backend: str = Query("jaccard"),
) -> dict:
    """Instant GET spark for curl, browsers, and agents."""
    try:
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
            llm_base_url=llm_base_url,
            diversity_backend=diversity_backend,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
