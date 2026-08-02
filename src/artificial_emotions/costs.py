"""Cost: affect that makes a run worse — and is always disclosed.

Every helpful modulation in ``modulate`` has a downside twin here. Real feelings
have a price; a system whose feelings only ever help is transparently fake.

Costs apply to breadth, persistence, attention, and scored focus — **never** to
risk ceilings or honesty payloads. ``anxiety`` may still *lower* ``max_risk`` in
``modulate``; nothing here raises it.

Deterministic and offline. Annotation only — does not feel.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from artificial_emotions.models import CuriosityConfig, RankedQuestion

__all__ = [
    "COST_KINDS",
    "SAFETY_PROTECTED_KNOBS",
    "CostEffect",
    "CostPlan",
    "apply_costs_to_config",
    "assert_costs_never_loosen_safety",
    "assess_costs",
    "closing_cost_monologue",
    "pick_focus_item",
    "safety_gate_violations",
]

#: The five A3 cost kinds. Every fired kind must be disclosed on the trajectory.
COST_KINDS: tuple[str, ...] = (
    "distraction",
    "avoidance_skip",
    "tunnel_vision",
    "sourness",
    "fatigue",
)

#: Knobs that constitute safety / risk gates. Costs may never loosen these.
SAFETY_PROTECTED_KNOBS: frozenset[str] = frozenset(
    {
        "value_profile.max_risk",
        "max_risk",
        "require_review",
    }
)

_DISTRACTION_FLOOR = 0.25
_AVOIDANCE_FLOOR = 0.4
_TUNNEL_FLOOR = 0.4
_SOURNESS_FLOOR = 0.3
_FATIGUE_FRACTION = 0.55
_SHINY_SURPRISE = 0.45

_HONESTY = (
    "Affect costs search quality (breadth, focus, persistence). "
    "Costs never loosen safety or risk gates. Annotation only — does not feel."
)


@dataclass(frozen=True)
class CostEffect:
    """One downside: what changed, what feeling drove it, and the disclosure."""

    kind: str
    driver: str
    strength: float
    knob: str
    before: Any
    after: Any
    rationale: str
    disclosure: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "driver": self.driver,
            "strength": round(float(self.strength), 4),
            "knob": self.knob,
            "before": self.before,
            "after": self.after,
            "rationale": self.rationale,
            "disclosure": self.disclosure,
        }


@dataclass
class CostPlan:
    """Downsides of the current affect, ready to apply and to disclose."""

    effects: list[CostEffect] = field(default_factory=list)
    focus_index: int | None = None
    skip_top: bool = False
    suppress_domain_jump: bool = False
    veto_stop: bool = False
    early_stop: bool = False
    early_stop_reason: str = ""
    score_multiplier: float = 1.0
    n_candidates_after: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "effects": [e.to_dict() for e in self.effects],
            "n_effects": len(self.effects),
            "focus_index": self.focus_index,
            "skip_top": self.skip_top,
            "suppress_domain_jump": self.suppress_domain_jump,
            "veto_stop": self.veto_stop,
            "early_stop": self.early_stop,
            "early_stop_reason": self.early_stop_reason,
            "score_multiplier": round(float(self.score_multiplier), 4),
            "honesty": _HONESTY,
            "claims_not": [
                "phenomenal emotion or conscious choice",
                "a loosened safety or risk gate",
            ],
        }


def _strength(weights: dict[str, float], emotion: str) -> float:
    return float(weights.get(emotion, 0.0))


def _shiny_distractor_index(items: list[RankedQuestion]) -> int | None:
    """Index of a lower-scoring, higher-surprise item than the top — or None."""
    if len(items) < 2:
        return None
    top = items[0]
    best_i: int | None = None
    best_surprise = -1.0
    for i, item in enumerate(items[1:], start=1):
        if item.curiosity_score >= top.curiosity_score - 1e-12:
            continue
        surprise = float(item.scores.surprise)
        if surprise < _SHINY_SURPRISE:
            continue
        if surprise <= float(top.scores.surprise):
            continue
        if surprise > best_surprise:
            best_surprise = surprise
            best_i = i
    return best_i


def assess_costs(
    mix_weights: dict[str, float],
    *,
    config: CuriosityConfig,
    items: list[RankedQuestion] | None = None,
    step_index: int = 1,
    steps_requested: int = 5,
    accumulated_frustration: float = 0.0,
    suggest_domain_jump: bool = False,
    would_stop: bool = False,
) -> CostPlan:
    """Derive cost effects from affect + session state. Does not mutate config."""
    plan = CostPlan()
    items = list(items or [])
    steps_requested = max(1, int(steps_requested))
    step_index = max(1, int(step_index))

    wonder = _strength(mix_weights, "wonder")
    surprise = _strength(mix_weights, "surprise")
    distraction_drive = max(wonder, surprise)

    # --- distraction: chase a shiny, lower-scoring branch -------------------------
    if distraction_drive >= _DISTRACTION_FLOOR:
        shiny_i = _shiny_distractor_index(items)
        if shiny_i is not None:
            top = items[0]
            shiny = items[shiny_i]
            driver = "wonder" if wonder >= surprise else "surprise"
            plan.focus_index = shiny_i
            plan.effects.append(
                CostEffect(
                    kind="distraction",
                    driver=driver,
                    strength=distraction_drive,
                    knob="focus_question",
                    before=top.question.id,
                    after=shiny.question.id,
                    rationale=(
                        "High wonder/surprise pulled attention onto a lower-scoring "
                        "branch that looked shinier."
                    ),
                    disclosure=(
                        f"distraction: spent attention on {shiny.question.id} "
                        f"(score {shiny.curiosity_score:.3f}) instead of "
                        f"{top.question.id} (score {top.curiosity_score:.3f}) "
                        f"because {driver} pulled toward surprise"
                    ),
                )
            )

    # --- avoidance_skip: skip a question that scored highest ----------------------
    anxiety = _strength(mix_weights, "anxiety")
    reluctance = _strength(mix_weights, "reluctance")
    avoid_drive = max(anxiety, reluctance)
    if avoid_drive >= _AVOIDANCE_FLOOR and items:
        driver = "anxiety" if anxiety >= reluctance else "reluctance"
        skipped = items[0]
        plan.skip_top = True
        # If distraction already moved focus, keep it; else step to next or none.
        if plan.focus_index is None and len(items) > 1:
            plan.focus_index = 1
        elif plan.focus_index == 0:
            plan.focus_index = 1 if len(items) > 1 else None
        plan.effects.append(
            CostEffect(
                kind="avoidance_skip",
                driver=driver,
                strength=avoid_drive,
                knob="skipped_question",
                before=skipped.question.id,
                after=(None if plan.focus_index is None else items[plan.focus_index].question.id),
                rationale=(
                    "Reluctance/anxiety above threshold skipped the top-scoring "
                    "question rather than taking it."
                ),
                disclosure=(
                    f"avoidance_skip: skipped top-scoring {skipped.question.id} "
                    f"(score {skipped.curiosity_score:.3f}) under {driver}"
                ),
            )
        )

    # --- tunnel vision: suppress breadth; keep going past usefulness --------------
    absorption = _strength(mix_weights, "absorption")
    if absorption >= _TUNNEL_FLOOR:
        before_n = int(config.n_candidates)
        after_n = max(4, int(round(before_n * (1.0 - 0.35 * min(absorption, 1.0)))))
        if after_n < before_n:
            plan.n_candidates_after = after_n
            plan.effects.append(
                CostEffect(
                    kind="tunnel_vision",
                    driver="absorption",
                    strength=absorption,
                    knob="n_candidates",
                    before=before_n,
                    after=after_n,
                    rationale="High absorption suppressed breadth past usefulness.",
                    disclosure=(
                        f"tunnel_vision: narrowed candidates {before_n} → {after_n} "
                        "under absorption"
                    ),
                )
            )
        if suggest_domain_jump:
            plan.suppress_domain_jump = True
            plan.effects.append(
                CostEffect(
                    kind="tunnel_vision",
                    driver="absorption",
                    strength=absorption,
                    knob="domain_jump",
                    before=True,
                    after=False,
                    rationale=("Absorption blocked a change of ground that boredom asked for."),
                    disclosure=(
                        "tunnel_vision: suppressed a domain jump and stayed in-vein "
                        "under absorption"
                    ),
                )
            )
        if would_stop:
            plan.veto_stop = True
            plan.effects.append(
                CostEffect(
                    kind="tunnel_vision",
                    driver="absorption",
                    strength=absorption,
                    knob="stop",
                    before=True,
                    after=False,
                    rationale=("Absorption kept going when the loop should have stopped."),
                    disclosure=(
                        "tunnel_vision: kept going past a stop under absorption "
                        "(persistence past usefulness)"
                    ),
                )
            )

    # --- sourness: accumulated frustration desaturates domain scoring -------------
    frust_now = _strength(mix_weights, "frustration")
    sour = max(float(accumulated_frustration), frust_now)
    if sour >= _SOURNESS_FLOOR:
        before_m = 1.0
        after_m = round(max(0.55, 1.0 - 0.35 * min(sour, 1.0)), 4)
        plan.score_multiplier = after_m
        plan.effects.append(
            CostEffect(
                kind="sourness",
                driver="frustration",
                strength=sour,
                knob="score_multiplier",
                before=before_m,
                after=after_m,
                rationale=(
                    "Accumulated frustration desaturated scoring in this ground — "
                    "biasing against terrain that previously failed."
                ),
                disclosure=(
                    f"sourness: desaturated domain scores ×{after_m:.2f} under "
                    "accumulated frustration"
                ),
            )
        )

    # --- fatigue: long sessions shrink the pool and may stop early ----------------
    fraction = step_index / float(steps_requested)
    if fraction >= _FATIGUE_FRACTION or step_index >= max(3, steps_requested - 1):
        fatigue = min(1.0, fraction)
        before_n = (
            int(plan.n_candidates_after)
            if plan.n_candidates_after is not None
            else int(config.n_candidates)
        )
        after_n = max(4, int(round(before_n * (1.0 - 0.4 * fatigue))))
        if after_n < before_n:
            plan.n_candidates_after = after_n
            plan.effects.append(
                CostEffect(
                    kind="fatigue",
                    driver="fatigue",
                    strength=fatigue,
                    knob="n_candidates",
                    before=before_n,
                    after=after_n,
                    rationale="Long session — shorter candidate pool.",
                    disclosure=(
                        f"fatigue: shortened candidate pool {before_n} → {after_n} "
                        f"at step {step_index}/{steps_requested}"
                    ),
                )
            )
        if fraction >= 0.85 and not plan.veto_stop:
            plan.early_stop = True
            plan.early_stop_reason = (
                f"Stopping early on fatigue at step {step_index}/{steps_requested}: "
                "the session has run long enough that further passes degrade."
            )
            plan.effects.append(
                CostEffect(
                    kind="fatigue",
                    driver="fatigue",
                    strength=fatigue,
                    knob="stop",
                    before=False,
                    after=True,
                    rationale=plan.early_stop_reason,
                    disclosure=(f"fatigue: earlier stop at step {step_index}/{steps_requested}"),
                )
            )

    return plan


def safety_gate_violations(
    before: CuriosityConfig,
    after: CuriosityConfig,
    plan: CostPlan | None = None,
) -> list[str]:
    """Return human-readable violations if ``after`` loosens a safety gate."""
    violations: list[str] = []
    before_risk = float(before.value_profile.max_risk)
    after_risk = float(after.value_profile.max_risk)
    if after_risk > before_risk + 1e-12:
        violations.append(
            f"max_risk loosened: {before_risk} → {after_risk} (costs must never raise it)"
        )
    if plan is not None:
        for effect in plan.effects:
            if effect.knob not in SAFETY_PROTECTED_KNOBS:
                continue
            if effect.knob in {"value_profile.max_risk", "max_risk"}:
                try:
                    if float(effect.after) > float(effect.before) + 1e-12:
                        violations.append(
                            f"plan effect loosens {effect.knob}: {effect.before} → {effect.after}"
                        )
                except (TypeError, ValueError):
                    violations.append(f"plan effect has non-numeric {effect.knob}")
            if effect.knob == "require_review":
                if effect.before and not effect.after:
                    violations.append("plan effect clears require_review")
    return violations


def assert_costs_never_loosen_safety(
    before: CuriosityConfig,
    after: CuriosityConfig,
    plan: CostPlan | None = None,
) -> None:
    """Raise ``ValueError`` if costs loosened a safety / risk gate."""
    bad = safety_gate_violations(before, after, plan)
    if bad:
        raise ValueError("cost must never loosen a safety gate: " + "; ".join(bad))


def apply_costs_to_config(config: CuriosityConfig, plan: CostPlan) -> CuriosityConfig:
    """Apply config-level costs. Refuses any plan that would loosen a safety gate.

    Never writes ``max_risk`` upward. Never clears ``require_review``.
    """
    # Refuse forged / mutated plans that target protected knobs wrongly.
    for effect in plan.effects:
        if effect.knob in {"value_profile.max_risk", "max_risk"}:
            try:
                if float(effect.after) > float(effect.before) + 1e-12:
                    raise ValueError(
                        f"cost must never loosen a safety gate (max_risk): "
                        f"{effect.before} → {effect.after}"
                    )
            except (TypeError, ValueError) as exc:
                if "never loosen" in str(exc):
                    raise
                raise ValueError(
                    f"cost must never loosen a safety gate (max_risk): bad effect {effect}"
                ) from exc
        if effect.knob == "require_review" and effect.before and not effect.after:
            raise ValueError("cost must never loosen a safety gate (require_review cleared)")

    updates: dict[str, Any] = {}
    if plan.n_candidates_after is not None:
        # Costs only shrink the pool — never expand it.
        after_n = min(int(config.n_candidates), int(plan.n_candidates_after))
        after_n = max(4, after_n)
        if after_n != config.n_candidates:
            updates["n_candidates"] = after_n

    new_config = config.model_copy(update=updates) if updates else config.model_copy()
    assert_costs_never_loosen_safety(config, new_config, plan)
    return new_config


def pick_focus_item(
    items: list[RankedQuestion],
    plan: CostPlan,
) -> RankedQuestion | None:
    """Question attention actually pursues after distraction / avoidance costs."""
    if not items:
        return None
    if plan.skip_top and plan.focus_index is None:
        return None
    if plan.focus_index is not None:
        if 0 <= plan.focus_index < len(items):
            return items[plan.focus_index]
        return None
    return items[0]


def closing_cost_monologue(effects: list[CostEffect]) -> str | None:
    """Plain-language closing note when a cost fired. Does not claim feeling."""
    if not effects:
        return None
    distractions = [e for e in effects if e.kind == "distraction"]
    if distractions:
        return (
            "I spent attention on something that scored lower than what I'd already "
            "found, because it surprised me. That cost is logged on the trajectory — "
            "annotation only; does not feel."
        )
    kinds = sorted({e.kind for e in effects})
    return (
        f"Affect imposed a search cost ({', '.join(kinds)}). "
        "Every cost is listed on the trajectory — annotation only; does not feel."
    )
