"""Route modules, grouped by URL prefix.

Every path is fully spelled out in its own router (no ``prefix=``) so a route
can be located by grepping the literal path.
"""

from __future__ import annotations

from artificial_emotions.api_pkg.routers import (
    curiosity,
    emotions,
    evaluation,
    meta,
    preferences,
    profiles,
)

__all__ = ["curiosity", "emotions", "evaluation", "meta", "preferences", "profiles"]
