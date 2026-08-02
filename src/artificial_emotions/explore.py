"""The loop: curiosity with causes, consequences, and a history.

Ranking answers "what is worth investigating". This answers something a single
ranking cannot: **where does attention go next, and why.**

Each step the engine ranks, appraises what it found, feels something as a
*result* of that, lets the feeling change how it searches, and remembers where
it has been. Run it for a few steps and you get a research trajectory — a path
through a field with the reasoning for every turn attached, ending in a
decomposed plan for the best thing it found.

    appraise → feel → modulate → remember → repeat

What it is not: a closed-loop scientist. It does not run experiments, does not
answer anything, and the path it takes is a heuristic walk under an explicit
ValueProfile — not an optimal search. Everything it felt and everything that
feeling changed is in the output, because affect you cannot audit is affect you
cannot trust.

Offline and deterministic: the same inputs produce the same trajectory.
"""

from __future__ import annotations

from typing import Any

from artificial_emotions.appraisal import appraise_run, signals_to_weights
from artificial_emotions.costs import (
    CostEffect,
    apply_costs_to_config,
    assess_costs,
    closing_cost_monologue,
    pick_focus_item,
)
from artificial_emotions.decompose import decompose_ranked
from artificial_emotions.emotions import mix_emotions
from artificial_emotions.models import CuriosityConfig, Domain, RankedQuestion
from artificial_emotions.modulate import modulate_config
from artificial_emotions.pipeline import CuriosityEngine
from artificial_emotions.trajectory import Trajectory, TrajectoryStep, question_terms

__all__ = ["MAX_STEPS", "explore"]

# persist_memory is off by default (library / MCP / HTTP). CLI may enable it.
# CURIOSITY_NO_MEMORY=1 keeps byte-identical offline behaviour regardless.

MAX_STEPS = 12

# Where boredom sends it next. Ordered so a jump lands somewhere genuinely
# different rather than an adjacent field.
_JUMP_ORDER: dict[str, str] = {
    "ai": "biology",
    "biology": "materials",
    "materials": "climate",
    "climate": "energy",
    "energy": "physics",
    "physics": "medicine",
    "medicine": "social",
    "social": "ai",
    "general": "ai",
}


def _next_domain(current: str, visited: list[str]) -> str:
    """Pick unvisited ground, following the jump order."""
    candidate = _JUMP_ORDER.get(str(current).lower(), "general")
    for _ in range(len(_JUMP_ORDER)):
        if candidate not in visited:
            return candidate
        candidate = _JUMP_ORDER.get(candidate, "general")
    return candidate


def _driver_of(plan_dict: dict[str, Any], knob: str) -> str:
    """Which feeling actually moved this knob — not merely the loudest one."""
    for change in plan_dict.get("changes", []):
        if change.get("knob") == knob:
            return str(change.get("driver") or "affect")
    return "affect"


def _step_note(plan_dict: dict[str, Any], primary: str, made_progress: bool) -> str:
    if plan_dict.get("stop"):
        return plan_dict.get("stop_reason", "Stopping.")
    if plan_dict.get("suggest_domain_jump"):
        return f"{_driver_of(plan_dict, 'domain').capitalize()} pushed a change of ground."
    if plan_dict.get("force_decompose"):
        driver = _driver_of(plan_dict, "force_decompose")
        return f"{driver.capitalize()} called for the ladder rather than more breadth."
    if not made_progress:
        return "Nothing new surfaced this step."
    return f"Kept going on {primary}."


