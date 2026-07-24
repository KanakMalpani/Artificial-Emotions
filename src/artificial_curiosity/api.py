"""FastAPI surface for the curiosity layer — usable by humans and any AI agent."""

from __future__ import annotations

import posixpath
import secrets
from typing import Any
from urllib.parse import unquote, urlparse

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from starlette.middleware.base import BaseHTTPMiddleware

from artificial_curiosity import __version__
from artificial_curiosity.agent_tools import mcp_tool_tiers, openai_tools
from artificial_curiosity.config import (
    clear_config_cache,
    configured_api_keys,
    cors_origins,
    get_config,
)
from artificial_curiosity.emotions import (
    annotate_epistemic,
    elicit_helpers,
    emotion_catalog,
    emotion_pack,
    list_epistemic_cues,
    mix_emotions,
)
from artificial_curiosity.errors import (
    ERR_AUTH_REQUIRED,
    ERR_INTERNAL,
    ERR_VALIDATION,
    CuriosityError,
    classify_value_error,
    error_payload,
)
from artificial_curiosity.llm import resolve_llm_settings
from artificial_curiosity.logutil import get_logger
from artificial_curiosity.models import (
    VALUE_PROFILE_PRESETS,
    CuriosityConfig,
    Domain,
    ValueProfile,
    list_profile_names,
    resolve_value_profile,
)
from artificial_curiosity.pipeline import CuriosityEngine
from artificial_curiosity.preferences import learn_profile_weight_hints, summarize_preferences
from artificial_curiosity.provoke import provoke
from artificial_curiosity.compare import (
    compare_constitution as compare_constitution_fn,
    compare_profiles as compare_profiles_fn,
)

logger = get_logger("api")

app = FastAPI(
    title="Artificial Curiosity",
    description=(
        "Curiosity layer API: generate and rank valuable *unanswered* scientific "
        "questions. Designed so any human or AI model/provider can download this "
        "repo, start the server, and instantly ask: what should we investigate next?"
    ),
    version=__version__,
)

_origins = cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=("*" not in _origins),
    allow_methods=["*"],
    allow_headers=["*"],
)


_AUTH_OPEN_PATHS = frozenset({"/", "/health", "/ready", "/docs", "/openapi.json", "/redoc"})


def _normalize_request_path(path: str) -> str:
    """Normalize path for auth open-list checks (decode, collapse ``..`` / ``//``)."""
    raw = unquote(path or "/")
    if not raw.startswith("/"):
        raw = "/" + raw
    norm = posixpath.normpath(raw)
    if not norm.startswith("/"):
        norm = "/" + norm
    return norm


def _is_auth_open_path(path: str) -> bool:
    """Exact open paths, plus safe ``/docs/`` and ``/redoc/`` prefixes only."""
    p = _normalize_request_path(path)
    if p in _AUTH_OPEN_PATHS:
        return True
    # Trailing-slash prefixes avoid ``startswith("/docs")`` matching ``/docsEvil``.
    return p.startswith("/docs/") or p.startswith("/redoc/")


def _api_key_matches(provided: str, keys: set[str]) -> bool:
    """Constant-time key check; never raises on length/type mismatch (always → fail closed)."""
    if not provided or not isinstance(provided, str):
        return False
    for key in keys:
        if not isinstance(key, str):
            continue
        try:
            if secrets.compare_digest(provided, key):
                return True
        except (TypeError, ValueError):
            continue
    return False


def _redact_base_url(url: str | None) -> str | None:
    """Expose scheme only — never leak host/path from unauthenticated ``/health``."""
    if not url:
        return None
    parsed = urlparse(url)
    if parsed.scheme:
        return f"{parsed.scheme}://[redacted]"
    return "[redacted]"


class OptionalApiKeyMiddleware(BaseHTTPMiddleware):
    """When API keys are configured, require Bearer or X-API-Key on protected routes."""

    async def dispatch(self, request: Request, call_next):
        keys = configured_api_keys()
        if not keys:
            return await call_next(request)
        if _is_auth_open_path(request.url.path):
            return await call_next(request)
        provided = ""
        auth = request.headers.get("authorization") or ""
        if auth.lower().startswith("bearer "):
            provided = auth[7:].strip()
        if not provided:
            provided = (request.headers.get("x-api-key") or "").strip()
        if not _api_key_matches(provided, keys):
            return JSONResponse(
                status_code=401,
                content=error_payload(
                    ERR_AUTH_REQUIRED,
                    (
                        "API key required. Set Authorization: Bearer <key> or "
                        "X-API-Key. Local demos: unset CURIOSITY_API_KEY."
                    ),
                ),
            )
        return await call_next(request)


