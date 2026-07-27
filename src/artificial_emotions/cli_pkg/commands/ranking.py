"""Ranking surfaces: `run`, `spark`, and `serve`."""

from __future__ import annotations

import argparse
import json

from artificial_emotions.models import (
    CuriosityConfig,
    resolve_value_profile,
)
from artificial_emotions.pipeline import CuriosityEngine
from artificial_emotions.provoke import provoke


def _run_engine(args: argparse.Namespace) -> int:
    profile = resolve_value_profile(profile_name=args.profile)
    config = CuriosityConfig(
        domain=args.domain,
        topic=args.topic,
        n_candidates=args.candidates,
        n_return=args.n,
        use_llm=args.llm,
        use_literature=not args.no_literature,
        literature_backend=args.literature_backend,
        literature_cache_dir=args.lit_cache,
        literature_workers=max(1, min(16, int(getattr(args, "lit_workers", 4) or 4))),
        llm_model=args.model,
        judge_model=args.judge_model,
        judge_ensemble_n=args.judge_ensemble,
        llm_base_url=args.base_url,
        value_profile=profile,
        diversity_backend=args.diversity,
        preference_log_path=args.preference_log,
        preference_rerank_path=getattr(args, "preference_rerank", None),
        preference_learn_path=getattr(args, "preference_learn", None),
    )
    results = CuriosityEngine(config).run()

    if args.json:
        print(json.dumps([r.model_dump(mode="json") for r in results], indent=2))
        return 0

    print(f"\nArtificial Emotions - domain={args.domain}")
    print(f"ValueProfile: {profile.name}")
    print(f"Literature backend: {args.literature_backend if not args.no_literature else 'none'}")
    print("What should we investigate next?\n")
    for r in results:
        band = ""
        if r.score_low is not None and r.score_high is not None:
            band = f"  [{r.score_low:.2f}–{r.score_high:.2f}]"
        print(f"#{r.rank}  score={r.curiosity_score:.3f}{band}  conf={r.confidence:.2f}")
        print(f"    {r.question.question}")
        print(f"    gap={r.gap.status.value}  flags={','.join(r.flags) or 'none'}")
        print()
    return 0


def _serve(args: argparse.Namespace) -> int:
    import uvicorn

    print(
        f"Artificial Emotions API → http://{args.host}:{args.port}\n"
        f"  Instant spark: GET /v1/curiosity/provoke?domain=ai&n=5\n"
        f"  Emotions:      GET /v1/emotions/catalog  POST /v1/emotions/mix\n"
        f"                 GET /v1/emotions/cues  POST /v1/emotions/annotate\n"
        f"  Agent guide:   GET /v1/agent\n"
        f"  Agent tools:   GET /v1/agent/tools\n"
        f"  Profiles:      GET /v1/profiles\n"
        f"  OpenAPI:       http://{args.host}:{args.port}/docs\n"
        f"  MCP (stdio):   curiosity-mcp\n"
    )
    uvicorn.run(
        "artificial_emotions.api:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )
    return 0


def _spark(args: argparse.Namespace) -> int:
    pack = provoke(
        domain=args.domain,
        topic=args.topic,
        n=args.n,
        fast=not args.literature,
        use_llm=args.llm,
        use_literature=args.literature,
        profile_name=args.profile,
        llm_model=args.model,
        judge_model=args.judge_model,
        llm_base_url=args.base_url,
        diversity_backend=args.diversity,
    )
    if args.json:
        print(json.dumps(pack, indent=2))
        return 0
    print(pack["inject"])
    return 0


def _explore(args: argparse.Namespace) -> int:
    """Run the curiosity loop and print the trajectory."""
    from artificial_emotions.explore import explore

    payload = explore(
        domain=args.domain,
        topic=args.topic,
        steps=args.steps,
        n_return=args.n,
        profile_name=args.profile,
        use_literature=args.literature,
        allow_weight_deltas=args.affect_weights,
        allow_domain_jump=not args.no_jump,
    )
    if args.json:
        print(json.dumps(payload, indent=2))
        return 0

    print(f"\nExploring {payload['domain_started']} — {payload['steps_taken']} steps\n")
    for step in payload["trajectory"]["steps"]:
        feels = ", ".join(f"{a['emotion']} {a['weight']:.2f}" for a in step["appraisal"][:3])
        print(f"  step {step['step']}  [{step['domain']}]  {len(step['new_question_ids'])} new")
        print(f"      feels: {feels}")
        for change in step["modulation"]:
            print(f"      · {change['knob']}: {change['before']} → {change['after']}")
            print(f"        because {change['driver']} — {change['rationale']}")
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

    plan = payload.get("investigation_plan")
    if plan:
        step = plan["discriminating_step"]
        print(f"\nDo this first ({step['kind']}, cost {step['expected_cost_band']}):")
        print(f"  {step['observation']}")
    print(f"\n{payload['claims_not'][0].capitalize()} is not claimed here.")
    return 0
