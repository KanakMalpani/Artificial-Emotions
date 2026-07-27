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
from artificial_emotions.decompose import decompose_ranked
from artificial_emotions.emotions import mix_emotions
from artificial_emotions.models import CuriosityConfig, Domain, RankedQuestion
from artificial_emotions.modulate import modulate_config
from artificial_emotions.pipeline import CuriosityEngine
from artificial_emotions.trajectory import Trajectory, TrajectoryStep, question_terms

__all__ = ["MAX_STEPS", "explore"]

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
) -> dict[str, Any]:
    """Run the curiosity loop and return the trajectory.

    Args:
        domain: where to start.
        steps: how many passes to take (clamped to ``MAX_STEPS``).
        allow_weight_deltas: let affect nudge ValueProfile weights (bounded, logged).
        allow_domain_jump: let boredom change ground.
        decompose_depth: depth of the closing investigation plan.

    Returns:
        The full trajectory: every step, what it felt and why, what that
        changed, and a decomposed plan for the strongest thing it found.
    """
    steps = max(1, min(int(steps), MAX_STEPS))
    from artificial_emotions.models import resolve_value_profile

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
    last_mix: dict[str, Any] | None = None
    stop_reason = "Completed the requested number of steps."

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
        )
        mix = mix_emotions(signals_to_weights(signals))
        last_mix = mix

        new_config, plan = modulate_config(
            config,
            {c["id"]: c["weight"] for c in mix["components"]},
            allow_weight_deltas=allow_weight_deltas,
            exhausted=trail.is_exhausted(),
        )
        plan_dict = plan.to_dict()

        top = items[0] if items else None
        if top is not None and (best is None or top.curiosity_score > best.curiosity_score):
            best = top

        made_progress = bool(new_ids)
        trail.record(
            TrajectoryStep(
                step=step_index,
                domain=str(config.domain),
                topic=config.topic,
                n_returned=len(items),
                top_question_id=top.question.id if top else None,
                top_question=top.question.question if top else "",
                top_score=top.curiosity_score if top else 0.0,
                new_question_ids=new_ids,
                appraisal=[s.to_dict() for s in signals],
                modulation=plan_dict["changes"],
                primary_feeling=mix["primary"],
                ambivalence=float(mix["ambivalence"]["score"]),
                made_progress=made_progress,
                note=_step_note(plan_dict, mix["primary"], made_progress),
            )
        )

        if plan.stop:
            stop_reason = plan.stop_reason
            break

        config = new_config
        if plan.suggest_domain_jump and allow_domain_jump:
            config = config.model_copy(
                update={"domain": _next_domain(str(config.domain), trail.domains_visited)}
            )

    plan_out = decompose_ranked(best, depth=decompose_depth) if best is not None else None

    return {
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
        ],
        "docs": "docs/EMOTIONS.md",
    }


def domains() -> list[str]:
    """Domains the loop can jump between."""
    return [d.value for d in Domain]
