"""CLI: `emotions loop --outcomes PATH` — dry-run, not experiment execution."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _loop(args: argparse.Namespace) -> int:
    from artificial_emotions.outcome_loop import dry_run_outcome_loop

    path = getattr(args, "outcomes", None)
    if not path:
        print(
            "Usage: emotions loop --outcomes PATH [--json] [--profile NAME]\n"
            "  Dry-run: read outcome JSONL → suggested re-rank / next explore.\n"
            "  Does not run experiments. Not a lab closed-loop.",
            file=sys.stderr,
        )
        return 2

    payload = dry_run_outcome_loop(
        Path(path),
        profile_name=getattr(args, "profile", None) or None,
    )
    if args.json:
        print(json.dumps(payload, indent=2))
        return 0 if payload.get("ok") else 1

    print("Outcome loop (dry-run — not experiment execution)")
    print(
        f"  outcomes={payload.get('outcomes_path')}  "
        f"n_outcome={payload.get('n_outcome')}  "
        f"experiments_run={payload.get('experiments_run')}"
    )
    print(f"  ok={payload.get('ok')}  reason={payload.get('reason')}")
    rerank = payload.get("suggested_rerank") or []
    if rerank:
        print("  suggested re-rank:")
        for row in rerank:
            delta = float(row.get("delta") or 0.0)
            print(
                f"    {row.get('suggested_rank')}. {row.get('question_id')}  "
                f"delta={delta:+.2f}  {row.get('reason')}"
            )
    else:
        print("  suggested re-rank: (none)")
    nxt = payload.get("next_explore")
    if nxt:
        qid = nxt.get("question_id") or "—"
        print(f"  next explore: {nxt.get('action')} {qid} (executed={nxt.get('executed')})")
        cmd = nxt.get("suggested_command")
        if cmd:
            print(f"    suggested (not run): {cmd}")
    else:
        print("  next explore: (none)")
    print(f"\n{payload.get('honesty')}")
    return 0 if payload.get("ok") else 1
