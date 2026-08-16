"""Modulation: where affect stops being a label and starts causing things.

An affective state that changes nothing is decoration. This module lets the
state derived by ``appraisal`` change what the engine does next — widen the
search when curious, narrow and decompose when confused, jump ground when
bored, demand literature when the system catches itself being overconfident.

Catalog ``effects`` are the contract. ``apply_effects`` enacts the frozen
vocabulary; per-emotion if-ladders must not grow. Characterization of the
existing modulators (n_candidates, literature, jump) is preserved.

**The honesty constraint.** This project's central claim is that ranking is a
function of an explicit ValueProfile with no hidden weights. So by default
affect moves *search behaviour* — breadth, whether to fetch literature, whether
to decompose, whether to change ground — and never touches the scoring weights.
The score stays a pure function of the profile you stated.

Weight modulation exists, but it is opt-in (``allow_weight_deltas=True``),
bounded by ``MAX_WEIGHT_DELTA``, and every delta is reported in the plan. That
mirrors how ``preferences.learn_profile_weight_hints`` already works: small,
visible, and never silent.

Deterministic and offline.

Catalog ``apply_effects`` lives in ``modulate_effects``; this module keeps the
public import path and plan assembly (``modulate_config``).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from artificial_emotions.models import CuriosityConfig
from artificial_emotions.modulate_effects import (
    _STRENGTH_FLOOR,
    ALWAYS_ON_HIGH_COERCION_EFFECTS,
    HIGH_COERCION_IDS,
    MAX_WEIGHT_DELTA,
    ModulationChange,
    ModulationPlan,
    _catalog_effect_index,
    _current_profile,
    _effect_permitted,
    _EffectState,
    _record,
    _strength,
    apply_effects,
    high_coercion_effect_allowed,
    somatic_modulate_requested,
)

__all__ = [
    "ALWAYS_ON_HIGH_COERCION_EFFECTS",
    "AMBIVALENCE_ENACT_THRESHOLD",
    "HIGH_COERCION_IDS",
    "MAX_WEIGHT_DELTA",
    "ModulationChange",
    "ModulationPlan",
    "apply_effects",
    "high_coercion_effect_allowed",
    "modulate_config",
    "somatic_modulate_requested",
]

#: ``detect_ambivalence`` score at which exclusive expansions must not both apply.
AMBIVALENCE_ENACT_THRESHOLD = 0.35

#: Honesty tokens on an enacted payload — a pattern in the mix, not a motive.
_AMBIVALENCE_CLAIMS = ("ambivalence_enacted", "pattern_not_motive")

#: Knobs that disagree when both sides of a named opposite pair fire.
#: Applying both in one step treats disagreement as agreement.
_EXCLUSIVE_KNOBS: dict[str, frozenset[str]] = {
    "curiosity": frozenset({"n_candidates", "value_profile.weight_surprise"}),
    "boredom": frozenset({"diversity_threshold", "domain", "value_profile.weight_neglectedness"}),
}


def _resolve_somatic_modulate(
    config: CuriosityConfig,
    mix_weights: Mapping[str, float],
    somatic_modulate: bool | None,
) -> bool:
    """Explicit flag wins; otherwise config, else caller mix containing high-coercion ids."""
    if somatic_modulate is not None:
        return bool(somatic_modulate)
    if bool(getattr(config, "somatic_modulate", False)):
        return True
    return somatic_modulate_requested(mix_weights=mix_weights)


def _ambivalence_skips(
    mix_weights: dict[str, float],
    ambivalence: dict[str, Any] | None,
) -> tuple[frozenset[str], dict[str, Any] | None]:
    """Knobs to withhold when a named opposite pair is above the enact threshold.

    Returns ``(skip, record)``. ``record`` is None when exclusive expansions may
    both apply (no named pair, score too low, or the pair has no exclusive knobs).
    """
    if not ambivalence:
        return frozenset(), None
    score = float(ambivalence.get("score") or 0.0)
    if score < AMBIVALENCE_ENACT_THRESHOLD:
        return frozenset(), None
    pairs = list(ambivalence.get("pairs") or [])
    if not pairs:
        return frozenset(), None
    comps = [str(c).lower() for c in (pairs[0].get("components") or [])]
    if len(comps) != 2:
        return frozenset(), None
    left, right = comps
    exclusive_left = _EXCLUSIVE_KNOBS.get(left, frozenset())
    exclusive_right = _EXCLUSIVE_KNOBS.get(right, frozenset())
    if not exclusive_left and not exclusive_right:
        return frozenset(), None
    wa = float(mix_weights.get(left, 0.0))
    wb = float(mix_weights.get(right, 0.0))
    if wa <= 0.0 or wb <= 0.0:
        return frozenset(), None

    if wa > wb:
        louder = left
    elif wb > wa:
        louder = right
    else:
        louder = left

    skip: set[str] = set(_EXCLUSIVE_KNOBS.get(louder, ()))
    # Freeze search width whenever either side would move it — never widen and
    # shrink as if the pair agreed.
    if "n_candidates" in exclusive_left or "n_candidates" in exclusive_right:
        skip.add("n_candidates")
    if wa == wb:
        skip.update(_EXCLUSIVE_KNOBS.get(right if louder == left else left, ()))

    parts = [
        f"Named opposite pair {left} vs {right} at tension {score:.2f}.",
        (
            "Exclusive expansions disagree — skipped louder-side "
            f"({louder}) exclusive move(s) rather than applying both."
        ),
    ]
    if "n_candidates" in skip:
        parts.append("n_candidates frozen this step.")
    parts.append(
        "Discriminating observation: whether this step's returns are still "
        "novel open gaps or repeats of already-mined ground."
    )
    because = " ".join(parts)
    record = {
        "pair": [left, right],
        "score": score,
        "louder": louder,
        "skipped": sorted(skip),
        "because": because,
        "claims": list(_AMBIVALENCE_CLAIMS),
    }
    return frozenset(skip), record


def _stay_aggregate(
    mix_weights: Mapping[str, float],
    opt_in: bool,
    index: Mapping[str, tuple[tuple[str, ...], str]],
) -> tuple[str, float]:
    """Sum permitted ``stay_course`` strengths; pick a driver for the audit trail."""
    parts: list[tuple[str, float]] = []
    for eid, raw in mix_weights.items():
        strength = float(raw)
        if strength <= 0.0:
            continue
        effects, coercion = index.get(str(eid), ((), ""))
        if "stay_course" not in effects:
            continue
        if not _effect_permitted(
            "stay_course",
            opt_in=opt_in,
            emotion_id=str(eid),
            coercion=coercion,
            effects=effects,
        ):
            continue
        parts.append((str(eid), strength))
    total = sum(w for _, w in parts)
    if total < _STRENGTH_FLOOR:
        return "", 0.0
    by_id = dict(parts)
    if by_id.get("absorption", 0.0) >= _STRENGTH_FLOOR:
        driver = "absorption"
    elif by_id.get("hope", 0.0) >= _STRENGTH_FLOOR:
        driver = "hope"
    else:
        driver = max(parts, key=lambda item: (item[1], item[0]))[0]
    return driver, total


def modulate_config(
    config: CuriosityConfig,
    mix_weights: dict[str, float],
    *,
    allow_weight_deltas: bool = False,
    exhausted: bool = False,
    ambivalence: dict[str, Any] | None = None,
    somatic_modulate: bool | None = None,
) -> tuple[CuriosityConfig, ModulationPlan]:
    """Return a new config shaped by the current affect, plus the audit trail.

    Args:
        config: the run configuration to adjust.
        mix_weights: normalized emotion weights from the appraised mix.
        allow_weight_deltas: permit bounded ValueProfile nudges (default off).
        exhausted: the trajectory has stopped surfacing anything new.
        ambivalence: ``detect_ambivalence`` payload from the mix. When its
            score is ≥ ``AMBIVALENCE_ENACT_THRESHOLD`` on a named pair with
            exclusive knobs, those knobs are not applied as if they agreed.
        somatic_modulate: high-coercion search knobs. ``None`` infers from
            ``config.somatic_modulate`` or a caller mix that names those ids.
            ``False`` forces off (appraisal-driven explore). ``True`` opts in.
            Reads ``config.somatic_modulate``; does not redefine it. Safety
            effects may still apply either way.

    Returns:
        ``(new_config, plan)``. The input config is never mutated.
    """
    plan = ModulationPlan()
    plan.somatic_modulate = _resolve_somatic_modulate(config, mix_weights, somatic_modulate)
    updates: dict[str, Any] = {}
    skip, enacted = _ambivalence_skips(mix_weights, ambivalence)
    if enacted is not None:
        plan.ambivalence_enacted = True
        plan.skipped_exclusive = list(enacted["skipped"])
        plan.because = str(enacted["because"])
        plan.claims = list(enacted["claims"])
        plan.changes.append(
            ModulationChange(
                "ambivalence_exclusive",
                "apply_both",
                "skip_louder",
                "ambivalence",
                float(enacted["score"]),
                plan.because,
                bounded_by="ambivalence_enacted",
            )
        )

    opt_in = plan.somatic_modulate
    index = _catalog_effect_index()
    state = _EffectState(
        config=config,
        updates=updates,
        skip=skip,
        exhausted=exhausted,
        mix_weights=mix_weights,
    )

    stay_driver, stay_strength = _stay_aggregate(mix_weights, opt_in, index)
    if stay_strength >= _STRENGTH_FLOOR:
        apply_effects(
            plan,
            ("stay_course",),
            stay_strength,
            opt_in,
            emotion_id=stay_driver,
            coercion="",
            state=state,
        )

    for eid, raw in mix_weights.items():
        strength = float(raw)
        if strength < _STRENGTH_FLOOR:
            continue
        effects, coercion = index.get(str(eid), ((), ""))
        remaining = tuple(e for e in effects if e != "stay_course")
        if not remaining:
            continue
        apply_effects(
            plan,
            remaining,
            strength,
            opt_in,
            emotion_id=str(eid),
            coercion=coercion,
            state=state,
        )

    # Leave-the-line: frustration / resignation / exhaustion stop unless a live
    # thread is protected. Not a frozen effect id — characterization of jump_ground.
    frustration = _strength(mix_weights, "frustration")
    resignation = _strength(mix_weights, "resignation")
    persistence = _strength(mix_weights, "persistence")
    if (frustration >= 0.35 or resignation >= 0.3 or exhausted) and not (
        plan.stay_the_course or persistence >= _STRENGTH_FLOOR
    ):
        plan.stop = True
        driver = (
            "frustration"
            if frustration >= 0.35
            else "resignation"
            if resignation >= 0.3
            else "exhaustion"
        )
        plan.stop_reason = (
            f"Stopping on {driver}: repeated effort stopped ruling things out. "
            "Recording the dead end is more useful than another pass."
        )
        _record(
            plan,
            knob="stop",
            before=False,
            after=True,
            driver=driver,
            strength=max(frustration, resignation),
            rationale=plan.stop_reason,
        )

    if allow_weight_deltas:
        curiosity = _strength(mix_weights, "curiosity")
        confusion = _strength(mix_weights, "confusion") + _strength(mix_weights, "perplexity")
        boredom = _strength(mix_weights, "boredom")
        deltas: dict[str, float] = {}
        if curiosity >= _STRENGTH_FLOOR and "value_profile.weight_surprise" not in skip:
            deltas["weight_surprise"] = min(MAX_WEIGHT_DELTA, 0.1 * curiosity)
        if confusion >= _STRENGTH_FLOOR:
            deltas["weight_tractability"] = min(MAX_WEIGHT_DELTA, 0.1 * confusion)
        if boredom >= _STRENGTH_FLOOR and "value_profile.weight_neglectedness" not in skip:
            deltas["weight_neglectedness"] = min(MAX_WEIGHT_DELTA, 0.1 * boredom)
        if deltas:
            profile = _current_profile(state)
            fields: dict[str, Any] = {}
            loudest = max(mix_weights, key=mix_weights.get) if mix_weights else "affect"
            for knob, delta in deltas.items():
                before = float(getattr(profile, knob))
                after = round(min(2.0, before + delta), 4)
                fields[knob] = after
                _record(
                    plan,
                    knob=f"value_profile.{knob}",
                    before=before,
                    after=after,
                    driver=str(loudest),
                    strength=delta,
                    rationale="Opt-in affect nudge on a scoring weight.",
                    bounded_by=f"|delta| <= {MAX_WEIGHT_DELTA}",
                )
            state.updates["value_profile"] = profile.model_copy(update=fields)
            plan.weights_touched = True

    new_config = config.model_copy(update=updates) if updates else config.model_copy()
    return new_config, plan
