"""Offline eval harnesses: spotcheck, elicit, gap-status, report, cooccur."""

from __future__ import annotations

import argparse
import json

from artificial_curiosity.resources import find_data_file


def _eval(args: argparse.Namespace) -> int:
    cmd = getattr(args, "eval_cmd", None) or "spotcheck"

    if cmd == "elicit":
        from artificial_curiosity.elicit_eval import run_elicit_ab

        payload = run_elicit_ab(
            protocol_path=args.protocol,
            responses_path=args.responses,
            domain=args.domain,
            topic=args.topic or "",
            n=int(args.n or 3),
            profile_name=args.profile,
        )
        if args.json:
            print(json.dumps(payload, indent=2))
            return 0
        print(
            f"Elicit A/B  protocol={payload.get('protocol')}  v={payload.get('protocol_version')}"
        )
        print(f"  scored={payload.get('n_responses_scored')}  deltas={payload.get('deltas')}")
        for row in payload.get("conditions") or []:
            cid = row.get("condition_id")
            flags = []
            if row.get("inject_has_incongruity"):
                flags.append("incongruity")
            if row.get("inject_has_cues"):
                flags.append("cues")
            if row.get("inject_has_mix"):
                flags.append("mix")
            mean = (row.get("response_scores") or {}).get("mean")
            mean_s = f" mean={mean}" if mean is not None else ""
            print(f"  [{cid}] inject=[{','.join(flags) or 'plain'}]{mean_s}")
        print(f"\n{payload.get('honesty')}")
        return 0

    if cmd == "gap-status":
        from artificial_curiosity.evals import load_gap_status_fixtures, run_gap_status_eval

        cases = (
            load_gap_status_fixtures(args.fixtures) if args.fixtures else load_gap_status_fixtures()
        )
        report = run_gap_status_eval(cases)
        payload = report.to_dict()
        if args.json:
            print(json.dumps(payload, indent=2))
            return 0
        print("Gap-status hand-label fixture eval")
        print(
            f"  cases={report.n_cases}  status_accuracy={report.status_accuracy}  "
            f"false_answered_rate={report.false_answered_rate}"
        )
        print(
            f"  related_but_unanswered_n={report.related_but_unanswered_n}  "
            f"recall={report.related_but_unanswered_recall}"
        )
        print(f"  methodology: {report.methodology}")
        for r in report.results:
            mark = "OK" if r.get("match") else "MISS"
            print(
                f"  [{mark}] {r['case_id']}: gold={r['gold_status']} pred={r['predicted_status']}"
            )
        return 0

    if cmd == "report":
        from artificial_curiosity.eval_report import build_eval_report

        sample = find_data_file("examples/elicit_ab_sample_responses.json")
        payload = build_eval_report(
            fixtures=args.fixtures,
            elicit_responses=str(sample) if sample.is_file() else None,
        )
        if args.json:
            print(json.dumps(payload, indent=2))
            return 0
        secs = payload.get("sections") or {}
        gf = secs.get("gap_f1") or {}
        print("Composite eval report (multi-metric)")
        print(
            f"  gap_f1={gf.get('f1')}  precision={gf.get('precision')}  recall={gf.get('recall')}"
        )
        gs = secs.get("gap_status_handlabel") or {}
        print(
            f"  gap_status accuracy={gs.get('status_accuracy')}  "
            f"rbu_recall={gs.get('related_but_unanswered_recall')}"
        )
        el = secs.get("elicit_rubric") or {}
        print(f"  elicit means={el.get('condition_means')}  deltas={el.get('deltas')}")
        print(f"\n{payload.get('honesty')}")
        return 0

    if cmd == "cooccur":
        from artificial_curiosity.cooccur_study import run_cooccur_correlation

        path = args.fixtures or find_data_file("evals/fixtures/cooccur_neglectedness_smoke_v1.json")
        payload = run_cooccur_correlation(path)
        if args.json:
            print(json.dumps(payload, indent=2))
            return 0
        print(f"Cooccur study  n={payload.get('n')}  spearman_rho={payload.get('spearman_rho')}")
        print(f"\n{payload.get('honesty')}")
        return 0

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
        print(f"  cases={report.n_cases}  match={report.n_match}  match_rate={report.match_rate}")
        print(
            f"  already_answered_gold={report.n_already_answered_gold}  "
            f"missed_answered={report.n_missed_answered}"
        )
        print(f"  methodology: {report.methodology}")
        for r in report.results:
            mark = "OK" if r.match else "MISS"
            print(f"  [{mark}] {r.case_id}: gold={r.gold_status} pred={r.predicted_status}")
    return 0
