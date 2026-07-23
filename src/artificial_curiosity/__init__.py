"""Artificial Curiosity — generate and rank valuable unanswered questions."""

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

__all__ = [
    "CuriosityConfig",
    "CuriosityEngine",
    "RankedQuestion",
    "UnansweredQuestion",
    "ValueProfile",
    "get_profile",
    "list_profile_names",
    "provoke",
]

__version__ = "0.2.0"