app.add_middleware(OptionalApiKeyMiddleware)


def _http_error_response(exc: CuriosityError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.http_status,
        content={"error": exc.to_dict(), "detail": exc.message},
    )


@app.exception_handler(CuriosityError)
async def curiosity_error_handler(_request: Request, exc: CuriosityError) -> JSONResponse:
    return _http_error_response(exc)


@app.exception_handler(ValueError)
async def value_error_handler(_request: Request, exc: ValueError) -> JSONResponse:
    return _http_error_response(classify_value_error(exc))


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=error_payload(
            ERR_VALIDATION,
            "Request validation failed",
            details={"errors": exc.errors()},
        ),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict) and "error" in detail:
        return JSONResponse(status_code=exc.status_code, content=detail)
    message = detail if isinstance(detail, str) else str(detail)
    code = ERR_AUTH_REQUIRED if exc.status_code == 401 else ERR_VALIDATION
    if exc.status_code >= 500:
        code = ERR_INTERNAL
    body = error_payload(code, message)
    body["detail"] = message
    return JSONResponse(status_code=exc.status_code, content=body)


class RunRequest(BaseModel):
    domain: str = Field(
        Domain.AI.value,
        examples=["ai", "biology", "climate"],
        description="Domain key for seed pool / packs",
    )
    topic: str = Field("", examples=["aging biomarkers", "sandbagging evals"])
    n_return: int = Field(8, ge=1, le=32, examples=[5, 8])
    n_candidates: int = Field(16, ge=4, le=64)
    use_llm: bool = False
    use_literature: bool = True
    literature_backend: str = Field(
        "openalex",
        pattern="^(openalex|semantic_scholar|both)$",
        description="Literature adapter (W11)",
        examples=["openalex", "both"],
    )
    llm_model: str | None = None
    judge_model: str | None = None
    judge_ensemble_n: int = Field(1, ge=1, le=5)
    # llm_base_url / literature_cache_dir are env/CLI-only (SSRF + path injection).
    literature_workers: int = Field(
        4,
        ge=1,
        le=16,
        description="Parallel literature fetches when use_literature=true (1=serial)",
        examples=[1, 4],
    )
    profile_name: str | None = Field(
        None,
        description=f"Named ValueProfile preset: {', '.join(list_profile_names())}",
        examples=["humanity_default", "alignment_lab", "climate_adaptation"],
    )
    value_profile: ValueProfile | None = None
    diversity_backend: str = Field("jaccard", pattern="^(jaccard|embedding)$")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "domain": "ai",
                    "topic": "",
                    "n_return": 8,
                    "n_candidates": 16,
                    "use_llm": False,
                    "use_literature": True,
                    "literature_backend": "openalex",
                    "literature_workers": 4,
                    "profile_name": "alignment_lab",
                    "diversity_backend": "jaccard",
                }
            ]
        }
    }


class ProvokeRequest(BaseModel):
    domain: str = Domain.AI.value
    topic: str = ""
    n: int = Field(5, ge=1, le=16)
    fast: bool = Field(
        True,
        description=(
            "Skip literature for instant local spark (default). Set false for OpenAlex grounding."
        ),
    )
    use_llm: bool = False
    use_literature: bool | None = None
    llm_model: str | None = None
    judge_model: str | None = None
    # llm_base_url is env/CLI-only — never accept client URLs (SSRF / key leak).
    profile_name: str | None = None
    value_profile: ValueProfile | None = None
    diversity_backend: str = Field("jaccard", pattern="^(jaccard|embedding)$")


