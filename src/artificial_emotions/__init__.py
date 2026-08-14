"""Artificial Emotions — generate and rank valuable unanswered questions."""

from artificial_emotions.emotions import (
    annotate_epistemic,
    elicit_helpers,
    emotion_catalog,
    emotion_pack,
    feel,
    list_epistemic_cues,
    mix_emotions,
)
from artificial_emotions.errors import CuriosityError
from artificial_emotions.models import (
    CuriosityConfig,
    RankedQuestion,
    UnansweredQuestion,
    ValueProfile,
    get_profile,
    list_profile_names,
)
from artificial_emotions.pipeline import CuriosityEngine
from artificial_emotions.provoke import provoke

__version__ = "1.0.0"

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
