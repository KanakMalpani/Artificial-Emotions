"""Form-only critique and worksheet fills — none of these re-rank."""

from __future__ import annotations

import argparse
import json


def _critique_brief(args: argparse.Namespace) -> int:
    from artificial_emotions.critique import critique_brief

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
    from artificial_emotions.voi import fill_voi_worksheet

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
    print(f"  honesty={payload.get('honesty')}  evsi={payload.get('evsi')}")
    print(f"\n{payload.get('honesty_note') or payload.get('honesty')}")
    return 0


def _surprise_worksheet(args: argparse.Namespace) -> int:
    from artificial_emotions.bayesian import fill_surprise_worksheet

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


def _decompose(args: argparse.Namespace) -> int:
    """Open one unknown into its next layer of questions."""
    from artificial_emotions.decompose import decompose_question
    from artificial_emotions.models import UnansweredQuestion

    q = UnansweredQuestion(
        id="cli-decompose",
        question=args.question,
        domain=args.domain,
        operationalization=args.operationalization,
        why_it_matters="Supplied for decomposition.",
    )
    payload = decompose_question(
        q,
        depth=args.depth,
        answerability=args.answerability,
        tractability=args.tractability,
        risk=args.risk,
    )
    if args.json:
        print(json.dumps(payload, indent=2))
        return 0

    print(f"\nUnknown: {payload['question']}")
    print(f"Depth {payload['depth']} — {payload['sub_question_count']} sub-questions\n")
    for sub in payload["sub_questions"]:
        print(f"[{sub['kind']}]")
        print(f"    {sub['question']}")
        print(f"    why: {sub['why_this_narrows_it']}")
        for child in sub["children"]:
            print(f"      └ [{child['kind']}] {child['question']}")
        print()

    step = payload["discriminating_step"]
    print(f"Do this first ({step['kind']}, cost {step['expected_cost_band']}):")
    print(f"    {step['observation']}")
    print(f"    {step['why_this_first']}\n")

    print("Falsifiers:")
    for f in payload["falsifiers"]:
        print(f"  - {f['criterion']}  →  refuted if {f['refuted_if']}")
    print("\nStop rules:")
    for rule in payload["stop_rules"]:
        print(f"  - {rule}")
    print(f"\n{payload['open_after_this']}")
    return 0
