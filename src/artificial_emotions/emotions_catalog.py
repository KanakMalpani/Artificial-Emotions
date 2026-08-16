"""Named-emotion catalog load and query.

Callers import from ``artificial_emotions.emotions`` (stable). This module
holds the JSON catalog contract: load, family filter, and ``emotion_catalog()``
payload shape. Mix math lives in ``emotions_mix``.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from artificial_emotions.errors import ERR_UNKNOWN_FAMILY, CuriosityError

__all__ = [
    "emotion_catalog",
]

_PACKS_DIR = Path(__file__).resolve().parent / "packs"
_CATALOG_FILE = "emotion_catalog.json"
_DEFAULT_MAX_MIX = 8
_AFFECT_HONESTY = "computational_affect"
_MIX_DISCLAIMER = (
    "Mix weights drive a computational PAD mood + intensity simulation "
    "intended to feel as close as possible to an affective state for "
    "investigation framing. This is NOT biological feeling, consciousness, "
    "EES clinical scores, or OCC live appraisal — it is a CME-style blend."
)


@lru_cache(maxsize=1)
def _load_catalog_raw() -> dict[str, Any]:
    path = _PACKS_DIR / _CATALOG_FILE
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict) or "emotions" not in data:
        raise RuntimeError(f"Invalid emotion catalog at {path}")
    return data


def emotion_catalog(
    *,
    family: str | None = None,
) -> dict[str, Any]:
    """Return the mixable named-emotion catalog (computational affect)."""
    raw = _load_catalog_raw()
    emotions = list(raw["emotions"])
    fam = (family or "").strip().lower() or None
    if fam:
        emotions = [e for e in emotions if str(e.get("family", "")).lower() == fam]
        if not emotions:
            known = sorted({str(e.get("family")) for e in raw["emotions"]})
            raise CuriosityError(
                ERR_UNKNOWN_FAMILY,
                f"Unknown family '{family}'. Known: {', '.join(known)}",
                details={"known": known},
            )
    families = sorted({str(e.get("family")) for e in raw["emotions"]})
    return {
        "name": raw.get("name", "emotion_catalog"),
        "version": raw.get("version"),
        "count": len(emotions),
        "families": families,
        "emotions": emotions,
        "max_mix_components": int(raw.get("max_mix_components") or _DEFAULT_MAX_MIX),
        "pad_axes": raw.get("pad_axes"),
        "ids": [e["id"] for e in emotions],
        "honesty": _AFFECT_HONESTY,
        "disclaimer": raw.get("disclaimer") or _MIX_DISCLAIMER,
        "docs": "docs/EMOTIONS.md",
        "research": "docs/EMOTIONS.md",
        "note": (
            "Use individually or mix with mix_emotions / feel() / POST /v1/emotions/mix. "
            "Mixes produce felt_simulation (PAD + intensity + inner monologue) — "
            "computational_affect; does not feel."
        ),
    }
