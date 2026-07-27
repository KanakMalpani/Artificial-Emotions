"""FastAPI surface for the curiosity layer — usable by humans and any AI agent.

``artificial_emotions.api:app`` is the stable entry point (uvicorn target,
``curiosity serve``, TestClient). The implementation lives in
``artificial_emotions.api_pkg``:

    api_pkg/__init__.py      app assembly — middleware, handlers, router wiring
    api_pkg/security.py      opt-in API-key middleware
    api_pkg/error_handlers.py exception → stable JSON envelope
    api_pkg/schemas.py       pydantic request models
    api_pkg/routers/         handlers grouped by URL prefix

Names re-exported here are part of the public surface; keep them importable
from this module.
"""

from __future__ import annotations

from artificial_emotions.api_pkg import app, create_app
from artificial_emotions.api_pkg.routers.meta import ready
from artificial_emotions.api_pkg.schemas import (
    AnnotateEmotionsRequest,
    CompareProfilesRequest,
    ConstitutionCompareRequest,
    CritiqueBriefRequest,
    CrossModelVoteRequest,
    DecomposeRequest,
    ExploreRequest,
    IdeaGraphRequest,
    MixEmotionsRequest,
    PreferenceHintsRequest,
    PreferenceSummarizeRequest,
    ProvokeRequest,
    RunRequest,
    SoundnessPassRequest,
    SuggestPairRequest,
    SurpriseWorksheetRequest,
    VoiWorksheetRequest,
)
from artificial_emotions.api_pkg.security import OptionalApiKeyMiddleware

__all__ = [
    "AnnotateEmotionsRequest",
    "CompareProfilesRequest",
    "ConstitutionCompareRequest",
    "CritiqueBriefRequest",
    "DecomposeRequest",
    "ExploreRequest",
    "CrossModelVoteRequest",
    "IdeaGraphRequest",
    "MixEmotionsRequest",
    "OptionalApiKeyMiddleware",
    "PreferenceHintsRequest",
    "PreferenceSummarizeRequest",
    "ProvokeRequest",
    "RunRequest",
    "SoundnessPassRequest",
    "SuggestPairRequest",
    "SurpriseWorksheetRequest",
    "VoiWorksheetRequest",
    "app",
    "create_app",
    "ready",
]
