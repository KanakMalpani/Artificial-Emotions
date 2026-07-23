"""CLI for Artificial Curiosity."""

from __future__ import annotations

import argparse
import json
import sys

from artificial_curiosity.models import (
    CuriosityConfig,
    Domain,
    list_profile_names,
    resolve_value_profile,
)
from artificial_curiosity.pipeline import CuriosityEngine
from artificial_curiosity.provoke import provoke


def _add_run_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--domain", default="ai", choices=[d.value for d in Domain])
    p.add_argument("--topic", default="")
    p.add_argument("--n", type=int, default=8, help="Number of questions to return")
    p.add_argument("--candidates", type=int, default=16)
    p.add_argument("--llm", action="store_true", help="Use any OpenAI-compatible LLM")
    p.add_argument("--no-literature", action="store_true")
    p.add_argument(
        "--literature-backend",
        default="openalex",
        choices=["openalex", "semantic_scholar", "both"],
        help="Literature adapter (default openalex; both merges OpenAlex+S2)",
    )
    p.add_argument("--json", action="store_true", help="Emit JSON")
    p.add_argument("--model", default="gpt-4o-mini", help="Generator model")
    p.add_argument(
        "--judge-model",
        default=None,
        help="Separate judge/gap-reader model (default: same as --model / LLM_JUDGE_MODEL)",
    )
    p.add_argument(
        "--judge-ensemble",
        type=int,
        default=1,
        help="Multi-judge ensemble size (W15); >1 flags disagreement",
    )
    p.add_argument("--base-url", default=None, help="OpenAI-compatible API base URL")
    p.add_argument(
        "--profile",
        default="humanity_default",
        help=f"ValueProfile preset name ({', '.join(list_profile_names())})",
    )
    p.add_argument(
        "--diversity",
        default="jaccard",
        choices=["jaccard", "embedding"],
        help="Near-dup backend (embedding needs pip install '.[embeddings]')",
    )
    p.add_argument(
        "--preference-log",
        default=None,
        help="Opt-in JSONL path for preference / ranking snapshots (W13)",
    )
    p.add_argument(
        "--lit-cache",
        default=None,
        help="Optional directory for literature response cache",
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="curiosity",
        description="Generate and rank valuable unanswered questions.",
    )
    sub = p.add_subparsers(dest="command")

    run_p = sub.add_parser("run", help="Rank unanswered questions (default)")
    _add_run_args(run_p)

    serve_p = sub.add_parser("serve", help="Start the HTTP API for any client/agent")
    serve_p.add_argument("--host", default="127.0.0.1")
    serve_p.add_argument("--port", type=int, default=8000)
    serve_p.add_argument("--reload", action="store_true")

    spark_p = sub.add_parser(
        "spark", help="Instant curiosity pack (inject into any model)"
    )
    spark_p.add_argument("--domain", default="ai", choices=[d.value for d in Domain])
    spark_p.add_argument("--topic", default="")
    spark_p.add_argument("--n", type=int, default=5)
    spark_p.add_argument(
        "--literature",
        action="store_true",
        help="Ground gaps in literature (slower)",
    )
    spark_p.add_argument("--llm", action="store_true")
    spark_p.add_argument("--json", action="store_true")
    spark_p.add_argument("--model", default=None)
    spark_p.add_argument("--judge-model", default=None)
    spark_p.add_argument("--base-url", default=None)
    spark_p.add_argument(
        "--profile",
        default="humanity_default",
        help=f"ValueProfile preset ({', '.join(list_profile_names())})",
    )
    spark_p.add_argument(
        "--diversity",
        default="jaccard",
        choices=["jaccard", "embedding"],
    )

    profiles_p = sub.add_parser("profiles", help="List ValueProfile presets")
    profiles_p.add_argument("--json", action="store_true")

    eval_p = sub.add_parser(
        "eval",
        help="Offline expert-eval / spot-check harness (W10; no vanity accuracy %)",
    )
    eval_p.add_argument(
        "--fixtures",
        default=None,
        help="Path to fixture JSON or directory (default: evals/fixtures)",
    )
    eval_p.add_argument("--json", action="store_true")
    return p


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
        llm_model=args.model,
        judge_model=args.judge_model,
        judge_ensemble_n=args.judge_ensemble,
        llm_base_url=args.base_url,
        value_profile=profile,
        diversity_backend=args.diversity,
        preference_log_path=args.preference_log,
    )
    results = CuriosityEngine(config).run()

    if args.json:
        print(json.dumps([r.model_dump(mode="json") for r in results], indent=2))
        return 0

    print(f"\nArtificial Curiosity - domain={args.domain}")
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
        f"Artificial Curiosity API → http://{args.host}:{args.port}\n"
        f"  Instant spark: GET /v1/curiosity/provoke?domain=ai&n=5\n"
        f"  Agent guide:   GET /v1/agent\n"
        f"  Agent tools:   GET /v1/agent/tools\n"
        f"  Profiles:      GET /v1/profiles\n"
        f"  OpenAPI:       http://{args.host}:{args.port}/docs\n"
        f"  MCP (stdio):   curiosity-mcp\n"
    )
    uvicorn.run(
        "artificial_curiosity.api:app",
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


def _profiles(args: argparse.Namespace) -> int:
    from artificial_curiosity.models import VALUE_PROFILE_PRESETS

    rows = [
        {
            "name": name,
            "description": p.description,
            "time_horizon_years": p.time_horizon_years,
            "max_risk": p.max_risk,
            "min_answerability": p.min_answerability,
        }
        for name, p in sorted(VALUE_PROFILE_PRESETS.items())
    ]
    if args.json:
        print(json.dumps(rows, indent=2))
    else:
        for r in rows:
            print(f"{r['name']}: {r['description']}")
    return 0


def _eval(args: argparse.Namespace) -> int:
    from artificial_curiosity.evals import (
        already_answered_fail_rate,
        load_fixtures,
        run_spotcheck,
    )

    cases = load_fixtures(args.fixtures) if args.fixtures else load_fixtures()
    report = run_spotcheck(cases)
    payload = report.to_dict()
    payload["already_answered_fail_rate"] = already_answered_fail_rate(report)
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print("Expert-eval spot-check (offline fixtures)")
        print(f"  cases={report.n_cases}  match={report.n_match}  "
              f"match_rate={report.match_rate}")
        print(f"  already_answered_gold={report.n_already_answered_gold}  "
              f"missed_answered={report.n_missed_answered}")
        print(f"  methodology: {report.methodology}")
        for r in report.results:
            mark = "OK" if r.match else "MISS"
            print(f"  [{mark}] {r.case_id}: gold={r.gold_status} pred={r.predicted_status}")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()

    # Bare flags → default `run` so `curiosity --domain ai` still works.
    if not argv or argv[0] not in (
        "run",
        "serve",
        "spark",
        "profiles",
        "eval",
        "-h",
        "--help",
    ):
        argv = ["run", *argv]

    args = parser.parse_args(argv)

    if args.command == "serve":
        return _serve(args)
    if args.command == "spark":
        return _spark(args)
    if args.command == "profiles":
        return _profiles(args)
    if args.command == "eval":
        return _eval(args)
    return _run_engine(args)


if __name__ == "__main__":
    sys.exit(main())
