"""Form-only critique and worksheet fills — none of these re-rank."""

from __future__ import annotations

import argparse
import json


def _critique_brief(args: argparse.Namespace) -> int:
    from artificial_curiosity.critique import critique_brief

    payload = critique_brief(
        question=args.question or "",
        operationalization=args.operationalization or "",
        brief=args.brief or "",
        why_it_matters=args.why_it_matters or "",
    )
    if args.json:
        print(json.dumps(payload, indent=2))
        return 0
    print(f"Critique brief  issues={payload['n_issues']}  changes_ranks=False")
    for issue in payload.get("issues") or []:
        print(f"  [{issue['severity']}] {issue['code']}: {issue['detail']}")
    print(f"\n{payload.get('honesty')}")
    return 0


def _voi_worksheet(args: argparse.Namespace) -> int:
    from artificial_curiosity.voi import fill_voi_worksheet

    payload = fill_voi_worksheet(
        question_id=args.question_id,
        question=args.question or "",
        operationalization=args.operationalization or "",
        profile_name=args.profile,
        domain=args.domain or "",
    )
    if args.json:
        print(json.dumps(payload, indent=2))
        return 0
    print("VOI worksheet (template fill — not EVSI)")
    print(f"  decision_problem={payload.get('decision_problem')[:120]}")
    print(f"  link={payload.get('link_to_ranked_question')}")
    print(f"\n{payload.get('honesty')}")
    return 0


def _surprise_worksheet(args: argparse.Namespace) -> int:
    from artificial_curiosity.bayesian import fill_surprise_worksheet

    payload = fill_surprise_worksheet(
        question_id=args.question_id,
        profile_name=args.profile_name,
        predicted_surprise=args.predicted_surprise,
        pilot_result=args.pilot_result or "",
        belief_shift_1_to_5=args.belief_shift,
        crude_update_note=args.crude_update_note or "",
    )
    if args.json:
        print(json.dumps(payload, indent=2))
        return 0
    fields = payload.get("fields") or {}
    print("Surprise worksheet (belief-shift log — not EVSI / not axis rename)")
    print(f"  question_id={fields.get('question_id')}")
    print(f"  predicted_surprise={fields.get('predicted_surprise')}")
    print(f"  belief_shift={fields.get('belief_shift_1_to_5')}")
    print(f"\n{payload.get('honesty')}")
    return 0