class PreferenceHintsRequest(BaseModel):
    """Inline preference events → tiny ValueProfile weight hints (no filesystem paths)."""

    events: list[dict[str, Any]] = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Labeled prefer/reject events with score_axes",
        examples=[
            [
                {
                    "event_type": "prefer",
                    "profile_name": "humanity_default",
                    "question_id": "ai-01",
                    "score_axes": {
                        "impact": 0.8,
                        "neglectedness": 0.7,
                        "tractability": 0.4,
                        "surprise": 0.6,
                    },
                },
                {
                    "event_type": "reject",
                    "profile_name": "humanity_default",
                    "question_id": "ai-02",
                    "score_axes": {
                        "impact": 0.4,
                        "neglectedness": 0.3,
                        "tractability": 0.8,
                        "surprise": 0.3,
                    },
                },
            ]
        ],
    )
    profile_name: str | None = Field(
        "humanity_default",
        description=f"Named ValueProfile preset: {', '.join(list_profile_names())}",
    )
    value_profile: ValueProfile | None = None
    max_delta: float = Field(0.08, ge=0.01, le=0.2)


class PreferenceSummarizeRequest(BaseModel):
    """Inline preference events → counts / pairwise wins / hints (no filesystem paths)."""

    events: list[dict[str, Any]] = Field(..., min_length=1, max_length=2000)
    profile_name: str | None = None
    top_k: int = Field(10, ge=1, le=50)


class CompareProfilesRequest(BaseModel):
    domain: str = Domain.AI.value
    topic: str = ""
    profile_a: str = Field("humanity_default", examples=["humanity_default", "funder_10y"])
    profile_b: str = Field("alignment_lab", examples=["alignment_lab", "climate_adaptation"])
    n: int = Field(8, ge=1, le=32)
    n_candidates: int = Field(16, ge=4, le=64)


class ConstitutionCompareRequest(BaseModel):
    domain: str = Domain.AI.value
    topic: str = ""
    primary_profile: str | None = Field(
        None, description="Override stack primary; default from constitution JSON"
    )
    veto_profile: str | None = Field(
        None,
        description="Override safety veto; default from stack or public_demo_strict_risk",
    )
    n: int = Field(8, ge=1, le=32)
    n_candidates: int = Field(16, ge=4, le=64)


class CritiqueBriefRequest(BaseModel):
    question: str = ""
    operationalization: str = ""
    brief: str = ""
    why_it_matters: str = ""


class VoiWorksheetRequest(BaseModel):
    question_id: str | None = None
    question: str = ""
    operationalization: str = ""
    profile_name: str | None = None
    domain: str = ""


class SuggestPairRequest(BaseModel):
    candidates: list[dict[str, Any]] = Field(
        ...,
        min_length=2,
        description="Top-k ranked unknowns with question_id / rank / curiosity_score",
    )
    events: list[dict[str, Any]] = Field(default_factory=list)
    profile_name: str | None = "humanity_default"


class CrossModelVoteRequest(BaseModel):
    candidates: list[dict[str, Any]] = Field(..., min_length=1)
    judges: int = Field(1, ge=1, le=6)


class AnnotateEmotionsRequest(BaseModel):
    question: str = Field(..., min_length=12)
    gap_status: str = Field(
        "unanswered",
        description="unanswered | partially_answered | likely_answered | unknown_with_caveat",
    )
    surprise: float = Field(0.5, ge=0.0, le=1.0)
    neglectedness: float = Field(0.5, ge=0.0, le=1.0)
    answerability: float = Field(0.5, ge=0.0, le=1.0)
    notes: str = ""
    domain: str = Domain.AI.value


class MixEmotionsRequest(BaseModel):
    """Percentage or weight mix over catalog emotion ids (normalized to sum=1)."""

    weights: dict[str, float] = Field(
        ...,
        description=(
            "Map of emotion_id → percent (e.g. 40) or weight (e.g. 0.4). "
            "Normalized to sum 1.0. Example: "
            '{"curiosity": 40, "confusion": 30, "awe": 30}'
        ),
        min_length=1,
    )
    profile_name: str | None = Field(
        None,
        description="Optional ValueProfile for mix_intensity_cap (e.g. public_demo_strict_risk)",
    )
    mix_intensity_cap: float | None = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Override non-epistemic mix mass cap (None → profile default)",
    )
    simulate_feeling: bool = Field(
        True,
        description="Include felt_simulation (PAD mood, intensity, and first-person prose) in response",
    )

    @field_validator("weights")
    @classmethod
    def _weights_must_be_numeric(cls, v: dict[str, Any]) -> dict[str, float]:
        if not v:
            raise ValueError("weights must contain at least one emotion_id")
        out: dict[str, float] = {}
        for key, val in v.items():
            kid = str(key).strip()
            if not kid:
                raise ValueError("empty emotion id in weights")
            try:
                out[kid] = float(val)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"weight for '{kid}' must be a number, got {val!r}") from exc
        return out


