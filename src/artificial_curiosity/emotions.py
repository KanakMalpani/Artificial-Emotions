"""Public emotion / epistemic-cue surface (UX annotations only).

These helpers expose *epistemic* tags for investigation framing
(incongruity, information-gap, confusion-risk, …), a named emotion
catalog, and percentage mixes. They are NOT a computational emotion
model and do NOT claim the system feels anything.

See docs/EMOTIONS.md, research/AI_EMOTIONS.md, research/EMOTION_MIXING.md.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

from artificial_curiosity.epistemic_cues import (
    EPISTEMIC_CUE_DISCLAIMER,
    TAG_BOREDOM_GUARD,
    TAG_CONFUSION_RISK,
    TAG_CURIOSITY_TARGET,
    TAG_INFORMATION_GAP,
    TAG_INCONGRUITY,
    TAG_SURPRISE_SIGNAL,
    derive_epistemic_cues,
    format_cues_for_inject,
    incongruity_investigate_block,
)
from artificial_curiosity.models import (
    GapEvidence,
    GapStatus,
    RankedQuestion,
    ScoreAxes,
    UnansweredQuestion,
)
from artificial_curiosity.packs import load_pack_file, questions_from_pack

# Re-export stable vocabulary for `from artificial_curiosity.emotions import …`
__all__ = [
    "EPISTEMIC_CUE_DISCLAIMER",
    "CUE_CATALOG",
    "list_epistemic_cues",
    "annotate_epistemic",
    "elicit_helpers",
    "emotion_pack",
    "emotion_catalog",
    "mix_emotions",
    "derive_epistemic_cues",
    "format_cues_for_inject",
    "incongruity_investigate_block",
    "TAG_INCONGRUITY",
    "TAG_INFORMATION_GAP",
    "TAG_CURIOSITY_TARGET",
    "TAG_CONFUSION_RISK",
    "TAG_SURPRISE_SIGNAL",
    "TAG_BOREDOM_GUARD",
]

_PACKS_DIR = Path(__file__).resolve().parent / "packs"
_CATALOG_FILE = "emotion_catalog.json"
_DEFAULT_MAX_MIX = 8
_MIX_DISCLAIMER = (
    "Emotion mixes are UX framing weights (normalized percentages) — "
    "NOT felt intensities, EES scores, or OCC appraisal state. "
    + EPISTEMIC_CUE_DISCLAIMER
)

CUE_CATALOG: list[dict[str, str]] = [
    {
        "tag": TAG_INFORMATION_GAP,
        "meaning": "Gap looks unanswered / partially answered — knowledge missing.",
    },
    {
        "tag": TAG_CURIOSITY_TARGET,
        "meaning": "Item is a candidate investigation target (functional curiosity cue).",
    },
    {
        "tag": TAG_CONFUSION_RISK,
        "meaning": "Partial/caveated gap or low answerability — risk of stuck confusion.",
    },
    {
        "tag": TAG_SURPRISE_SIGNAL,
        "meaning": "High surprise axis with an open gap — unexpectedness signal.",
    },
    {
        "tag": TAG_INCONGRUITY,
        "meaning": "Related literature ≠ answered, or surprise+gap — incongruity framing.",
    },
    {
        "tag": TAG_BOREDOM_GUARD,
        "meaning": "High neglectedness — prefer under-explored over over-covered topics.",
    },
]

_AFFECTIVE_PACK = "affective_science.json"


def list_epistemic_cues() -> dict[str, Any]:
    """List stable cue tags + honesty disclaimer (offline-safe)."""
    return {
        "cues": list(CUE_CATALOG),
        "tags": [c["tag"] for c in CUE_CATALOG],
        "honesty": "annotation_only",
        "disclaimer": EPISTEMIC_CUE_DISCLAIMER,
        "docs": "docs/EMOTIONS.md",
        "note": (
            "Epistemic cues annotate investigation framing. "
            "This software does not feel emotions."
        ),
    }


def _parse_gap_status(raw: str | GapStatus | None) -> GapStatus:
    if raw is None:
        return GapStatus.UNANSWERED
    if isinstance(raw, GapStatus):
        return raw
    key = str(raw).strip().lower()
    try:
        return GapStatus(key)
    except ValueError as exc:
        known = ", ".join(s.value for s in GapStatus)
        raise ValueError(f"Unknown gap_status '{raw}'. Known: {known}") from exc


def annotate_epistemic(
    question: str,
    *,
    gap_status: str | GapStatus = "unanswered",
    surprise: float = 0.5,
    neglectedness: float = 0.5,
    answerability: float = 0.5,
    notes: str = "",
    domain: str = "ai",
    operationalization: str = "Specify a falsifiable first experiment or analysis.",
    why_it_matters: str = "Annotate epistemic framing for an investigation candidate.",
) -> dict[str, Any]:
    """Annotate free-text (or scores) with epistemic cue tags.

    Offline-safe heuristics — same vocabulary as provoke inject packs.
    """
    q = (question or "").strip()
    if len(q) < 12:
        raise ValueError("question too short (need ≥12 characters)")

    def _clamp(x: float) -> float:
        return max(0.0, min(1.0, float(x)))

    item = RankedQuestion(
        question=UnansweredQuestion(
            id="annotate-ephemeral",
            question=q,
            domain=domain,
            operationalization=operationalization,
            why_it_matters=why_it_matters,
        ),
        scores=ScoreAxes(
            impact=0.5,
            neglectedness=_clamp(neglectedness),
            tractability=0.5,
            surprise=_clamp(surprise),
            answerability=_clamp(answerability),
            risk=0.2,
            cost_proxy=0.4,
        ),
        curiosity_score=0.5,
        confidence=0.4,
        gap=GapEvidence(
            status=_parse_gap_status(gap_status),
            confidence=0.5,
            notes=notes or "",
        ),
        rank=1,
    )
    cues = derive_epistemic_cues(item)
    return {
        "question": q,
        "gap_status": item.gap.status.value,
        "axes": {
            "surprise": item.scores.surprise,
            "neglectedness": item.scores.neglectedness,
            "answerability": item.scores.answerability,
        },
        "epistemic_cues": cues,
        "inject_fragment": format_cues_for_inject(cues),
        "honesty": "annotation_only",
        "disclaimer": EPISTEMIC_CUE_DISCLAIMER,
    }


def elicit_helpers() -> dict[str, Any]:
    """Elicit / inject helpers for incongruity → investigation framing."""
    framing = incongruity_investigate_block()
    return {
        "framing": framing,
        "inject_prefix": (
            "Epistemic framing (not anthropomorphism): treat ranked items as "
            "information gaps / incongruities. Name missing knowledge → first "
            "experiment → falsifier. This layer does not feel."
        ),
        "how_to_use": [
            "Call list_epistemic_cues (or GET /v1/emotions/cues) for the tag vocabulary.",
            "Call emotion_catalog (or GET /v1/emotions/catalog) for mixable named emotions.",
            "Mix percentages with mix_emotions (or POST /v1/emotions/mix), e.g. curiosity=40 confusion=30 awe=30.",
            "Annotate a draft question with annotate_epistemic (or POST /v1/emotions/annotate).",
            "Paste framing + inject_fragment into agent context alongside provoke inject packs.",
        ],
        "disclaimer": EPISTEMIC_CUE_DISCLAIMER,
        "honesty": "annotation_only",
        "docs": "docs/EMOTIONS.md",
    }


def emotion_pack(name: str = "affective_science") -> dict[str, Any]:
    """Load a bundled domain pack useful for affective / epistemic research.

    Default: ``affective_science`` — ranking seeds only, not an emotion engine.
    """
    key = (name or "affective_science").strip().lower().replace("-", "_")
    if key in ("affective_science", "affective_science_pack", "affect"):
        filename = _AFFECTIVE_PACK
        pack_key = "affective_science"
    else:
        raise ValueError(
            f"Unknown emotion pack '{name}'. Available: affective_science"
        )

    path = Path(__file__).resolve().parent / "packs" / filename
    data = load_pack_file(path)
    qs = questions_from_pack(data)
    return {
        "name": pack_key,
        "pack_name": data.get("name"),
        "version": data.get("version"),
        "domain": data.get("domain"),
        "description": data.get("description"),
        "count": len(qs),
        "questions": [
            {
                "id": q.id,
                "question": q.question,
                "operationalization": q.operationalization,
                "why_it_matters": q.why_it_matters,
                "tags": q.tags,
                "assumptions": q.assumptions,
            }
            for q in qs
        ],
        "honesty": "annotation_only",
        "disclaimer": (
            "Domain pack seeds for ranking / evals — not a CME or claim that "
            "the system feels emotions. " + EPISTEMIC_CUE_DISCLAIMER
        ),
        "docs": "docs/EMOTIONS.md",
        "research": "research/AI_EMOTIONS.md",
    }


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
    """Return the mixable named-emotion catalog (annotation only)."""
    raw = _load_catalog_raw()
    emotions = list(raw["emotions"])
    fam = (family or "").strip().lower() or None
    if fam:
        emotions = [e for e in emotions if str(e.get("family", "")).lower() == fam]
        if not emotions:
            known = sorted({str(e.get("family")) for e in raw["emotions"]})
            raise ValueError(
                f"Unknown family '{family}'. Known: {', '.join(known)}"
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
        "honesty": "annotation_only",
        "disclaimer": raw.get("disclaimer") or _MIX_DISCLAIMER,
        "docs": "docs/EMOTIONS.md",
        "research": "research/EMOTION_MIXING.md",
        "note": (
            "Use individually or mix with mix_emotions / POST /v1/emotions/mix. "
            "Percentages are framing weights — this software does not feel."
        ),
    }


def _parse_mix_mapping(
    weights: Mapping[str, float] | None,
    *,
    extra: Mapping[str, float] | None = None,
) -> dict[str, float]:
    merged: dict[str, float] = {}
    for src in (weights, extra):
        if not src:
            continue
        for key, val in src.items():
            kid = str(key).strip().lower().replace("-", "_").replace(" ", "_")
            if not kid:
                continue
            try:
                num = float(val)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"Invalid weight for '{key}': expected a number, got {val!r}"
                ) from exc
            merged[kid] = merged.get(kid, 0.0) + num
    return merged


def _looks_like_percent_scale(values: list[float]) -> bool:
    """Heuristic: values that look like 0–100 percents vs 0–1 weights."""
    if not values:
        return False
    mx = max(values)
    # Clear percents (e.g. 40+30+30). Small floats stay as weights.
    if mx > 1.5:
        return True
    # Sum near 100 with values in (1, 100] — treat as percents.
    total = sum(values)
    if total > 1.5 and mx <= 100.0:
        return True
    return False


def _match_plutchik_dyad(
    ids: list[str],
    dyads: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if len(ids) != 2:
        return None
    a, b = sorted(ids)
    for d in dyads:
        comps = sorted(str(x).lower() for x in (d.get("components") or []))
        if comps == [a, b]:
            return {
                "name": d.get("name"),
                "components": list(d.get("components") or []),
                "note": (
                    "Optional Plutchik primary-dyad hint from wheel adjacency — "
                    "taxonomic metaphor, not a measured compound emotion."
                ),
            }
    return None


def mix_emotions(
    weights: Mapping[str, float] | None = None,
    /,
    **kwargs: float,
) -> dict[str, Any]:
    """Mix catalog emotions by percent or weight; normalize to sum=1.0.

    Examples::

        mix_emotions({"curiosity": 40, "confusion": 30, "awe": 30})
        mix_emotions(curiosity=0.4, confusion=0.3, awe=0.3)

    Returns a blend profile + framing. Annotation only — does not feel.
    """
    raw_map = _parse_mix_mapping(weights, extra=kwargs)
    if not raw_map:
        raise ValueError(
            "Empty mix. Pass at least one emotion_id=weight, e.g. "
            "curiosity=40, confusion=30, awe=30"
        )

    catalog = _load_catalog_raw()
    by_id = {e["id"]: e for e in catalog["emotions"]}
    max_n = int(catalog.get("max_mix_components") or _DEFAULT_MAX_MIX)

    unknown = sorted(k for k in raw_map if k not in by_id)
    if unknown:
        sample = ", ".join(sorted(by_id)[:12])
        raise ValueError(
            f"Unknown emotion id(s): {', '.join(unknown)}. "
            f"See emotion_catalog() ids (e.g. {sample}, …)."
        )

    # Drop exact zeros; reject negatives.
    cleaned: dict[str, float] = {}
    for kid, val in raw_map.items():
        if val < 0:
            raise ValueError(f"Negative weight not allowed for '{kid}' ({val})")
        if val == 0:
            continue
        cleaned[kid] = val

    if not cleaned:
        raise ValueError("All mix weights are zero — nothing to blend.")

    if len(cleaned) > max_n:
        raise ValueError(
            f"Too many components ({len(cleaned)}). Max is {max_n}."
        )

    values = list(cleaned.values())
    as_percents = _looks_like_percent_scale(values)
    total = sum(values)
    if total <= 0:
        raise ValueError("Mix weights must sum to a positive total.")

    norm = {k: v / total for k, v in cleaned.items()}
    # Stable order: descending weight, then id.
    ordered = sorted(norm.items(), key=lambda kv: (-kv[1], kv[0]))

    pad = {"P": 0.0, "A": 0.0, "D": 0.0}
    families: dict[str, float] = {}
    cue_weights: dict[str, float] = {}
    components: list[dict[str, Any]] = []
    hints: list[str] = []

    for eid, w in ordered:
        entry = by_id[eid]
        p = entry.get("pad") or {}
        for axis in ("P", "A", "D"):
            pad[axis] += w * float(p.get(axis, 0.0))
        fam = str(entry.get("family") or "unknown")
        families[fam] = families.get(fam, 0.0) + w
        for tag in entry.get("cue_tags") or []:
            cue_weights[str(tag)] = cue_weights.get(str(tag), 0.0) + w
        for h in entry.get("elicit_hints") or []:
            if h not in hints:
                hints.append(str(h))
        components.append(
            {
                "id": eid,
                "label": entry.get("label") or eid,
                "family": fam,
                "weight": round(w, 6),
                "percent": round(100.0 * w, 4),
                "description": entry.get("description"),
            }
        )

    # Round PAD for stable JSON
    pad_out = {k: round(v, 4) for k, v in pad.items()}
    cue_tags = [
        t
        for t, _cw in sorted(cue_weights.items(), key=lambda kv: (-kv[1], kv[0]))
        if _cw >= 0.05
    ]
    primary = ordered[0][0]
    mix_str = ", ".join(f"{eid}={100.0 * w:.1f}%" for eid, w in ordered)
    framing = (
        f"Emotion mix framing (annotation only — does not feel): {mix_str}. "
        f"Primary={primary}. Prefer investigation moves from the weighted "
        f"components; do not narrate as the system's inner feelings."
    )
    inject = (
        f"emotion_mix=[{mix_str}] primary={primary}"
        + (f" cues=[{', '.join(cue_tags)}]" if cue_tags else "")
    )

    dyad = _match_plutchik_dyad(
        [c["id"] for c in components],
        list(catalog.get("plutchik_primary_dyads") or []),
    )

    return {
        "components": components,
        "weights": {k: round(v, 6) for k, v in ordered},
        "percents": {k: round(100.0 * v, 4) for k, v in ordered},
        "sum_weights": 1.0,
        "primary": primary,
        "pad": pad_out,
        "families": {k: round(v, 6) for k, v in sorted(families.items())},
        "cue_tags": cue_tags,
        "elicit_hints": hints[:8],
        "framing": framing,
        "inject_fragment": inject,
        "plutchik_dyad_hint": dyad,
        "input_scale": "percent" if as_percents else "weight",
        "catalog_version": catalog.get("version"),
        "honesty": "annotation_only",
        "disclaimer": _MIX_DISCLAIMER,
        "docs": "docs/EMOTIONS.md",
        "research": "research/EMOTION_MIXING.md",
        "claims_not": [
            "phenomenal feeling in the software",
            "measured human affect / EES scores",
            "OCC appraisal intensity",
            "clinically validated PAD mood",
        ],
    }
