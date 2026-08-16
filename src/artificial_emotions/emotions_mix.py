"""Catalog mix: percent/weight blend → PAD + optional felt simulation.

Callers import from ``artificial_emotions.emotions`` (stable). Catalog load
and ``emotion_catalog()`` live in ``emotions_catalog``. Logger namespace stays
``emotions`` so mix-cap skip telemetry does not churn.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from artificial_emotions.affect import (
    build_felt_simulation,
    detect_ambivalence,
    match_blend_triad,
    match_plutchik_dyad,
)
from artificial_emotions.emotions_catalog import (
    _AFFECT_HONESTY,
    _DEFAULT_MAX_MIX,
    _MIX_DISCLAIMER,
    _load_catalog_raw,
)
from artificial_emotions.errors import (
    ERR_EMPTY_MIX,
    ERR_MIX_TOO_LARGE,
    ERR_NEGATIVE_WEIGHT,
    ERR_UNKNOWN_EMOTION,
    ERR_VALIDATION,
    CuriosityError,
)
from artificial_emotions.logutil import get_logger, soft_fail

__all__ = [
    "feel",
    "mix_emotions",
]

logger = get_logger("emotions")


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
    third-person computational affect) — computational_only; does not feel.
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
        except ValueError as exc:
            soft_fail(
                logger,
                "mix intensity cap lookup failed for profile %r; cap unused",
                profile_name,
                exc=exc,
            )
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
        "research": "docs/EMOTIONS.md",
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
    """Alias for ``mix_emotions(..., simulate_feeling=True)`` — computational affect API."""
    return mix_emotions(weights, simulate_feeling=True, **kwargs)
