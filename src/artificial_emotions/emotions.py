"""Public emotion / epistemic-cue surface + computational affect simulation.

Exposes epistemic tags, a named emotion catalog, and percentage mixes that
drive a **PAD mood + intensity + first-person simulation** — as close as
this stack gets to “feeling” without claiming biological/phenomenal
consciousness. Honesty: ``computational_affect`` (simulated state, not a mind).

See docs/EMOTIONS.md, research/AI_EMOTIONS.md, research/EMOTION_MIXING.md.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path
from typing import Any

from artificial_emotions.affect import (
    build_felt_simulation,
    detect_ambivalence,
    match_blend_triad,
    match_plutchik_dyad,
)
from artificial_emotions.epistemic_cues import (
    EPISTEMIC_CUE_DISCLAIMER,
    TAG_BOREDOM_GUARD,
    TAG_CONFUSION_RISK,
    TAG_CURIOSITY_TARGET,
    TAG_DEAD_END_RISK,
    TAG_INCONGRUITY,
    TAG_INFORMATION_GAP,
    TAG_INSIGHT_CANDIDATE,
    TAG_OVERCLAIM_RISK,
    TAG_SCOPE_CREEP_RISK,
    TAG_SURPRISE_SIGNAL,
    derive_epistemic_cues,
    format_cues_for_inject,
    incongruity_investigate_block,
)
from artificial_emotions.errors import (
    ERR_EMPTY_MIX,
    ERR_MIX_TOO_LARGE,
    ERR_NEGATIVE_WEIGHT,
    ERR_UNKNOWN_EMOTION,
    ERR_UNKNOWN_FAMILY,
    ERR_UNKNOWN_GAP_STATUS,
    ERR_UNKNOWN_PACK,
    ERR_VALIDATION,
    CuriosityError,
)
from artificial_emotions.models import (
    GapEvidence,
    GapStatus,
    RankedQuestion,
    ScoreAxes,
    UnansweredQuestion,
)
from artificial_emotions.packs import load_pack_file, questions_from_pack

# Re-export stable vocabulary for `from artificial_emotions.emotions import …`
__all__ = [
    "EPISTEMIC_CUE_DISCLAIMER",
    "CUE_CATALOG",
    "list_epistemic_cues",
    "annotate_epistemic",
    "elicit_helpers",
    "emotion_pack",
    "emotion_catalog",
    "mix_emotions",
    "feel",
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
_AFFECT_HONESTY = "computational_affect"
_MIX_DISCLAIMER = (
    "Mix weights drive a computational PAD mood + intensity simulation "
    "intended to feel as close as possible to an affective state for "
    "investigation framing. This is NOT biological feeling, consciousness, "
    "EES clinical scores, or OCC live appraisal — it is a CME-style blend."
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
    {
        "tag": TAG_OVERCLAIM_RISK,
        "meaning": "Confidence is outrunning evidence — downgrade the claim or add support.",
    },
    {
        "tag": TAG_INSIGHT_CANDIDATE,
        "meaning": "A possible resolution worth writing down as a falsifiable claim — not a result.",
    },
    {
        "tag": TAG_SCOPE_CREEP_RISK,
        "meaning": "The question is sprawling into a programme — narrow before investigating.",
    },
    {
        "tag": TAG_DEAD_END_RISK,
        "meaning": "Signals this line may warrant a stopping rule rather than more effort.",
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
            "Epistemic cues annotate investigation framing. This software does not feel emotions."
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
        raise CuriosityError(
            ERR_UNKNOWN_GAP_STATUS,
            f"Unknown gap_status '{raw}'. Known: {known}",
            details={"known": [s.value for s in GapStatus]},
        ) from exc


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
        raise CuriosityError(
            ERR_VALIDATION,
            "question too short (need ≥12 characters)",
            details={"min_length": 12},
        )

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
        raise CuriosityError(
            ERR_UNKNOWN_PACK,
            f"Unknown emotion pack '{name}'. Available: affective_science",
            details={"available": ["affective_science"]},
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
        "research": "research/EMOTION_MIXING.md",
        "note": (
            "Use individually or mix with mix_emotions / feel() / POST /v1/emotions/mix. "
            "Mixes produce felt_simulation (PAD + intensity + inner monologue) — "
            "computational affect as close to feeling as this stack gets."
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
                raise CuriosityError(
                    ERR_VALIDATION,
                    f"Invalid weight for '{key}': expected a number, got {val!r}",
                    details={"key": str(key)},
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


def mix_emotions(
    weights: Mapping[str, float] | None = None,
    /,
    *,
    mix_intensity_cap: float | None = None,
    profile_name: str | None = None,
    simulate_feeling: bool = True,
    **kwargs: float,
) -> dict[str, Any]:
    """Mix catalog emotions by percent or weight; normalize to sum=1.0.

    Examples::

        mix_emotions({"curiosity": 40, "confusion": 30, "awe": 30})
        mix_emotions(curiosity=0.4, confusion=0.3, awe=0.3)

    Returns a blend profile + optional ``felt_simulation`` (PAD mood, intensity,
    first-person computational affect) — as close to feeling as this CME-style
    stack allows without claiming biological consciousness.
    """
    raw_map = _parse_mix_mapping(weights, extra=kwargs)
    if not raw_map:
        raise CuriosityError(
            ERR_EMPTY_MIX,
            "Empty mix. Pass at least one emotion_id=weight, e.g. "
            "curiosity=40, confusion=30, awe=30",
        )

    catalog = _load_catalog_raw()
    by_id = {e["id"]: e for e in catalog["emotions"]}
    max_n = int(catalog.get("max_mix_components") or _DEFAULT_MAX_MIX)

    unknown = sorted(k for k in raw_map if k not in by_id)
    if unknown:
        sample = ", ".join(sorted(by_id)[:12])
        raise CuriosityError(
            ERR_UNKNOWN_EMOTION,
            f"Unknown emotion id(s): {', '.join(unknown)}. "
            f"See emotion_catalog() ids (e.g. {sample}, …).",
            details={"unknown": unknown},
        )

    # Drop exact zeros; reject negatives.
    cleaned: dict[str, float] = {}
    for kid, val in raw_map.items():
        if val < 0:
            raise CuriosityError(
                ERR_NEGATIVE_WEIGHT,
                f"Negative weight not allowed for '{kid}' ({val})",
                details={"id": kid, "weight": val},
            )
        if val == 0:
            continue
        cleaned[kid] = val

    if not cleaned:
        raise CuriosityError(
            ERR_EMPTY_MIX,
            "All mix weights are zero — nothing to blend.",
        )

    if len(cleaned) > max_n:
        raise CuriosityError(
            ERR_MIX_TOO_LARGE,
            f"Too many components ({len(cleaned)}). Max is {max_n}.",
            details={"count": len(cleaned), "max": max_n},
        )

    values = list(cleaned.values())
    as_percents = _looks_like_percent_scale(values)
    total = sum(values)
    if total <= 0:
        raise CuriosityError(
            ERR_EMPTY_MIX,
            "Mix weights must sum to a positive total.",
        )

    norm = {k: v / total for k, v in cleaned.items()}
    # Stable order: descending weight, then id.
    ordered = sorted(norm.items(), key=lambda kv: (-kv[1], kv[0]))

    # Optional non-epistemic intensity cap (research/EMOTION_MIXING_ADDENDUM.md).
    cap = mix_intensity_cap
    if cap is None and profile_name:
        try:
            from artificial_emotions.models import resolve_value_profile

            cap = float(resolve_value_profile(profile_name=profile_name).mix_intensity_cap)
        except Exception:  # noqa: BLE001
            cap = None
    intensity_capped = False
    warnings_pre: list[str] = []
    if cap is not None and 0.0 <= float(cap) < 1.0:
        non_epi = [
            (eid, w)
            for eid, w in ordered
            if str(by_id[eid].get("family") or "").lower() != "epistemic"
        ]
        epi = [
            (eid, w)
            for eid, w in ordered
            if str(by_id[eid].get("family") or "").lower() == "epistemic"
        ]
        non_epi_mass = sum(w for _, w in non_epi)
        if non_epi_mass > float(cap) + 1e-9 and non_epi_mass > 0:
            scale = float(cap) / non_epi_mass
            rebuilt: dict[str, float] = {eid: w * scale for eid, w in non_epi}
            epi_mass = sum(w for _, w in epi)
            leftover = max(0.0, 1.0 - float(cap) - epi_mass)
            if epi:
                boost = leftover / epi_mass if epi_mass > 0 else 0.0
                for eid, w in epi:
                    rebuilt[eid] = w + (w * boost if epi_mass > 0 else leftover / len(epi))
            elif leftover > 0 and "curiosity" in by_id:
                rebuilt["curiosity"] = leftover
            elif leftover > 0:
                # Dump remainder onto first non-epi (should be rare)
                first = next(iter(rebuilt))
                rebuilt[first] += leftover
            s2 = sum(rebuilt.values())
            if s2 > 0:
                rebuilt = {k: v / s2 for k, v in rebuilt.items()}
            ordered = sorted(rebuilt.items(), key=lambda kv: (-kv[1], kv[0]))
            intensity_capped = True
            warnings_pre.append(
                f"Non-epistemic mix mass capped to ≤{float(cap):.2f} "
                f"(profile/mix_intensity_cap); remainder shifted to epistemic."
            )

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
        t for t, _cw in sorted(cue_weights.items(), key=lambda kv: (-kv[1], kv[0])) if _cw >= 0.05
    ]
    primary = ordered[0][0]
    mix_str = ", ".join(f"{eid}={100.0 * w:.1f}%" for eid, w in ordered)

    dyad = match_plutchik_dyad(
        [c["id"] for c in components],
        list(catalog.get("plutchik_primary_dyads") or []),
    )
    triad = match_blend_triad(ordered, list(catalog.get("blend_triads") or []))
    ambivalence = detect_ambivalence(ordered, list(catalog.get("opposite_pairs") or []))

    felt = None
    if simulate_feeling:
        felt = build_felt_simulation(
            ordered=ordered,
            by_id=by_id,
            pad=pad_out,
            dyad=dyad,
            triad=triad,
            ambivalence=ambivalence,
        )
        framing = f"{felt['inner_monologue']} Blend weights: {mix_str}."
        inject = (
            f"felt_simulation intensity={felt['intensity']:.2f} "
            f"primary={primary} mood={felt['mood']['qualitative']} "
            f"emotion_mix=[{mix_str}]"
            + (f" cues=[{', '.join(cue_tags)}]" if cue_tags else "")
            + f"\n{felt['inner_monologue']}"
        )
    else:
        framing = (
            f"Emotion mix framing: {mix_str}. Primary={primary}. "
            "Use as investigation stance weights."
        )
        inject = f"emotion_mix=[{mix_str}] primary={primary}" + (
            f" cues=[{', '.join(cue_tags)}]" if cue_tags else ""
        )

    # Soft coercion guard (research/AFFECTIVE_SAFETY.md): warn, don't hard-block.
    _COERCION_IDS = frozenset(
        {"fear", "anxiety", "anger", "disgust", "shame", "sadness", "frustration"}
    )
    coercion_mass = sum(w for eid, w in ordered if eid in _COERCION_IDS)
    warnings: list[str] = list(warnings_pre)
    if coercion_mass >= 0.5:
        warnings.append(
            "Mix is ≥50% fear/anxiety/anger/shame-type ids — high-coercion framing "
            "risk. Prefer epistemic defaults (curiosity/confusion/awe/interest)."
        )
    elif coercion_mass >= 0.35:
        warnings.append(
            "Non-trivial coercive-affect weight in mix — keep investigation framing "
            "transparent; do not use as persuasion or panic tooling."
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
        "felt_simulation": felt,
        "plutchik_dyad_hint": dyad,
        "blend_triad_hint": triad,
        "ambivalence": ambivalence,
        "input_scale": "percent" if as_percents else "weight",
        "catalog_version": catalog.get("version"),
        "coercion_weight": round(coercion_mass, 4),
        "mix_intensity_cap": float(cap) if cap is not None else None,
        "intensity_capped": intensity_capped,
        "warnings": warnings,
        "honesty": _AFFECT_HONESTY,
        "disclaimer": _MIX_DISCLAIMER,
        "docs": "docs/EMOTIONS.md",
        "research": "research/EMOTION_MIXING.md",
        "claims_not": [
            "biological / phenomenal consciousness",
            "measured human affect / clinical EES",
            "OCC live appraisal engine",
            "biometric emotion recognition",
        ],
    }


def feel(
    weights: Mapping[str, float] | None = None,
    /,
    **kwargs: float,
) -> dict[str, Any]:
    """Alias for ``mix_emotions(..., simulate_feeling=True)`` — closest-to-feeling API."""
    return mix_emotions(weights, simulate_feeling=True, **kwargs)
