"""FastAPI app assembly.

Public entry point stays ``artificial_emotions.api:app`` — this package is the
implementation behind that module. Route handlers live in ``routers/``, request
models in ``schemas.py``, auth in ``security.py``.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from artificial_emotions import __version__
from artificial_emotions.api_pkg.audit import AuditMiddleware
from artificial_emotions.api_pkg.error_handlers import register_error_handlers
from artificial_emotions.api_pkg.rate_limit import RateLimitMiddleware
from artificial_emotions.api_pkg.routers import (
    alive,
    curiosity,
    emotions,
    evaluation,
    meta,
    preferences,
    profiles,
)
from artificial_emotions.api_pkg.security import OptionalApiKeyMiddleware
from artificial_emotions.config import cors_origins

__all__ = ["app", "create_app"]


def create_app() -> FastAPI:
    """Build the application. Kept as a function so tests can build a fresh one."""
    application = FastAPI(
        title="Artificial Emotions",
        description=(
            "Curiosity layer API: generate and rank valuable *unanswered* scientific "
            "questions. Designed so any human or AI model/provider can download this "
            "repo, start the server, and instantly ask: what should we investigate next?"
        ),
        version=__version__,
    )

    origins = cors_origins()
    # Order: CORS (inner) → auth → rate-limit → audit (outer).
    # Starlette: last-added = outermost, so 401/429 still reach the audit log.
    application.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=bool(origins) and ("*" not in origins),
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.add_middleware(OptionalApiKeyMiddleware)
    application.add_middleware(RateLimitMiddleware)
    application.add_middleware(AuditMiddleware)

    register_error_handlers(application)

    for module in (meta, profiles, curiosity, alive, preferences, evaluation, emotions):
        application.include_router(module.router)

    return application


app = create_app()
