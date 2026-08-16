"""CLI: `emotions explore` — the curiosity loop.

Implementation lives here so it is not mixed with `run` / `spark` / `serve`.
``ranking.py`` re-exports ``_explore`` so dispatch wiring does not churn.
Parser flags for this command live in ``cli_pkg/parser/alive.py``.
"""

from __future__ import annotations

import argparse
import json

__all__ = ["_explore"]


def _explore(args: argparse.Namespace) -> int:
    """Run the curiosity loop and print the trajectory."""
    from artificial_emotions.explore import explore
    from artificial_emotions.memory import memory_disabled

    # CLI-only persistence by default; MCP/HTTP never enable it.
    persist = not getattr(args, "no_memory", False) and not memory_disabled()
    payload = explore(
        domain=args.domain,
        topic=args.topic,
        steps=args.steps,
        n_return=args.n,
        profile_name=args.profile,
        use_literature=args.literature,
        allow_weight_deltas=args.affect_weights,
        somatic_modulate=bool(getattr(args, "somatic_modulate", False)),
        allow_domain_jump=not args.no_jump,
        persist_memory=persist,
        preference_log_path=getattr(args, "preference_log", None),
    )
    if args.json:
        print(json.dumps(payload, indent=2))
        return 0

    print(f"\nExploring {payload['domain_started']} — {payload['steps_taken']} steps\n")
    for step in payload["trajectory"]["steps"]:
        drivers = {c["driver"] for c in step["modulation"]}
        acted = [a for a in step["appraisal"] if a["emotion"] in drivers]
        observed = [a for a in step["appraisal"] if a["emotion"] not in drivers]

        print(f"  step {step['step']}  [{step['domain']}]  {len(step['new_question_ids'])} new")
        if acted:
            print(
                "      acted:    " + ", ".join(f"{a['emotion']} {a['weight']:.2f}" for a in acted)
            )
        if observed:
            print(
                "      observed: "
                + ", ".join(f"{a['emotion']} {a['weight']:.2f}" for a in observed[:6])
            )
        for change in step["modulation"]:
            print(f"      · {change['knob']}: {change['before']} → {change['after']}")
            print(f"        because {change['driver']} — {change['rationale']}")
        for cost in step.get("costs") or []:
            print(f"      ✗ cost {cost['kind']}: {cost['disclosure']}")
        print(f"      → {step['note']}\n")

    print(f"Stopped: {payload['stopped_because']}")
    print(f"Ground covered: {', '.join(payload['trajectory']['domains_visited'])}")

    best = payload.get("best_found")
    if best:
        print(f"\nBest found  [score {best['curiosity_score']:.3f}]")
        print(f"  {best['question']}")

    feeling = payload.get("final_feeling")
    if feeling:
        print(f"\n{feeling['inner_monologue']}")
    avoiding = payload.get("avoiding") or (feeling or {}).get("avoiding")
    if avoiding:
        print(
            "\n(Pattern note: non-selection is either judgment or avoidance — "
            "cannot tell which. Annotation only; does not feel.)"
        )

    plan = payload.get("investigation_plan")
    if plan:
        step = plan["discriminating_step"]
        print(f"\nDo this first ({step['kind']}, cost {step['expected_cost_band']}):")
        print(f"  {step['observation']}")
    print(f"\n{payload['claims_not'][0].capitalize()} is not claimed here.")
    return 0