class IdeaGraphRequest(BaseModel):
    candidates: list[dict[str, Any]] = Field(..., min_length=1)
    similarity_threshold: float = Field(0.28, ge=0.0, le=1.0)


class SoundnessPassRequest(BaseModel):
    candidates: list[dict[str, Any]] = Field(..., min_length=1)


class SurpriseWorksheetRequest(BaseModel):
    question_id: str | None = None
    profile_name: str | None = None
    predicted_surprise: float | None = Field(None, ge=0.0, le=1.0)
    pilot_result: str = ""
    belief_shift_1_to_5: int | None = Field(None, ge=1, le=5)
    crude_update_note: str = ""


def _safe_profile(
    value_profile: ValueProfile | None,
    profile_name: str | None,
) -> ValueProfile:
    try:
        return resolve_value_profile(value_profile, profile_name=profile_name)
    except ValueError as exc:
        raise classify_value_error(exc) from exc


@app.get("/health")
def health() -> dict[str, Any]:
    """Liveness + config summary (safe; no secrets)."""
    clear_config_cache()
    cfg = get_config()
    llm = resolve_llm_settings()
    judge = resolve_llm_settings(judge=True)
    return {
        "ok": True,
        "service": "artificial-curiosity",
        "version": cfg.version,
        "status": "alive",
        "llm_configured": llm is not None,
        "llm_model": llm.model if llm else None,
        "judge_model": judge.model if judge else None,
        "llm_base_url": _redact_base_url(llm.base_url if llm else None),
        "llm_timeout_s": cfg.llm_timeout_s,
        "literature_timeout_s": cfg.literature_timeout_s,
        "s2_key_configured": cfg.s2_configured,
        "profiles": list_profile_names(),
        "api_auth_required": cfg.api_auth_required,
        "cors_origins": list(cfg.cors_origins),
    }


@app.get("/ready")
def ready() -> JSONResponse:
    """Readiness: process can serve offline spark (no network required).

    Returns HTTP 503 when checks fail so load balancers stop routing traffic.
    """
    clear_config_cache()
    cfg = get_config()
    checks: dict[str, bool] = {
        "package_import": True,
        "emotion_catalog": False,
        "profiles": False,
    }
    try:
        cat = emotion_catalog()
        checks["emotion_catalog"] = cat.get("count", 0) >= 1
    except Exception as exc:  # noqa: BLE001
        logger.warning("readiness emotion_catalog check failed: %s", exc)
    try:
        checks["profiles"] = len(list_profile_names()) >= 1
    except Exception as exc:  # noqa: BLE001
        logger.warning("readiness profiles check failed: %s", exc)
    ok = all(checks.values())
    body = {
        "ok": ok,
        "ready": ok,
        "service": "artificial-curiosity",
        "version": cfg.version,
        "checks": checks,
        "note": ("Ready means offline spark/emotions work. Literature/LLM remain optional."),
    }
    return JSONResponse(status_code=200 if ok else 503, content=body)


@app.get("/")
def root() -> dict[str, Any]:
    return {
        "service": "Artificial Curiosity",
        "version": __version__,
        "tagline": "What should we investigate next?",
        "docs": "/docs",
        "health": "/health",
        "ready": "/ready",
        "provoke": "GET or POST /v1/curiosity/provoke",
        "run": "POST /v1/curiosity/run",
        "emotions": (
            "GET /v1/emotions/cues · GET /v1/emotions/catalog · "
            "POST /v1/emotions/mix · POST /v1/emotions/annotate · "
            "GET /v1/emotions/elicit · GET /v1/emotions/pack"
        ),
        "epistemic": "Alias of /v1/emotions/* (same handlers)",
        "agent": "GET /v1/agent",
        "tools": "GET /v1/agent/tools",
        "profiles": "GET /v1/profiles",
        "preferences": (
            "POST /v1/preferences/hints · POST /v1/preferences/summarize "
            "(inline events; no filesystem paths)"
        ),
        "compare_profiles": "POST /v1/profiles/compare",
        "mcp": "curiosity-mcp (stdio) or python -m artificial_curiosity.mcp_server",
        "config": "artificial_curiosity.config / .env.example",
        "safety": (
            "Not biometric emotion recognition. Emotion mix/cues are UX annotations. "
            "Provoke is opt-in investigation framing. Scores need explicit ValueProfile — "
            "decision aids, not oracles. See docs/LIMITS.md."
        ),
    }


