"""Service metadata: liveness, readiness, index, and the agent manifest.

``/health`` and ``/ready`` are in the auth open list, so nothing here may leak
secrets — see ``redact_base_url``.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from artificial_emotions import __version__
from artificial_emotions.agent_tools import mcp_tool_tiers, openai_tools
from artificial_emotions.api_pkg.security import redact_base_url
from artificial_emotions.config import clear_config_cache, get_config
from artificial_emotions.emotions import emotion_catalog
from artificial_emotions.llm import resolve_llm_settings
from artificial_emotions.logutil import get_logger
from artificial_emotions.models import Domain, list_profile_names

logger = get_logger("api")

router = APIRouter()


@router.get("/health")
def health() -> dict[str, Any]:
    """Liveness + config summary (safe; no secrets)."""
    clear_config_cache()
    cfg = get_config()
    llm = resolve_llm_settings()
    judge = resolve_llm_settings(judge=True)
    return {
        "ok": True,
        "service": "artificial-emotions",
        "version": cfg.version,
        "status": "alive",
        "llm_configured": llm is not None,
        "llm_model": llm.model if llm else None,
        "judge_model": judge.model if judge else None,
        "llm_base_url": redact_base_url(llm.base_url if llm else None),
        "llm_timeout_s": cfg.llm_timeout_s,
        "literature_timeout_s": cfg.literature_timeout_s,
        "s2_key_configured": cfg.s2_configured,
        "profiles": list_profile_names(),
        "api_auth_required": cfg.api_auth_required,
        "cors_origins": list(cfg.cors_origins),
    }


@router.get("/ready")
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
        "service": "artificial-emotions",
        "version": cfg.version,
        "checks": checks,
        "note": ("Ready means offline spark/emotions work. Literature/LLM remain optional."),
    }
    return JSONResponse(status_code=200 if ok else 503, content=body)


@router.get("/")
def root() -> dict[str, Any]:
    return {
        "service": "Artificial Emotions",
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
        "mcp": "curiosity-mcp (stdio) or python -m artificial_emotions.mcp_server",
        "config": "artificial_emotions.config / .env.example",
        "safety": (
            "Not biometric emotion recognition. Emotion mix/cues are UX annotations. "
            "Provoke is opt-in investigation framing. Scores need explicit ValueProfile — "
            "decision aids, not oracles. See docs/LIMITS.md."
        ),
    }


@router.get("/v1/agent")
def agent_manifest() -> dict[str, Any]:
    """Machine-readable guide for any AI agent or model provider."""
    return {
        "name": "artificial-emotions",
        "version": __version__,
        "purpose": (
            "Ranks valuable unanswered questions under an explicit ValueProfile; "
            "verifies literature neighborhoods without equating related work with "
            "answered questions; returns briefs and optional provoke inject packs."
        ),
        "card": (
            "Artificial Emotions ranks valuable unanswered questions under an "
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
                "python -m artificial_emotions.mcp_server",
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
            "docs": "artificial_emotions.errors",
        },
    }


@router.get("/v1/agent/tools")
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


@router.get("/v1/domains")
def domains() -> dict[str, Any]:
    return {"domains": [d.value for d in Domain]}
