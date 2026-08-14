"""Preference JSONL helpers: hints, summarize, suggest-pair."""

from __future__ import annotations

import argparse
import json
import sys


def _preferences(args: argparse.Namespace) -> int:
    from artificial_emotions.preferences import (
        preview_or_apply_weight_hints,
        summarize_preferences,
    )

    cmd = getattr(args, "preferences_cmd", None)
    if cmd == "hints":
        apply = bool(getattr(args, "apply", False))
        hints = preview_or_apply_weight_hints(args.path, profile_name=args.profile, apply=apply)
        if args.json:
            print(json.dumps(hints, indent=2))
            return 0
        mode = hints.get("mode") or ("apply" if apply else "preview")
        print(f"Preference weight hints for profile={args.profile}  mode={mode}")
        print(f"  ok={hints.get('ok')}  reason={hints.get('reason')}")
        print(
            f"  applied={hints.get('applied')}  "
            f"n_prefer={hints.get('n_prefer')}  n_reject={hints.get('n_reject')}"
        )
        deltas = hints.get("deltas") or {}
        if deltas:
            print("  deltas:")
            for k, v in deltas.items():
                print(f"    {k}: {v:+.4f}")
        else:
            print("  deltas: (none)")
        if hints.get("clamped_weights"):
            print(f"  clamped: {', '.join(hints['clamped_weights'])}")
        if apply:
            applied = hints.get("applied_profile") or {}
            print(f"  applied_profile={applied.get('name') or '(unchanged copy)'}")
        else:
            print("  (preview only — pass --apply to return an applied profile copy)")
        print(f"\n{hints.get('honesty')}")
        return 0
    if cmd == "summarize":
        summary = summarize_preferences(
            args.path, profile_name=args.profile, top_k=int(args.top or 10)
        )
        if args.json:
            print(json.dumps(summary, indent=2))
            return 0
        print(f"Preference summary  n={summary['n_events']}  profile={args.profile}")
        print(f"  counts: {summary.get('counts_by_type')}")
        print(f"  pairwise: {summary.get('n_pairwise')}")
        print("  top ids:")
        for row in summary.get("top_question_ids") or []:
            wr = row.get("win_rate")
            wr_s = f"{wr:.2f}" if wr is not None else "n/a"
            print(
                f"    {row['question_id']}: score={row['score']} "
                f"wins={row['wins']} losses={row['losses']} win_rate={wr_s}"
            )
        wh = summary.get("weight_hints") or {}
        print(f"  weight_hints ok={wh.get('ok')} deltas={wh.get('deltas')}")
        print(f"\n{summary.get('honesty')}")
        return 0
    if cmd == "suggest-pair":
        from artificial_emotions.preferences import suggest_next_pair

        cands = [c.strip() for c in str(args.candidates).split(",") if c.strip()]
        events = args.path if args.path else []
        payload = suggest_next_pair(cands, events, profile_name=args.profile)
        if args.json:
            print(json.dumps(payload, indent=2))
            return 0
        print(f"Suggest next pair  ok={payload.get('ok')}")
        pair = payload.get("pair") or {}
        if pair:
            print(f"  A={pair.get('a')}  B={pair.get('b')}")
            print(f"  prior_comparisons={pair.get('prior_comparisons')}")
        print(f"\n{payload.get('honesty')}")
        return 0
    print(
        "Usage:\n"
        "  curiosity preferences hints --path labeled.jsonl [--profile NAME] [--apply]\n"
        "  curiosity preferences summarize --path labeled.jsonl [--profile NAME]\n"
        "  curiosity preferences suggest-pair --candidates id1,id2,id3 [--path prefs.jsonl]\n"
        "Preference tools are profile-scoped decision aids — not calibrated learning.\n"
        "hints defaults to preview; --apply returns a profile copy (never overwrites a preset).",
        file=sys.stderr,
    )
    return 2