@app.get("/v1/agent")
def agent_manifest() -> dict[str, Any]:
    """Machine-readable guide for any AI agent or model provider."""
    return {
        "name": "artificial-curiosity",
        "version": __version__,
        "purpose": (
            "Ranks valuable unanswered questions under an explicit ValueProfile; "
            "verifies literature neighborhoods without equating related work with "
            "answered questions; returns briefs and optional provoke inject packs."
        ),
        "card": (
            "Artificial Curiosity ranks valuable unanswered questions under an "
            "explicit ValueProfile. Scores and epistemic cues are decision aids / "
            "UX annotations — not oracles, EVSI, emotion recognition, or proof the "
            "system feels curious. Co-scientist upstream layer — not a replacement "
            "for human judgment or closed-loop labs."
        ),
        "not": (
            "A Q&A or search engine. Not biometric emotion recognition. "
            "Returns unknowns, not answers; emotion mix/cues are UX annotations only."
        ),
        "honesty": [
            "Requires / surfaces ValueProfile (no value-free ranking — McNamara/hivemind)",
            "Gap verify: related ≠ answered",
            "Scores: proxies, not EVSI/ENBS or scientific priority truth",
            "Emotion mixes: computational_affect (PAD + felt_simulation) — not biometric ERS (EU AI Act)",
            "Dual-use risk filters: heuristics, not biosecurity authority",
            "Provoke: investigation framing for agents/humans — not persuasion toolkit",
            "Read curiosity://limits / docs/LIMITS.md before treating ranks as truth",
        ],
        "resources_first": ["curiosity://limits", "curiosity://profiles", "curiosity://domains"],
        "safety": (
            "Cues and emotion mixes are authoring/framing annotations — the software "
            "does not feel and does not infer user affect from biometrics. Provoke is "
            "opt-in investigation framing, not persuasion tooling. Always pass an "
            "explicit ValueProfile; scores are decision aids with bands, not oracles. "
            "Read curiosity://limits or docs/LIMITS.md before treating ranks as truth."
        ),
        "instant_spark": {
            "method": "GET",
            "path": "/v1/curiosity/provoke",
            "example": ("/v1/curiosity/provoke?domain=ai&n=5&fast=true&profile_name=alignment_lab"),
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
        "compare_profiles": {
            "method": "POST",
            "path": "/v1/profiles/compare",
            "body": {
                "domain": "ai",
                "profile_a": "humanity_default",
                "profile_b": "alignment_lab",
                "n": 8,
            },
            "note": "Side-by-side ranks — never a silent consensus merge.",
        },
        "constitution_compare": {
            "method": "POST",
            "path": "/v1/profiles/constitution-compare",
            "note": (
                "Primary vs safety-veto ranks + hard max_risk flag/drop — "
                "not a constitutional optimum."
            ),
        },
        "critique_brief": {
            "method": "POST",
            "path": "/v1/briefs/critique",
            "note": "Form-only critic — does not re-rank.",
        },
        "voi_worksheet": {
            "method": "POST",
            "path": "/v1/voi/worksheet",
            "note": "Template fill only — not computed EVSI.",
        },
        "surprise_worksheet": {
            "method": "POST",
            "path": "/v1/surprise/worksheet",
            "note": "Belief-shift logging only — not EVSI, not ScoreAxes.surprise rename.",
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
                "compare_profiles",
                "constitution_compare",
                "critique_brief",
                "voi_worksheet",
                "surprise_worksheet",
                "cross_model_vote",
                "export_idea_graph",
                "soundness_pass",
                "list_epistemic_cues",
                "emotion_catalog",
                "mix_emotions",
                "annotate_epistemic",
                "emotion_pack",
                "elicit_helpers",
            ],
            "tool_tiers": mcp_tool_tiers(),
            "docs": "docs/PLUGINS.md",
        },
        "emotions": {
            "path": "/v1/emotions/cues",
            "catalog": "GET /v1/emotions/catalog",
            "mix": "POST /v1/emotions/mix",
            "annotate": "POST /v1/emotions/annotate",
            "elicit": "GET /v1/emotions/elicit",
            "pack": "GET /v1/emotions/pack?name=affective_science",
            "alias": "/v1/epistemic/*",
            "docs": "docs/EMOTIONS.md",
            "note": (
                "Epistemic UX annotations + mixable catalog — "
                "not claims that the system feels emotions."
            ),
        },
        "value_profiles": {
            "path": "/v1/profiles",
            "presets": list_profile_names(),
            "note": ("Rankings are never value-free — pick a named preset or pass value_profile."),
        },
        "any_provider": {
            "protocol": "OpenAI-compatible Chat Completions",
            "env": [
                "LLM_API_KEY",
                "LLM_BASE_URL",
                "LLM_MODEL",
                "LLM_JUDGE_MODEL",
                "LLM_TIMEOUT_S",
                "CURIOSITY_API_KEY",
            ],
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
            "Emotion mixes produce computational felt_simulation (PAD mood + intensity)",
            "Jaccard diversity is default; embedding is optional extras",
        ],
        "error_shape": {
            "body": {"error": {"code": "string", "message": "string", "details": {}}},
            "docs": "artificial_curiosity.errors",
        },
    }


