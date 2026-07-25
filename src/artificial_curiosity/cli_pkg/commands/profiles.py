"""ValueProfile listing and side-by-side comparison."""

from __future__ import annotations

import argparse
import json


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


def _compare_profiles(args: argparse.Namespace) -> int:
    from artificial_curiosity.compare import compare_profiles

    payload = compare_profiles(
        domain=args.domain,
        topic=args.topic,
        profile_a=args.profile_a,
        profile_b=args.profile_b,
        n=args.n,
    )
    if args.json:
        print(json.dumps(payload, indent=2))
        return 0
    print(f"Compare profiles  domain={args.domain}  A={args.profile_a}  B={args.profile_b}\n")
    print(f"Strictest max_risk (veto tip): {payload['veto_tip']['strictest_max_risk']}")
    print("\nRank A:")
    for r in payload["ranks_a"]:
        print(f"  #{r['rank']}  {r['curiosity_score']:.3f}  {r['question'][:90]}")
    print("\nRank B:")
    for r in payload["ranks_b"]:
        print(f"  #{r['rank']}  {r['curiosity_score']:.3f}  {r['question'][:90]}")
    print("\nLargest rank deltas (A−B):")
    for d in (payload.get("rank_deltas") or [])[:5]:
        print(f"  {d['question_id']}: A#{d['rank_a']} B#{d['rank_b']} Δ={d['delta_a_minus_b']}")
    print(f"\n{payload.get('honesty')}")
    return 0