def explore(
    *,
    domain: str = "ai",
    topic: str = "",
    steps: int = 5,
    n_return: int = 5,
    n_candidates: int = 16,
    profile_name: str | None = None,
    use_literature: bool = False,
    use_llm: bool = False,
    allow_weight_deltas: bool = False,
    allow_domain_jump: bool = True,
    decompose_depth: int = 1,
    seed: int = 42,
    persist_memory: bool = False,
    memory_path: str | None = None,
    temperament: str | Any | None = None,
    temperament_path: str | None = None,
) -> dict[str, Any]:
    """Run the curiosity loop and return the trajectory.

    Args:
        domain: where to start.
        steps: how many passes to take (clamped to ``MAX_STEPS``).
        allow_weight_deltas: let affect nudge ValueProfile weights (bounded, logged).
        allow_domain_jump: let boredom change ground.
        decompose_depth: depth of the closing investigation plan.
        persist_memory: when True (CLI), append a session to PersistentMemory
            after the run. Default False — MCP/HTTP must not enable this.
            Honours ``CURIOSITY_NO_MEMORY=1`` (no read/write).
        memory_path: optional override for the memory JSON path (tests).
        temperament: A5 preset name (``restless``/``cautious``/``dogged``/
            ``flighty``), ``custom`` to load ``temperament.toml``, a
            ``Temperament`` instance, or ``None`` (default — no personality
            bias; keeps fresh-install / NO_MEMORY payloads byte-identical).
        temperament_path: optional override for ``~/.artificial_emotions/temperament.toml``.

    Returns:
        The full trajectory: every step, what it felt and why, what that
        changed, and a decomposed plan for the strongest thing it found.
    """
    steps = max(1, min(int(steps), MAX_STEPS))
    from artificial_emotions.models import resolve_value_profile
    from artificial_emotions.temperament import (
        apply_to_config,
        bias_signal_weights,
        decay_frustration,
        disclosure_payload,
        mood_bias_from_temperament,
        resolve_temperament,
    )

    profile = resolve_value_profile(profile_name=profile_name)

    config = CuriosityConfig(
        domain=domain,
        topic=topic,
        n_return=n_return,
        n_candidates=n_candidates,
        use_llm=use_llm,
        use_literature=use_literature,
        value_profile=profile,
        seed=seed,
    )

    trail = Trajectory()
    best: RankedQuestion | None = None
    best_effective: float = float("-inf")
    last_mix: dict[str, Any] | None = None
    stop_reason = "Completed the requested number of steps."
    all_cost_effects: list[CostEffect] = []
    accumulated_frustration = 0.0

    # A5: optional temperament (None = no-op for determinism).
    active_temperament = resolve_temperament(temperament, path=temperament_path)
    temperament_applications: list[Any] = []
    if active_temperament is not None:
        config, temperament_applications = apply_to_config(config, active_temperament)

    # A2: load decayed mood carryover when persistence is on (never when opted out).
    mood_bias = None
    opening_mood_payload: dict[str, Any] | None = None
    # A4: scars / affinities bias config + domain jumps (disclosed when applied).
    scar_applications: list[Any] = []
    mem_scars: list[dict[str, Any]] = []
    mem_affinities: list[dict[str, Any]] = []
    if persist_memory:
        from artificial_emotions.affect import threshold_bias_from_pad
        from artificial_emotions.memory import PersistentMemory, memory_disabled
        from artificial_emotions.scars import apply_history_biases

        if not memory_disabled():
            mem = PersistentMemory.load(memory_path)
            stored = mem.mood_carryover
            opening = stored.decayed()
            if not opening.is_neutral():
                mood_bias = threshold_bias_from_pad(
                    stored.pleasure,
                    stored.arousal,
                    stored.dominance,
                    updated_at=stored.updated_at,
                )
                opening_mood_payload = {
                    **mood_bias.to_dict(),
                    "updated_at": stored.updated_at,
                    "stored": stored.to_dict(),
                }
            mem_scars = list(mem.scars)
            mem_affinities = list(mem.affinities)
            config, scar_applications = apply_history_biases(config, mem_scars, mem_affinities)

    # A5 baseline_mood biases appraisal floors when no stronger carryover is active.
    if mood_bias is None and active_temperament is not None:
        mood_bias = mood_bias_from_temperament(active_temperament)

    for step_index in range(1, steps + 1):
        items = CuriosityEngine(config).run()

        # Snapshot memory *before* folding this run in, or the step gets judged
        # as already-seen against its own terms and boredom pins high forever.
        terms: list[str] = []
        for item in items:
            terms.extend(question_terms(item.question.question))
        saturation_before = trail.term_saturation(terms)
        seen_before = set(trail.seen_question_ids)

        new_ids = trail.observe(items)

        signals = appraise_run(
            items,
            seen_question_ids=seen_before,
            term_saturation=saturation_before,
            steps_without_progress=trail.steps_without_progress(),
            mood_bias=mood_bias,
            temperament=active_temperament,
        )
        mix = mix_emotions(signals_to_weights(signals))
        last_mix = mix

        # Modulate on the *appraised* strengths, not the normalised mix. A mix
        # percentage says "how much of the blend is this", which shrinks as more
        # emotions fire — so a strong secondary signal would drop under the
        # action floor purely because other things also fired. Appraised weight
        # says "how strongly did the situation present this", which is what
        # should decide whether to act on it.
        signal_weights = {s.emotion: s.weight for s in signals}
        if active_temperament is not None:
            signal_weights = bias_signal_weights(signal_weights, active_temperament)
        accumulated_frustration = max(
            accumulated_frustration, float(signal_weights.get("frustration", 0.0))
        )
        if active_temperament is not None:
            accumulated_frustration = decay_frustration(accumulated_frustration, active_temperament)

        new_config, plan = modulate_config(
            config,
            signal_weights,
            allow_weight_deltas=allow_weight_deltas,
            exhausted=trail.is_exhausted(),
        )

        # A3: costs — affect downside. Never loosens safety gates (enforced in costs).
        cost_plan = assess_costs(
            signal_weights,
            config=new_config,
            items=items,
            step_index=step_index,
            steps_requested=steps,
            accumulated_frustration=accumulated_frustration,
            suggest_domain_jump=plan.suggest_domain_jump,
            would_stop=plan.stop,
        )
        new_config = apply_costs_to_config(new_config, cost_plan)
        cost_dicts = [e.to_dict() for e in cost_plan.effects]
        all_cost_effects.extend(cost_plan.effects)

        if cost_plan.veto_stop and plan.stop:
            plan.stop = False
            plan.stop_reason = ""
        if cost_plan.early_stop and not cost_plan.veto_stop:
            plan.stop = True
            plan.stop_reason = cost_plan.early_stop_reason

        plan_dict = plan.to_dict()

        # Attention after distraction / avoidance — may be worse than the corpus top.
        focus = pick_focus_item(items, cost_plan)
        top = items[0] if items else None
        if focus is not None:
            effective = float(focus.curiosity_score) * float(cost_plan.score_multiplier)
            if best is None or effective > best_effective:
                best = focus
                best_effective = effective

        made_progress = bool(new_ids)
        note = _step_note(plan_dict, mix["primary"], made_progress)
        if cost_dicts:
            note = f"{note} Cost: {cost_dicts[0]['disclosure']}"

        trail.record(
            TrajectoryStep(
                step=step_index,
                domain=str(config.domain),
                topic=config.topic,
                n_returned=len(items),
                top_question_id=(
                    focus.question.id if focus is not None else (top.question.id if top else None)
                ),
                top_question=(
                    focus.question.question
                    if focus is not None
                    else (top.question.question if top else "")
                ),
                top_score=(
                    float(focus.curiosity_score) * float(cost_plan.score_multiplier)
                    if focus is not None
                    else (top.curiosity_score if top else 0.0)
                ),
                new_question_ids=new_ids,
                appraisal=[s.to_dict() for s in signals],
                modulation=plan_dict["changes"],
                costs=cost_dicts,
                primary_feeling=mix["primary"],
                ambivalence=float(mix["ambivalence"]["score"]),
                made_progress=made_progress,
                note=note,
            )
        )

        if plan.stop:
            stop_reason = plan.stop_reason
            break

        config = new_config
        if plan.suggest_domain_jump and allow_domain_jump and not cost_plan.suppress_domain_jump:
            if mem_scars or mem_affinities:
                from artificial_emotions.scars import next_domain_biased

                nxt, jump_bias = next_domain_biased(
                    str(config.domain),
                    trail.domains_visited,
                    scars=mem_scars,
                    affinities=mem_affinities,
                )
                if jump_bias is not None:
                    scar_applications.append(jump_bias)
            else:
                nxt = _next_domain(str(config.domain), trail.domains_visited)
            config = config.model_copy(update={"domain": nxt})

    plan_out = decompose_ranked(best, depth=decompose_depth) if best is not None else None

    result = {
        "domain_started": domain,
        "topic": topic,
        "steps_taken": len(trail.steps),
        "steps_requested": steps,
        "stopped_because": stop_reason,
        "value_profile": profile.model_dump(mode="json"),
        "trajectory": trail.to_dict(),
        "final_feeling": last_mix["felt_simulation"] if last_mix else None,
        "final_mix": (
            {
                "primary": last_mix["primary"],
                "percents": last_mix["percents"],
                "ambivalence": last_mix["ambivalence"],
                "blend_triad_hint": last_mix["blend_triad_hint"],
            }
            if last_mix
            else None
        ),
        "best_found": (
            {
                "question_id": best.question.id,
                "question": best.question.question,
                "curiosity_score": best.curiosity_score,
                "gap_status": best.gap.status.value,
                "flags": list(best.flags or []),
            }
            if best
            else None
        ),
        "investigation_plan": plan_out,
        "weights_modulated": allow_weight_deltas,
        "honesty": "affect_driven_search",
        "claims_not": [
            "an answer to any question it surfaced",
            "an optimal or complete search of the field",
            "a closed-loop scientist — it runs no experiments",
            "biological emotion; the affect is a computational blend",
            "a loosened safety or risk gate from affect costs",
        ],
        "docs": "docs/EMOTIONS.md",
    }

    # A3: every cost disclosed — root summary + optional closing monologue.
    if all_cost_effects:
        from artificial_emotions.costs import CostPlan

        cost_summary = CostPlan(effects=list(all_cost_effects)).to_dict()
        result["costs"] = cost_summary
        mono = closing_cost_monologue(all_cost_effects)
        feeling = result.get("final_feeling")
        if mono and isinstance(feeling, dict):
            existing = str(feeling.get("inner_monologue") or "").rstrip()
            feeling = {**feeling, "inner_monologue": f"{existing}\n{mono}".strip()}
            result["final_feeling"] = feeling

    # Disclose opening mood only when it actually biased appraisal (keeps
    # fresh-memory / no-memory payloads byte-identical to today).
    if opening_mood_payload is not None:
        result["mood_carryover"] = opening_mood_payload

    # A4: disclose scar/affinity biases only when they influenced this run.
    if scar_applications:
        from artificial_emotions.scars import disclosure_payload as scar_disclosure

        disclosed = scar_disclosure(scar_applications)
        if disclosed is not None:
            result["scar_affinities"] = disclosed

    # A5: disclose temperament whenever it was active (even if only appraisal scaled).
    if active_temperament is not None:
        result["temperament"] = disclosure_payload(active_temperament, temperament_applications)
        claims = list(result.get("claims_not") or [])
        for token in (
            "biological emotion or a felt personality",
            "a loosened safety or risk gate from temperament",
        ):
            if token not in claims:
                claims.append(token)
        result["claims_not"] = claims

    # Write + annotate in A6: persistence may attach avoidance to the feeling.
    # Library default (persist_memory=False) keeps today's payload unchanged.
    # A2 also writes session-end mood into mood_carryover via record_explore_result.
    if persist_memory:
        from artificial_emotions.avoidance import (
            apply_avoidance_to_feeling,
            detect_avoidance,
        )
        from artificial_emotions.memory import persist_explore_if_enabled

        mem = persist_explore_if_enabled(result, enabled=True, path=memory_path)
        if mem is not None:
            patterns = detect_avoidance(mem.encounters, mem.selections)
            if patterns:
                result["final_feeling"] = apply_avoidance_to_feeling(
                    result.get("final_feeling"),
                    patterns,
                )
                result["avoiding"] = [p.to_dict() for p in patterns]
                claims = list(result.get("claims_not") or [])
                for token in (
                    "a motive for non-selection",
                    "that non-selection is avoidance rather than judgment",
                ):
                    if token not in claims:
                        claims.append(token)
                result["claims_not"] = claims

    return result


def domains() -> list[str]:
    """Domains the loop can jump between."""
    return [d.value for d in Domain]