@app.get("/v1/agent/tools")
def agent_tools() -> dict[str, Any]:
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
            "list_epistemic_cues": "GET /v1/emotions/cues",
            "emotion_catalog": "GET /v1/emotions/catalog",
            "mix_emotions": "POST /v1/emotions/mix",
            "annotate_epistemic": "POST /v1/emotions/annotate",
            "emotion_pack": "GET /v1/emotions/pack",
            "elicit_helpers": "GET /v1/emotions/elicit",
        },
    }


@app.get("/v1/domains")
def domains() -> dict[str, Any]:
    return {"domains": [d.value for d in Domain]}


@app.get("/v1/profiles")
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


@app.post("/v1/curiosity/run")
def run_curiosity(req: RunRequest) -> dict[str, Any]:
    profile = _safe_profile(req.value_profile, req.profile_name)
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


@app.post("/v1/preferences/hints")
def preference_weight_hints(req: PreferenceHintsRequest) -> dict[str, Any]:
    """Suggest tiny ValueProfile weight deltas from inline labeled events.

    No filesystem paths accepted (path injection). Not calibrated learning.
    """
    profile = _safe_profile(req.value_profile, req.profile_name)
    return learn_profile_weight_hints(
        req.events,
        profile_name=req.profile_name or profile.name,
        base_profile=profile,
        max_delta=req.max_delta,
    )


@app.post("/v1/preferences/summarize")
def preference_summarize(req: PreferenceSummarizeRequest) -> dict[str, Any]:
    """Counts, pairwise wins, and weight hints from inline events (no paths)."""
    return summarize_preferences(
        req.events,
        profile_name=req.profile_name,
        top_k=req.top_k,
    )


@app.post("/v1/preferences/suggest-pair")
def preference_suggest_pair(req: SuggestPairRequest) -> dict[str, Any]:
    """Propose next pairwise duel among top-k — not BT weight overwrite."""
    from artificial_curiosity.preferences import suggest_next_pair

    return suggest_next_pair(
        req.candidates,
        req.events,
        profile_name=req.profile_name,
    )


@app.post("/v1/evals/cross-model-vote")
def evals_cross_model_vote(req: CrossModelVoteRequest) -> dict[str, Any]:
    """Offline keep/drop/rewrite annotations — does not re-rank."""
    from artificial_curiosity.hybrid_vote import cross_model_vote

    return cross_model_vote(req.candidates, judges=req.judges)


@app.post("/v1/evals/idea-graph")
def evals_idea_graph(req: IdeaGraphRequest) -> dict[str, Any]:
    """EIG-inspired idea graph export — display only."""
    from artificial_curiosity.idea_graph import export_idea_graph

    return export_idea_graph(
        req.candidates,
        similarity_threshold=req.similarity_threshold,
    )


@app.post("/v1/evals/soundness")
def evals_soundness(req: SoundnessPassRequest) -> dict[str, Any]:
    """Offline soundness pass on briefs — does not re-rank."""
    from artificial_curiosity.soundness import soundness_pass

    return soundness_pass(req.candidates)


@app.post("/v1/surprise/worksheet")
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


