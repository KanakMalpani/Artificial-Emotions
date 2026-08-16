"""Catalog effect applicators for modulation.

Callers import from ``artificial_emotions.modulate`` (stable). This module
enacts frozen catalog ``effects`` ids via :func:`apply_effects`. Plan assembly
(ambivalence, stay aggregation, stop, weight deltas) lives in ``modulate``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

from artificial_emotions.appraisal import EFFECT_IDS
from artificial_emotions.models import CuriosityConfig

__all__ = [
    "ALWAYS_ON_HIGH_COERCION_EFFECTS",
    "HIGH_COERCION_IDS",
    "MAX_WEIGHT_DELTA",
    "ModulationChange",
    "ModulationPlan",
    "apply_effects",
    "high_coercion_effect_allowed",
    "somatic_modulate_requested",
]

#: Same ceiling the preference-hint path uses. Affect nudges; it never steers.
MAX_WEIGHT_DELTA = 0.08

_STRENGTH_FLOOR = 0.15  # below this an emotion is present but not driving

#: Somatic cluster — catalog ``coercion: ""`` is unset, not ``low``. These ids
#: are high-coercion even while Wave 0 placeholders remain empty.
HIGH_COERCION_IDS: frozenset[str] = frozenset({"fear", "anger", "disgust", "joy", "sadness"})

#: Frozen-vocabulary effects that may run without ``--somatic-modulate``.
ALWAYS_ON_HIGH_COERCION_EFFECTS: frozenset[str] = frozenset({"tighten_safety", "drop_dual_use"})

#: ``jump_ground`` for these ids is the stop/leave-the-line characterization,
#: not a domain hop — domain hop would fight ``stay_the_course``.
_STOP_ON_JUMP: frozenset[str] = frozenset({"frustration", "resignation"})

#: Intrigue widens less than curiosity (catalog: weaker than curiosity).
_WIDEN_FACTOR = {"curiosity": 0.5, "intrigue": 0.25}


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
    drop_dual_use: bool = False
    forbid_similar_jump: bool = False
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
        if self.drop_dual_use:
            out["drop_dual_use"] = True
        if self.forbid_similar_jump:
            out["forbid_similar_jump"] = True
        if self.ambivalence_enacted:
            out["ambivalence_enacted"] = True
            out["pattern_not_motive"] = True
            out["claims"] = list(self.claims)
            out["because"] = self.because
            out["skipped_exclusive"] = list(self.skipped_exclusive)
        return out


@dataclass
class _EffectState:
    """Working set for ``apply_effects``. Config is never mutated."""

    config: CuriosityConfig
    updates: dict[str, Any]
    skip: frozenset[str]
    exhausted: bool
    mix_weights: Mapping[str, float]


def _strength(weights: Mapping[str, float], emotion: str) -> float:
    return float(weights.get(emotion, 0.0))


@lru_cache(maxsize=1)
def _catalog_effect_index() -> dict[str, tuple[tuple[str, ...], str]]:
    """id → (effects, coercion). Catalog is the source of truth."""
    from artificial_emotions.emotions import emotion_catalog

    out: dict[str, tuple[tuple[str, ...], str]] = {}
    for entry in emotion_catalog().get("emotions") or []:
        eid = str(entry.get("id") or "")
        if not eid:
            continue
        effects = tuple(str(e) for e in (entry.get("effects") or []) if str(e) in EFFECT_IDS)
        coercion = str(entry.get("coercion") or "")
        out[eid] = (effects, coercion)
    return out


def _effect_permitted(
    effect_id: str,
    *,
    opt_in: bool,
    emotion_id: str,
    coercion: str,
    effects: Sequence[str],
) -> bool:
    """High-coercion search knobs need opt-in; relief stay_course is opt-in too."""
    if effect_id == "stay_course" and "surface_only" in effects and not opt_in:
        return False
    return high_coercion_effect_allowed(
        effect_id,
        somatic_modulate=opt_in,
        emotion_id=emotion_id,
        coercion=coercion,
    )


def _record(
    plan: ModulationPlan,
    *,
    knob: str,
    before: Any,
    after: Any,
    driver: str,
    strength: float,
    rationale: str,
    bounded_by: str | None = None,
) -> None:
    plan.changes.append(
        ModulationChange(knob, before, after, driver, strength, rationale, bounded_by)
    )


def _current_n_candidates(state: _EffectState) -> int:
    return int(state.updates.get("n_candidates", state.config.n_candidates))


def _current_n_return(state: _EffectState) -> int:
    return int(state.updates.get("n_return", state.config.n_return))


def _current_profile(state: _EffectState) -> Any:
    return state.updates.get("value_profile", state.config.value_profile)


def _narrow_n_return(emotion_id: str, strength: float, base: int) -> int:
    """Preserve per-driver characterization of ``narrow_search``."""
    if emotion_id == "disorientation":
        return max(2, base // 2)
    if emotion_id in {"urgency", "impatience"}:
        return max(3, int(round(base * (1.0 - 0.25 * strength))))
    return max(3, int(round(base * (1.0 - 0.4 * min(strength, 0.8)))))


def apply_effects(
    plan: ModulationPlan,
    effects: Sequence[str],
    strength: float,
    opt_in: bool,
    *,
    emotion_id: str = "",
    coercion: str = "",
    state: _EffectState | None = None,
) -> None:
    """Enact frozen catalog effect ids. Does not invent extras.

    High-coercion search effects need ``opt_in``. ``tighten_safety`` and
    ``drop_dual_use`` may run without it. Never raises ``max_risk``.
    """
    if strength < _STRENGTH_FLOOR or state is None:
        return
    driver = emotion_id or "affect"
    for raw in effects:
        effect = str(raw)
        if effect not in EFFECT_IDS:
            continue
        if not _effect_permitted(
            effect,
            opt_in=opt_in,
            emotion_id=driver,
            coercion=coercion,
            effects=effects,
        ):
            continue
        if effect == "surface_only":
            continue
        if effect == "widen_search":
            _apply_widen_search(plan, state, driver, strength)
        elif effect == "narrow_search":
            _apply_narrow_search(plan, state, driver, strength)
        elif effect == "demand_literature":
            _apply_demand_literature(plan, state, driver, strength)
        elif effect == "decompose":
            _apply_decompose(plan, state, driver, strength)
        elif effect == "jump_ground":
            _apply_jump_ground(plan, state, driver, strength)
        elif effect == "forbid_similar_jump":
            _apply_forbid_similar_jump(plan, driver, strength)
        elif effect == "tighten_safety":
            _apply_tighten_safety(plan, state, driver, strength)
        elif effect == "drop_dual_use":
            _apply_drop_dual_use(plan, driver, strength)
        elif effect == "stay_course":
            _apply_stay_course(plan, driver, strength)


def _apply_widen_search(
    plan: ModulationPlan, state: _EffectState, driver: str, strength: float
) -> None:
    if "n_candidates" in state.skip:
        return
    factor = _WIDEN_FACTOR.get(driver, 0.5)
    before = _current_n_candidates(state)
    after = min(64, int(round(state.config.n_candidates * (1.0 + factor * strength))))
    if after <= before:
        return
    state.updates["n_candidates"] = after
    _record(
        plan,
        knob="n_candidates",
        before=before,
        after=after,
        driver=driver,
        strength=strength,
        rationale="Open, neglected gaps are worth casting wider for.",
        bounded_by="n_candidates <= 64",
    )


def _apply_narrow_search(
    plan: ModulationPlan, state: _EffectState, driver: str, strength: float
) -> None:
    before = _current_n_return(state)
    proposed = _narrow_n_return(driver, strength, state.config.n_return)
    after = min(before, proposed)
    if after >= before:
        return
    state.updates["n_return"] = after
    bound = "n_return >= 2" if driver == "disorientation" else "n_return >= 3"
    if driver == "disorientation":
        rationale = "The frame is unclear — shrink the field and re-derive the question."
    elif driver in {"urgency", "impatience"}:
        rationale = "Take the cheap discriminating step rather than more breadth."
    else:
        rationale = "Disagreement or loose posing — return fewer, look harder."
    _record(
        plan,
        knob="n_return",
        before=before,
        after=after,
        driver=driver,
        strength=strength,
        rationale=rationale,
        bounded_by=bound,
    )


def _apply_demand_literature(
    plan: ModulationPlan, state: _EffectState, driver: str, strength: float
) -> None:
    already = bool(state.updates.get("use_literature", state.config.use_literature))
    if not already:
        state.updates["use_literature"] = True
        if driver == "hubris":
            rationale = "Confidence outran the evidence — go and get some before ranking further."
        elif driver in {"skepticism", "suspicion"}:
            rationale = "Go and check the neighbourhood rather than assuming it."
        else:
            rationale = "Demand literature rather than ranking on a thin neighbourhood."
        _record(
            plan,
            knob="use_literature",
            before=False,
            after=True,
            driver=driver,
            strength=strength,
            rationale=rationale,
        )
    if driver in {"skepticism", "suspicion"}:
        if not plan.force_soundness:
            plan.force_soundness = True
            _record(
                plan,
                knob="force_soundness",
                before=False,
                after=True,
                driver=driver,
                strength=strength,
                rationale="Grounding looked shaky — run the soundness pass before trusting ranks.",
            )


def _apply_decompose(
    plan: ModulationPlan, state: _EffectState, driver: str, strength: float
) -> None:
    confusion = _strength(state.mix_weights, "confusion") + _strength(
        state.mix_weights, "perplexity"
    )
    if driver == "determination" and confusion >= _STRENGTH_FLOOR:
        return
    notes = {
        "confusion": "A confusing result is exactly what decomposition is for.",
        "perplexity": "A confusing result is exactly what decomposition is for.",
        "determination": "A workable high-value target is live — turn it into a plan.",
        "disorientation": "The frame is unclear — shrink the field and re-derive the question.",
        "triumph": "A result that holds up — turn it into a concrete plan.",
        "satisfaction": "Proportionate to the question asked — write the plan.",
    }
    plan.force_decompose = True
    _record(
        plan,
        knob="force_decompose",
        before=False,
        after=True,
        driver=driver,
        strength=strength,
        rationale=notes.get(driver, "Turn the live target into a plan rather than more breadth."),
    )


def _apply_jump_ground(
    plan: ModulationPlan, state: _EffectState, driver: str, strength: float
) -> None:
    if driver in _STOP_ON_JUMP:
        return
    if driver == "boredom":
        if "diversity_threshold" not in state.skip:
            before_div = float(
                state.updates.get("diversity_threshold", state.config.diversity_threshold)
            )
            after_div = round(max(0.5, state.config.diversity_threshold - 0.15 * strength), 4)
            if after_div < before_div:
                state.updates["diversity_threshold"] = after_div
                _record(
                    plan,
                    knob="diversity_threshold",
                    before=before_div,
                    after=after_div,
                    driver=driver,
                    strength=strength,
                    rationale="Ground already covered — suppress near-duplicates harder.",
                    bounded_by="diversity_threshold >= 0.5",
                )
        if "domain" in state.skip or not (strength >= 0.3 or state.exhausted):
            return
    if "domain" in state.skip:
        return
    plan.suggest_domain_jump = True
    if driver == "boredom":
        rationale = "This vein is mined out; the honest move is to change ground."
    elif driver == "disappointment":
        rationale = "These gaps already closed — record the nulls and move."
    else:
        rationale = "Leave this line; the honest move is to change ground."
    _record(
        plan,
        knob="domain",
        before=str(state.config.domain),
        after="<caller picks a new one>",
        driver=driver,
        strength=strength,
        rationale=rationale,
    )


def _apply_forbid_similar_jump(plan: ModulationPlan, driver: str, strength: float) -> None:
    plan.forbid_similar_jump = True
    _record(
        plan,
        knob="forbid_similar_jump",
        before=False,
        after=True,
        driver=driver,
        strength=strength,
        rationale="Progress is blocked on abandoned ground — do not jump to a similar vein.",
    )


def _apply_tighten_safety(
    plan: ModulationPlan, state: _EffectState, driver: str, strength: float
) -> None:
    profile = _current_profile(state)
    before = float(profile.max_risk)
    after = round(max(0.05, before - 0.1 * strength), 4)
    if after < before:
        state.updates["value_profile"] = profile.model_copy(update={"max_risk": after})
        _record(
            plan,
            knob="value_profile.max_risk",
            before=before,
            after=after,
            driver=driver,
            strength=strength,
            rationale=(
                "Dual-use or high-risk material present — lower the ceiling. "
                "Affect is allowed to make the gate stricter, never looser."
            ),
            bounded_by="max_risk >= 0.05",
        )
    plan.require_review = True
    _record(
        plan,
        knob="require_review",
        before=False,
        after=True,
        driver=driver,
        strength=strength,
        rationale="Route through human review before acting on this set.",
    )


def _apply_drop_dual_use(plan: ModulationPlan, driver: str, strength: float) -> None:
    plan.drop_dual_use = True
    plan.require_review = True
    _record(
        plan,
        knob="drop_dual_use",
        before=False,
        after=True,
        driver=driver,
        strength=strength,
        rationale="Dual-use flagged candidates drop rather than rank. Never loosens safety.",
    )


def _apply_stay_course(plan: ModulationPlan, driver: str, strength: float) -> None:
    plan.stay_the_course = True
    _record(
        plan,
        knob="stay_the_course",
        before=False,
        after=True,
        driver=driver,
        strength=strength,
        rationale="A live, reachable thread is running — do not change ground yet.",
    )
