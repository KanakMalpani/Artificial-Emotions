"""CLI for Artificial Curiosity."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

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
        "--preference-rerank",
        default=None,
        help=(
            "Opt-in labeled prefer/reject JSONL for thin profile-scoped re-rank "
            "(not weight learning; CLI only)"
        ),
    )
    p.add_argument(
        "--preference-learn",
        default=None,
        help=(
            "Opt-in labeled JSONL with score_axes for tiny ValueProfile weight hints "
            "(profile-scoped; not calibrated; CLI only)"
        ),
    )
    p.add_argument(
        "--lit-cache",
        default=None,
        help="Optional directory for literature response cache",
    )
    p.add_argument(
        "--lit-workers",
        type=int,
        default=4,
        help="Parallel literature fetches (1=serial; default 4)",
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

    spark_p = sub.add_parser("spark", help="Instant curiosity pack (inject into any model)")
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

    pref_p = sub.add_parser(
        "preferences",
        help="Preference JSONL helpers (hints — not calibrated learning)",
    )
    pref_sub = pref_p.add_subparsers(dest="preferences_cmd")
    hints_p = pref_sub.add_parser(
        "hints",
        help="Suggest tiny ValueProfile weight deltas from labeled prefer/reject JSONL",
    )
    hints_p.add_argument("--path", required=True, help="Labeled preference JSONL path")
    hints_p.add_argument(
        "--profile",
        default="humanity_default",
        help=f"ValueProfile preset ({', '.join(list_profile_names())})",
    )
    hints_p.add_argument("--json", action="store_true")

    sum_p = pref_sub.add_parser(
        "summarize",
        help="Summarize preference JSONL (counts, pairwise wins, weight hints)",
    )
    sum_p.add_argument("--path", required=True, help="Preference JSONL path")
    sum_p.add_argument(
        "--profile",
        default=None,
        help="Optional profile filter (default: all events in file)",
    )
    sum_p.add_argument("--top", type=int, default=10, help="Top question ids to show")
    sum_p.add_argument("--json", action="store_true")

    compare_p = sub.add_parser(
        "compare-profiles",
        help="Side-by-side offline ranks under two ValueProfiles (no silent merge)",
    )
    compare_p.add_argument("--domain", default="ai", choices=[d.value for d in Domain])
    compare_p.add_argument("--topic", default="")
    compare_p.add_argument("--a", default="humanity_default", dest="profile_a")
    compare_p.add_argument("--b", default="alignment_lab", dest="profile_b")
    compare_p.add_argument("--n", type=int, default=8)
    compare_p.add_argument("--json", action="store_true")

    critique_p = sub.add_parser(
        "critique-brief",
        help="Form-only critique of a brief/ops (does not re-rank)",
    )
    critique_p.add_argument("--question", default="")
    critique_p.add_argument("--ops", default="", dest="operationalization")
    critique_p.add_argument("--brief", default="")
    critique_p.add_argument("--why", default="", dest="why_it_matters")
    critique_p.add_argument("--json", action="store_true")

    voi_p = sub.add_parser(
        "voi-worksheet",
        help="Fill VOI worksheet metadata (not computed EVSI)",
    )
    voi_p.add_argument("--question-id", default=None)
    voi_p.add_argument("--question", default="")
    voi_p.add_argument("--ops", default="", dest="operationalization")
    voi_p.add_argument("--profile", default=None)
    voi_p.add_argument("--domain", default="")
    voi_p.add_argument("--json", action="store_true")

    eval_p = sub.add_parser(
        "eval",
        help="Offline eval harnesses (spotcheck / elicit A/B / gap-status; no vanity %%)",
    )
    eval_p.add_argument(
        "eval_cmd",
        nargs="?",
        default="spotcheck",
        choices=["spotcheck", "elicit", "gap-status", "report"],
        help="Harness: spotcheck (default), elicit, gap-status, or report",
    )
    eval_p.add_argument(
        "--fixtures",
        default=None,
        help="Fixture JSON/dir (spotcheck) or gap-status handlabel JSON",
    )
    eval_p.add_argument(
        "--responses",
        default=None,
        help="Elicit: JSON map condition_id → agent response text",
    )
    eval_p.add_argument(
        "--protocol",
        default=None,
        help="Elicit: protocol JSON (default examples/elicit_ab_protocol.json)",
    )
    eval_p.add_argument(
        "--domain",
        default="ai",
        choices=[d.value for d in Domain],
        help="Elicit: domain for inject packaging",
    )
    eval_p.add_argument("--topic", default="", help="Elicit: optional topic")
    eval_p.add_argument("--n", type=int, default=3, help="Elicit: unknowns per inject")
    eval_p.add_argument(
        "--profile",
        default="humanity_default",
        help="Elicit: ValueProfile preset",
    )
    eval_p.add_argument("--json", action="store_true")

    for emo_name, emo_help in (
        ("emotions", "Emotion catalog + epistemic cues (UX annotations — does not feel)"),
        ("epistemic", "Alias of emotions — cues/catalog/mix/annotate/elicit/pack"),
    ):
        emo_p = sub.add_parser(emo_name, help=emo_help)
        emo_sub = emo_p.add_subparsers(dest="emotions_cmd")

        cues_p = emo_sub.add_parser("cues", help="List epistemic cue tags")
        cues_p.add_argument("--json", action="store_true")

        cat_p = emo_sub.add_parser(
            "catalog", help="List mixable named emotions (optional --family)"
        )
        cat_p.add_argument(
            "--family",
            default=None,
            help="Filter: epistemic | basic | social | achievement",
        )
        cat_p.add_argument("--json", action="store_true")

        mix_p = emo_sub.add_parser(
            "mix",
            help="Mix emotions by percent, e.g. curiosity=40 confusion=30 awe=30",
        )
        mix_p.add_argument(
            "parts",
            nargs="+",
            help="emotion_id=percent_or_weight (repeatable)",
        )
        mix_p.add_argument("--json", action="store_true")

        ann_p = emo_sub.add_parser("annotate", help="Annotate a question with epistemic cues")
        ann_p.add_argument("question", help="Question text to annotate")
        ann_p.add_argument(
            "--gap",
            default="unanswered",
            dest="gap_status",
            help="Gap status (unanswered, partially_answered, …)",
        )
        ann_p.add_argument("--surprise", type=float, default=0.5)
        ann_p.add_argument("--neglectedness", type=float, default=0.5)
        ann_p.add_argument("--answerability", type=float, default=0.5)
        ann_p.add_argument("--notes", default="")
        ann_p.add_argument("--domain", default="ai")
        ann_p.add_argument("--json", action="store_true")

        elicit_p = emo_sub.add_parser("elicit", help="Incongruity → investigation framing helpers")
        elicit_p.add_argument("--json", action="store_true")

        pack_p = emo_sub.add_parser("pack", help="Load affective_science (or named) domain pack")
        pack_p.add_argument(
            "--name",
            default="affective_science",
            help="Pack id (default: affective_science)",
        )
        pack_p.add_argument("--json", action="store_true")

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
        f"  Emotions:      GET /v1/emotions/catalog  POST /v1/emotions/mix\n"
        f"                 GET /v1/emotions/cues  POST /v1/emotions/annotate\n"
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
    print(
        f"Compare profiles  domain={args.domain}  "
        f"A={args.profile_a}  B={args.profile_b}\n"
    )
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


def _preferences(args: argparse.Namespace) -> int:
    from artificial_curiosity.preferences import (
        learn_profile_weight_hints,
        summarize_preferences,
    )

    cmd = getattr(args, "preferences_cmd", None)
    if cmd == "hints":
        hints = learn_profile_weight_hints(args.path, profile_name=args.profile)
        if args.json:
            print(json.dumps(hints, indent=2))
            return 0
        print(f"Preference weight hints for profile={args.profile}")
        print(f"  ok={hints.get('ok')}  reason={hints.get('reason')}")
        print(f"  n_prefer={hints.get('n_prefer')}  n_reject={hints.get('n_reject')}")
        deltas = hints.get("deltas") or {}
        if deltas:
            print("  deltas:")
            for k, v in deltas.items():
                print(f"    {k}: {v:+.4f}")
        else:
            print("  deltas: (none)")
        if hints.get("clamped_weights"):
            print(f"  clamped: {', '.join(hints['clamped_weights'])}")
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
    print(
        "Usage:\n"
        "  curiosity preferences hints --path labeled.jsonl [--profile NAME]\n"
        "  curiosity preferences summarize --path labeled.jsonl [--profile NAME]\n"
        "Preference tools are profile-scoped decision aids — not calibrated learning.",
        file=sys.stderr,
    )
    return 2

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
        print(f"Elicit A/B  protocol={payload.get('protocol')}  v={payload.get('protocol_version')}")
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
            load_gap_status_fixtures(args.fixtures)
            if args.fixtures
            else load_gap_status_fixtures()
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
                f"  [{mark}] {r['case_id']}: gold={r['gold_status']} "
                f"pred={r['predicted_status']}"
            )
        return 0

    if cmd == "report":
        from artificial_curiosity.eval_report import build_eval_report

        root = Path(__file__).resolve().parents[2]
        sample = root / "examples" / "elicit_ab_sample_responses.json"
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
        print(f"  gap_f1={gf.get('f1')}  precision={gf.get('precision')}  recall={gf.get('recall')}")
        gs = secs.get("gap_status_handlabel") or {}
        print(
            f"  gap_status accuracy={gs.get('status_accuracy')}  "
            f"rbu_recall={gs.get('related_but_unanswered_recall')}"
        )
        el = secs.get("elicit_rubric") or {}
        print(f"  elicit means={el.get('condition_means')}  deltas={el.get('deltas')}")
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


def _parse_mix_parts(parts: list[str]) -> dict[str, float]:
    out: dict[str, float] = {}
    for part in parts:
        raw = part.strip()
        if "=" not in raw:
            raise ValueError(
                f"Expected emotion_id=percent, got '{part}'. "
                "Example: curiosity=40 confusion=30 awe=30"
            )
        key, val = raw.split("=", 1)
        kid = key.strip().lower().replace("-", "_")
        if not kid:
            raise ValueError(f"Empty emotion id in '{part}'")
        out[kid] = float(val.strip())
    return out


def _emotions(args: argparse.Namespace) -> int:
    from artificial_curiosity.emotions import (
        annotate_epistemic,
        elicit_helpers,
        emotion_catalog,
        emotion_pack,
        list_epistemic_cues,
        mix_emotions,
    )

    cmd = getattr(args, "emotions_cmd", None)
    if not cmd:
        print(
            "Usage: curiosity emotions {cues|catalog|mix|annotate|elicit|pack}\n"
            "  (alias: curiosity epistemic …)\n"
            "  mix example: curiosity emotions mix curiosity=40 confusion=30 awe=30\n"
            "Emotion tags/mixes are UX annotations — this system does not feel.",
            file=sys.stderr,
        )
        return 2

    if cmd == "cues":
        payload = list_epistemic_cues()
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print("Epistemic cue tags (annotation only — does not feel)\n")
            for c in payload["cues"]:
                print(f"  {c['tag']}: {c['meaning']}")
            print(f"\n{payload['disclaimer']}")
        return 0

    if cmd == "catalog":
        try:
            payload = emotion_catalog(family=getattr(args, "family", None))
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(
                f"Emotion catalog v{payload.get('version')} — "
                f"{payload['count']} emotions (annotation only)\n"
            )
            for e in payload["emotions"]:
                print(f"  {e['id']:14} [{e['family']}] {e['label']}")
            print(f"\n{payload['disclaimer']}")
        return 0

    if cmd == "mix":
        try:
            weights = _parse_mix_parts(list(args.parts))
            payload = mix_emotions(weights)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(f"primary={payload['primary']}")
            print(
                "mix=" + ", ".join(f"{c['id']}={c['percent']:.1f}%" for c in payload["components"])
            )
            if payload.get("cue_tags"):
                print(f"cues={', '.join(payload['cue_tags'])}")
            print(payload["inject_fragment"])
            print(payload["disclaimer"])
        return 0

    if cmd == "annotate":
        try:
            payload = annotate_epistemic(
                args.question,
                gap_status=args.gap_status,
                surprise=args.surprise,
                neglectedness=args.neglectedness,
                answerability=args.answerability,
                notes=args.notes,
                domain=args.domain,
            )
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            cues = payload["epistemic_cues"]
            print(f"primary={cues['primary']}")
            print(f"tags={', '.join(cues['tags'])}")
            if payload.get("inject_fragment"):
                print(payload["inject_fragment"])
            print(payload["disclaimer"])
        return 0

    if cmd == "elicit":
        payload = elicit_helpers()
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(payload["framing"])
            print()
            print(payload["inject_prefix"])
        return 0

    if cmd == "pack":
        try:
            payload = emotion_pack(args.name)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(f"{payload['name']} v{payload.get('version')} — {payload['count']} questions")
            print(payload.get("description") or "")
            for q in payload["questions"][:5]:
                print(f"  - {q['id']}: {q['question'][:100]}")
            if payload["count"] > 5:
                print(f"  … +{payload['count'] - 5} more (use --json)")
            print(f"\n{payload['disclaimer']}")
        return 0

    print(f"Unknown emotions subcommand: {cmd}", file=sys.stderr)
    return 2


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()

    # Bare flags → default `run` so `curiosity --domain ai` still works.
    if not argv or argv[0] not in (
        "run",
        "serve",
        "spark",
        "profiles",
        "preferences",
        "compare-profiles",
        "critique-brief",
        "voi-worksheet",
        "eval",
        "emotions",
        "epistemic",
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
    if args.command == "preferences":
        return _preferences(args)
    if args.command == "compare-profiles":
        return _compare_profiles(args)
    if args.command == "critique-brief":
        return _critique_brief(args)
    if args.command == "voi-worksheet":
        return _voi_worksheet(args)
    if args.command == "eval":
        return _eval(args)
    if args.command in ("emotions", "epistemic"):
        return _emotions(args)
    return _run_engine(args)


if __name__ == "__main__":
    sys.exit(main())