@app.post("/v1/profiles/compare")
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


@app.post("/v1/profiles/constitution-compare")
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


@app.post("/v1/briefs/critique")
def briefs_critique(req: CritiqueBriefRequest) -> dict[str, Any]:
    """Form-only brief critic — does not change ranks or strip dual-use."""
    from artificial_curiosity.critique import critique_brief

    return critique_brief(
        question=req.question,
        operationalization=req.operationalization,
        brief=req.brief,
        why_it_matters=req.why_it_matters,
    )


@app.post("/v1/voi/worksheet")
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


@app.post("/v1/curiosity/provoke")
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


# ---------------------------------------------------------------------------
# Emotions / epistemic cues (UX annotations — not a CME)
# Aliases under /v1/epistemic/* for discoverability.
# ---------------------------------------------------------------------------


def _emotions_cues() -> dict[str, Any]:
    return list_epistemic_cues()


def _emotions_catalog(family: str | None = None) -> dict[str, Any]:
    return emotion_catalog(family=family)


def _emotions_mix(req: MixEmotionsRequest) -> dict[str, Any]:
    return mix_emotions(
        req.weights,
        profile_name=req.profile_name,
        mix_intensity_cap=req.mix_intensity_cap,
        simulate_feeling=req.simulate_feeling,
    )


def _emotions_annotate(req: AnnotateEmotionsRequest) -> dict[str, Any]:
    return annotate_epistemic(
        req.question,
        gap_status=req.gap_status,
        surprise=req.surprise,
        neglectedness=req.neglectedness,
        answerability=req.answerability,
        notes=req.notes,
        domain=req.domain,
    )


def _emotions_elicit() -> dict[str, Any]:
    return elicit_helpers()


def _emotions_pack(name: str = "affective_science") -> dict[str, Any]:
    return emotion_pack(name)


@app.get("/v1/emotions/cues")
@app.get("/v1/epistemic/cues")
def emotions_cues() -> dict[str, Any]:
    """List epistemic cue tags (investigation framing — not felt emotion)."""
    return _emotions_cues()


@app.get("/v1/emotions/catalog")
@app.get("/v1/epistemic/catalog")
def emotions_catalog(
    family: str | None = Query(
        None,
        description="Optional filter: epistemic | basic | social | achievement",
    ),
) -> dict[str, Any]:
    """Named mixable emotion catalog (annotation only)."""
    return _emotions_catalog(family)


@app.post("/v1/emotions/mix")
@app.post("/v1/epistemic/mix")
def emotions_mix(req: MixEmotionsRequest) -> dict[str, Any]:
    """Mix catalog emotions by percent/weight; normalize to sum=1.0."""
    return _emotions_mix(req)


@app.post("/v1/emotions/annotate")
@app.post("/v1/epistemic/annotate")
def emotions_annotate(req: AnnotateEmotionsRequest) -> dict[str, Any]:
    """Annotate question text with epistemic cue tags."""
    return _emotions_annotate(req)


@app.get("/v1/emotions/annotate")
@app.get("/v1/epistemic/annotate")
def emotions_annotate_get(
    question: str = Query(..., min_length=12),
    gap_status: str = Query("unanswered"),
    surprise: float = Query(0.5, ge=0.0, le=1.0),
    neglectedness: float = Query(0.5, ge=0.0, le=1.0),
    answerability: float = Query(0.5, ge=0.0, le=1.0),
    notes: str = Query(""),
    domain: str = Query("ai"),
) -> dict[str, Any]:
    """GET annotate for curl / browsers."""
    return _emotions_annotate(
        AnnotateEmotionsRequest(
            question=question,
            gap_status=gap_status,
            surprise=surprise,
            neglectedness=neglectedness,
            answerability=answerability,
            notes=notes,
            domain=domain,
        )
    )


@app.get("/v1/emotions/elicit")
@app.get("/v1/epistemic/elicit")
def emotions_elicit() -> dict[str, Any]:
    """Incongruity → investigation framing + inject helpers."""
    return _emotions_elicit()


@app.get("/v1/emotions/pack")
@app.get("/v1/epistemic/pack")
def emotions_pack(
    name: str = Query("affective_science", description="Bundled pack id"),
) -> dict[str, Any]:
    """Affective-science (or named) domain pack — ranking seeds, not an emotion engine."""
    return _emotions_pack(name)
