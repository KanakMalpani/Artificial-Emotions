"""Modulation: where affect stops being a label and starts causing things.

An affective state that changes nothing is decoration. This module lets the
state derived by ``appraisal`` change what the engine does next — widen the
search when curious, narrow and decompose when confused, jump ground when
bored, demand literature when the system catches itself being overconfident.

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
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from artificial_emotions.models import CuriosityConfig

__all__ = [
    "ALWAYS_ON_HIGH_COERCION_EFFECTS",
    "AMBIVALENCE_ENACT_THRESHOLD",
    "HIGH_COERCION_IDS",
    "MAX_WEIGHT_DELTA",
    "ModulationChange",
    "ModulationPlan",
    "high_coercion_effect_allowed",
    "modulate_config",
    "somatic_modulate_requested",
]

#: Same ceiling the preference-hint path uses. Affect nudges; it never steers.
MAX_WEIGHT_DELTA = 0.08

_STRENGTH_FLOOR = 0.15  # below this an emotion is present but not driving

#: ``detect_ambivalence`` score at which exclusive expansions must not both apply.
AMBIVALENCE_ENACT_THRESHOLD = 0.35

#: Honesty tokens on an enacted payload — a pattern in the mix, not a motive.
_AMBIVALENCE_CLAIMS = ("ambivalence_enacted", "pattern_not_motive")

#: Somatic cluster — catalog ``coercion: ""`` is unset, not ``low``. These ids
#: are high-coercion even while Wave 0 placeholders remain empty.
HIGH_COERCION_IDS: frozenset[str] = frozenset({"fear", "anger", "disgust", "joy", "sadness"})

#: Frozen-vocabulary effects that may run without ``--somatic-modulate``.
ALWAYS_ON_HIGH_COERCION_EFFECTS: frozenset[str] = frozenset({"tighten_safety", "drop_dual_use"})

#: Knobs that disagree when both sides of a named opposite pair fire.
#: Applying both in one step treats disagreement as agreement.
_EXCLUSIVE_KNOBS: dict[str, frozenset[str]] = {
    "curiosity": frozenset({"n_candidates", "value_profile.weight_surprise"}),
    "boredom": frozenset({"diversity_threshold", "domain", "value_profile.weight_neglectedness"}),
}


def somatic_modulate_requested(
    *,
    somatic_modulate: bool = False,
    mix_weights: Mapping[str, float] | None = None,
    from_appraisal: bool = False,
) -> bool:
    """Whether the user asked for high-coercion search knobs.

    Asking is ``somatic_modulate=True`` (CLI / ``CuriosityConfig``). A
    caller-authored mix that already names high-coercion ids also counts,
    unless ``from_appraisal`` — appraisal dumps are not a request.
    """
    if somatic_modulate:
        return True
    if from_appraisal:
        return False
    if not mix_weights:
        return False
    return any(str(eid) in HIGH_COERCION_IDS and float(w) > 0.0 for eid, w in mix_weights.items())


def high_coercion_effect_allowed(
    effect_id: str,
    *,
    somatic_modulate: bool,
    emotion_id: str | None = None,
    coercion: str = "",
) -> bool:
    """High-coercion search effects need opt-in; safety effects may always run.

    ``coercion: ""`` is unset, not ``low``. Known high-coercion ids still gate
    while catalog rows are empty placeholders. Wave 2 ``apply_effects`` reads
    this; it does not invent effect ids.
    """
    eid = str(effect_id)
    if eid in ALWAYS_ON_HIGH_COERCION_EFFECTS or eid == "surface_only":
        return True
    is_high = coercion == "high" or (
        emotion_id is not None and str(emotion_id) in HIGH_COERCION_IDS
    )
    if not is_high:
        return True
    return bool(somatic_modulate)


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


@dataclass(frozen=True)
class ModulationChange:
    """One adjustment, the feeling that caused it, and the bound that held it."""

    knob: str
    before: Any
    after: Any
    driver: str
    strength: float
    rationale: str
    bounded_by: str | None = None

    def to_dict(self) -> dict[str, Any]:
        out = {
            "knob": self.knob,
            "before": self.before,
            "after": self.after,
            "driver": self.driver,
            "strength": round(float(self.strength), 4),
            "rationale": self.rationale,
        }
        if self.bounded_by:
            out["bounded_by"] = self.bounded_by
        return out


@dataclass
class ModulationPlan:
    """What affect changed, and what it deliberately did not."""

    changes: list[ModulationChange] = field(default_factory=list)
    weights_touched: bool = False
    force_decompose: bool = False
    suggest_domain_jump: bool = False
    stay_the_course: bool = False
    require_review: bool = False
    force_soundness: bool = False
    stop: bool = False
    stop_reason: str = ""
    somatic_modulate: bool = False
    ambivalence_enacted: bool = False
    skipped_exclusive: list[str] = field(default_factory=list)
    because: str = ""
    claims: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        honesty = (
            "Affect modulates search behaviour. ValueProfile weights are "
            "untouched unless allow_weight_deltas was set, and any delta is "
            f"capped at ±{MAX_WEIGHT_DELTA} and listed above."
        )
        if self.ambivalence_enacted:
            honesty += (
                " Ambivalence is enacted as a pattern, not a motive "
                "(ambivalence_enacted, pattern_not_motive)."
            )
        out: dict[str, Any] = {
            "changes": [c.to_dict() for c in self.changes],
            "n_changes": len(self.changes),
            "weights_touched": self.weights_touched,
            "force_decompose": self.force_decompose,
            "suggest_domain_jump": self.suggest_domain_jump,
            "stay_the_course": self.stay_the_course,
            "require_review": self.require_review,
            "force_soundness": self.force_soundness,
            "stop": self.stop,
            "stop_reason": self.stop_reason,
            "somatic_modulate": self.somatic_modulate,
            "honesty": honesty,
        }
        if self.ambivalence_enacted:
            out["ambivalence_enacted"] = True
            out["pattern_not_motive"] = True
            out["claims"] = list(self.claims)
            out["because"] = self.because
            out["skipped_exclusive"] = list(self.skipped_exclusive)
        return out


def _strength(weights: dict[str, float], emotion: str) -> float:
    return float(weights.get(emotion, 0.0))


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
            Wave 2 reads this; safety effects may still apply either way.

    Returns:
        ``(new_config, plan)``. The input config is never mutated.
    """
    plan = ModulationPlan()
    plan.somatic_modulate = _resolve_somatic_modulate(config, mix_weights, somatic_modulate)
    updates: dict[str, Any] = {}
    profile = config.value_profile
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

    curiosity = _strength(mix_weights, "curiosity")
    confusion = _strength(mix_weights, "confusion") + _strength(mix_weights, "perplexity")
    boredom = _strength(mix_weights, "boredom")
    hubris = _strength(mix_weights, "hubris")
    frustration = _strength(mix_weights, "frustration")
    resignation = _strength(mix_weights, "resignation")
    determination = _strength(mix_weights, "determination")

    # Momentum is resolved up front because the stop rule below has to be able to
    # consult it — a live thread should survive one bad step.
    absorption = _strength(mix_weights, "absorption")
    persistence = _strength(mix_weights, "persistence")
    stay = absorption + _strength(mix_weights, "hope") + _strength(mix_weights, "anticipation")
    if stay >= _STRENGTH_FLOOR:
        plan.stay_the_course = True
        plan.changes.append(
            ModulationChange(
                "stay_the_course",
                False,
                True,
                "absorption" if absorption >= _STRENGTH_FLOOR else "hope",
                stay,
                "A live, reachable thread is running — do not change ground yet.",
            )
        )

    # --- curiosity widens the net ---------------------------------------------
    if curiosity >= _STRENGTH_FLOOR and "n_candidates" not in skip:
        before = config.n_candidates
        after = min(64, int(round(before * (1.0 + 0.5 * curiosity))))
        if after != before:
            updates["n_candidates"] = after
            plan.changes.append(
                ModulationChange(
                    "n_candidates",
                    before,
                    after,
                    "curiosity",
                    curiosity,
                    "Open, neglected gaps are worth casting wider for.",
                    bounded_by="n_candidates <= 64",
                )
            )

    # --- confusion narrows and forces the ladder ------------------------------
    if confusion >= _STRENGTH_FLOOR:
        before = config.n_return
        after = max(3, int(round(before * (1.0 - 0.4 * min(confusion, 0.8)))))
        if after != before:
            updates["n_return"] = after
            plan.changes.append(
                ModulationChange(
                    "n_return",
                    before,
                    after,
                    "confusion",
                    confusion,
                    "Disagreement or loose posing — return fewer, look harder.",
                    bounded_by="n_return >= 3",
                )
            )
        plan.force_decompose = True
        plan.changes.append(
            ModulationChange(
                "force_decompose",
                False,
                True,
                "confusion",
                confusion,
                "A confusing result is exactly what decomposition is for.",
            )
        )

    # --- boredom pushes off the mined vein ------------------------------------
    if boredom >= _STRENGTH_FLOOR:
        if "diversity_threshold" not in skip:
            before = config.diversity_threshold
            after = round(max(0.5, before - 0.15 * boredom), 4)
            if after != before:
                updates["diversity_threshold"] = after
                plan.changes.append(
                    ModulationChange(
                        "diversity_threshold",
                        before,
                        after,
                        "boredom",
                        boredom,
                        "Ground already covered — suppress near-duplicates harder.",
                        bounded_by="diversity_threshold >= 0.5",
                    )
                )
        if "domain" not in skip and (boredom >= 0.3 or exhausted):
            plan.suggest_domain_jump = True
            plan.changes.append(
                ModulationChange(
                    "domain",
                    str(config.domain),
                    "<caller picks a new one>",
                    "boredom",
                    boredom,
                    "This vein is mined out; the honest move is to change ground.",
                )
            )

    # --- hubris makes the system demand evidence of itself --------------------
    if hubris >= _STRENGTH_FLOOR and not config.use_literature:
        updates["use_literature"] = True
        plan.changes.append(
            ModulationChange(
                "use_literature",
                False,
                True,
                "hubris",
                hubris,
                "Confidence outran the evidence — go and get some before ranking further.",
            )
        )

    # --- determination presses a live target ----------------------------------
    if determination >= _STRENGTH_FLOOR and confusion < _STRENGTH_FLOOR:
        plan.force_decompose = True
        plan.changes.append(
            ModulationChange(
                "force_decompose",
                False,
                True,
                "determination",
                determination,
                "A workable high-value target is live — turn it into a plan.",
            )
        )

    # --- frustration / resignation stop the loop ------------------------------
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
        plan.changes.append(
            ModulationChange(
                "stop",
                False,
                True,
                driver,
                max(frustration, resignation),
                plan.stop_reason,
            )
        )

    # --- safety: affect tightens the risk ceiling on itself -------------------
    anxiety = _strength(mix_weights, "anxiety")
    reluctance = _strength(mix_weights, "reluctance")
    if max(anxiety, reluctance) >= _STRENGTH_FLOOR:
        driver = "anxiety" if anxiety >= reluctance else "reluctance"
        strength = max(anxiety, reluctance)
        before = float(profile.max_risk)
        after = round(max(0.05, before - 0.1 * strength), 4)
        if after < before:
            profile = profile.model_copy(update={"max_risk": after})
            updates["value_profile"] = profile
            plan.changes.append(
                ModulationChange(
                    "value_profile.max_risk",
                    before,
                    after,
                    driver,
                    strength,
                    "Dual-use or high-risk material present — lower the ceiling. "
                    "Affect is allowed to make the gate stricter, never looser.",
                    bounded_by="max_risk >= 0.05",
                )
            )
        plan.require_review = True
        plan.changes.append(
            ModulationChange(
                "require_review",
                False,
                True,
                driver,
                strength,
                "Route through human review before acting on this set.",
            )
        )

    # --- doubt about the evidence itself --------------------------------------
    skepticism = _strength(mix_weights, "skepticism") + _strength(mix_weights, "suspicion")
    if skepticism >= _STRENGTH_FLOOR:
        plan.force_soundness = True
        plan.changes.append(
            ModulationChange(
                "force_soundness",
                False,
                True,
                "skepticism",
                skepticism,
                "Grounding looked shaky — run the soundness pass before trusting ranks.",
            )
        )
        if not config.use_literature:
            updates["use_literature"] = True
            plan.changes.append(
                ModulationChange(
                    "use_literature",
                    False,
                    True,
                    "skepticism",
                    skepticism,
                    "Go and check the neighbourhood rather than assuming it.",
                )
            )

    # --- lost the frame: shrink and re-derive rather than widen ----------------
    disorientation = _strength(mix_weights, "disorientation")
    if disorientation >= _STRENGTH_FLOOR:
        before = config.n_return
        after = max(2, before // 2)
        if after != before:
            updates["n_return"] = after
            plan.changes.append(
                ModulationChange(
                    "n_return",
                    before,
                    after,
                    "disorientation",
                    disorientation,
                    "The frame is unclear — shrink the field and re-derive the question.",
                    bounded_by="n_return >= 2",
                )
            )
        plan.force_decompose = True

    # --- urgency / impatience: cheaper, narrower, sooner -----------------------
    urgency = _strength(mix_weights, "urgency")
    impatience = _strength(mix_weights, "impatience")
    if max(urgency, impatience) >= _STRENGTH_FLOOR:
        pressure = max(urgency, impatience)
        before = config.n_return
        after = max(3, int(round(before * (1.0 - 0.25 * pressure))))
        if after != before:
            updates["n_return"] = after
            plan.changes.append(
                ModulationChange(
                    "n_return",
                    before,
                    after,
                    "urgency" if urgency >= impatience else "impatience",
                    pressure,
                    "Take the cheap discriminating step rather than more breadth.",
                    bounded_by="n_return >= 3",
                )
            )

    # --- outcomes worth writing down ------------------------------------------
    for name, note in (
        ("triumph", "A result that holds up — turn it into a concrete plan."),
        ("satisfaction", "Proportionate to the question asked — write the plan."),
    ):
        strength = _strength(mix_weights, name)
        if strength >= _STRENGTH_FLOOR:
            plan.force_decompose = True
            plan.changes.append(
                ModulationChange("force_decompose", False, True, name, strength, note)
            )

    # --- ground that closed before we got to it -------------------------------
    disappointment = _strength(mix_weights, "disappointment")
    if disappointment >= _STRENGTH_FLOOR:
        plan.suggest_domain_jump = True
        plan.changes.append(
            ModulationChange(
                "domain",
                str(config.domain),
                "<caller picks a new one>",
                "disappointment",
                disappointment,
                "These gaps already closed — record the nulls and move.",
            )
        )

    # --- opt-in, bounded weight nudges ----------------------------------------
    if allow_weight_deltas:
        deltas: dict[str, float] = {}
        if curiosity >= _STRENGTH_FLOOR and "value_profile.weight_surprise" not in skip:
            deltas["weight_surprise"] = min(MAX_WEIGHT_DELTA, 0.1 * curiosity)
        if confusion >= _STRENGTH_FLOOR:
            deltas["weight_tractability"] = min(MAX_WEIGHT_DELTA, 0.1 * confusion)
        if boredom >= _STRENGTH_FLOOR and "value_profile.weight_neglectedness" not in skip:
            deltas["weight_neglectedness"] = min(MAX_WEIGHT_DELTA, 0.1 * boredom)
        if deltas:
            fields: dict[str, Any] = {}
            for knob, delta in deltas.items():
                before = float(getattr(profile, knob))
                after = round(min(2.0, before + delta), 4)
                fields[knob] = after
                plan.changes.append(
                    ModulationChange(
                        f"value_profile.{knob}",
                        before,
                        after,
                        max(mix_weights, key=mix_weights.get) if mix_weights else "affect",
                        delta,
                        "Opt-in affect nudge on a scoring weight.",
                        bounded_by=f"|delta| <= {MAX_WEIGHT_DELTA}",
                    )
                )
            profile = profile.model_copy(update=fields)
            updates["value_profile"] = profile
            plan.weights_touched = True

    new_config = config.model_copy(update=updates) if updates else config.model_copy()
    return new_config, plan
