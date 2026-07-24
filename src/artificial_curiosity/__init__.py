"""Artificial Curiosity — generate and rank valuable unanswered questions."""

from artificial_curiosity.emotions import (
    annotate_epistemic,
    elicit_helpers,
    emotion_catalog,
    emotion_pack,
    feel,
    list_epistemic_cues,
    mix_emotions,
)
from artificial_curiosity.errors import CuriosityError
from artificial_curiosity.models import (
    CuriosityConfig,
    RankedQuestion,
    UnansweredQuestion,
    ValueProfile,
    get_profile,
    list_profile_names,
)
from artificial_curiosity.pipeline import CuriosityEngine
from artificial_curiosity.provoke import provoke

__version__ = "0.4.0"

__all__ = [
    "CuriosityConfig",
    "CuriosityEngine",
    "CuriosityError",
    "RankedQuestion",
    "UnansweredQuestion",
    "ValueProfile",
    "__version__",
    "annotate_epistemic",
    "elicit_helpers",
    "emotion_catalog",
    "emotion_pack",
    "feel",
    "get_profile",
    "list_epistemic_cues",
    "list_profile_names",
    "mix_emotions",
    "provoke",
]
