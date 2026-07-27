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

from dataclasses import dataclass, field
from typing import Any

from artificial_emotions.models import CuriosityConfig

__all__ = [
    "MAX_WEIGHT_DELTA",
    "ModulationChange",
    "ModulationPlan",
    "modulate_config",
]

#: Same ceiling the preference-hint path uses. Affect nudges; it never steers.
MAX_WEIGHT_DELTA = 0.08

_STRENGTH_FLOOR = 0.15  # below this an emotion is present but not driving


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
    stop: bool = False
    stop_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "changes": [c.to_dict() for c in self.changes],
            "n_changes": len(self.changes),
            "weights_touched": self.weights_touched,
            "force_decompose": self.force_decompose,
            "suggest_domain_jump": self.suggest_domain_jump,
            "stop": self.stop,
            "stop_reason": self.stop_reason,
            "honesty": (
                "Affect modulates search behaviour. ValueProfile weights are "
                "untouched unless allow_weight_deltas was set, and any delta is "
                f"capped at ±{MAX_WEIGHT_DELTA} and listed above."
            ),
        }


def _strength(weights: dict[str, float], emotion: str) -> float:
    return float(weights.get(emotion, 0.0))


def modulate_config(
    config: CuriosityConfig,
    mix_weights: dict[str, float],
    *,
    allow_weight_deltas: bool = False,
    exhausted: bool = False,
) -> tuple[CuriosityConfig, ModulationPlan]:
    """Return a new config shaped by the current affect, plus the audit trail.

    Args:
        config: the run configuration to adjust.
        mix_weights: normalized emotion weights from the appraised mix.
        allow_weight_deltas: permit bounded ValueProfile nudges (default off).
        exhausted: the trajectory has stopped surfacing anything new.

    Returns:
        ``(new_config, plan)``. The input config is never mutated.
    """
    plan = ModulationPlan()
    updates: dict[str, Any] = {}

    curiosity = _strength(mix_weights, "curiosity")
    confusion = _strength(mix_weights, "confusion") + _strength(mix_weights, "perplexity")
    boredom = _strength(mix_weights, "boredom")
    hubris = _strength(mix_weights, "hubris")
    frustration = _strength(mix_weights, "frustration")
    resignation = _strength(mix_weights, "resignation")
    determination = _strength(mix_weights, "determination")

    # --- curiosity widens the net ---------------------------------------------
    if curiosity >= _STRENGTH_FLOOR:
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
        if boredom >= 0.3 or exhausted:
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
    if frustration >= 0.35 or resignation >= 0.3 or exhausted:
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

    # --- opt-in, bounded weight nudges ----------------------------------------
    profile = config.value_profile
    if allow_weight_deltas:
        deltas: dict[str, float] = {}
        if curiosity >= _STRENGTH_FLOOR:
            deltas["weight_surprise"] = min(MAX_WEIGHT_DELTA, 0.1 * curiosity)
        if confusion >= _STRENGTH_FLOOR:
            deltas["weight_tractability"] = min(MAX_WEIGHT_DELTA, 0.1 * confusion)
        if boredom >= _STRENGTH_FLOOR:
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
