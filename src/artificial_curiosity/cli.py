"""CLI for Artificial Curiosity."""

from __future__ import annotations

import argparse
import json
import sys

from artificial_curiosity.models import CuriosityConfig, Domain, ValueProfile
from artificial_curiosity.pipeline import CuriosityEngine


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="curiosity",
        description="Generate and rank valuable unanswered questions.",
    )
    p.add_argument("--domain", default="ai", choices=[d.value for d in Domain])
    p.add_argument("--topic", default="")
    p.add_argument("--n", type=int, default=8, help="Number of questions to return")
    p.add_argument("--candidates", type=int, default=16)
    p.add_argument("--llm", action="store_true", help="Use OpenAI-compatible LLM")
    p.add_argument("--no-literature", action="store_true")
    p.add_argument("--json", action="store_true", help="Emit JSON")
    p.add_argument("--model", default="gpt-4o-mini")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = CuriosityConfig(
        domain=args.domain,
        topic=args.topic,
        n_candidates=args.candidates,
        n_return=args.n,
        use_llm=args.llm,
        use_literature=not args.no_literature,
        llm_model=args.model,
        value_profile=ValueProfile(),
    )
    results = CuriosityEngine(config).run()

    if args.json:
        print(json.dumps([r.model_dump(mode="json") for r in results], indent=2))
        return 0

    print(f"\nArtificial Curiosity - domain={args.domain}")
    print("What should we investigate next?\n")
    for r in results:
        print(f"#{r.rank}  score={r.curiosity_score:.3f}  conf={r.confidence:.2f}")
        print(f"    {r.question.question}")
        print(f"    gap={r.gap.status.value}  flags={','.join(r.flags) or 'none'}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
