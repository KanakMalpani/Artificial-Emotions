"""Argparse definitions for every `curiosity` subcommand.

Kept apart from the handlers so the full command surface can be read in
one place — and so `build_parser()` stays importable without pulling in
the pipeline."""

from __future__ import annotations

import argparse

from artificial_emotions.models import (
    Domain,
    list_profile_names,
)


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

    serve_p = sub.add_parser(
        "serve",
        help=(
            "Start the HTTP API (CORS deny-by-default; auth opt-in via "
            "CURIOSITY_API_KEY; rate limit via CURIOSITY_API_RATE_LIMIT_PER_MINUTE)"
        ),
    )
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

    pair_p = pref_sub.add_parser(
        "suggest-pair",
        help="Suggest next pairwise duel among candidate ids (not BT fit)",
    )
    pair_p.add_argument(
        "--candidates",
        required=True,
        help="Comma-separated question ids (top-k)",
    )
    pair_p.add_argument("--path", default=None, help="Optional preference JSONL for prior edges")
    pair_p.add_argument("--profile", default="humanity_default")
    pair_p.add_argument("--json", action="store_true")

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

    stance_p = sub.add_parser(
        "stance",
        help="Ask a different question of a ranked set (doubt, safety, focus, close, taste, survey)",
    )
    stance_p.add_argument(
        "stance_name",
        nargs="?",
        default="list",
        help="Stance name, or omit to list them",
    )
    stance_p.add_argument("--domain", default="ai", choices=[d.value for d in Domain])
    stance_p.add_argument("--topic", default="")
    stance_p.add_argument("--n", type=int, default=6)
    stance_p.add_argument("--profile", default="humanity_default")
    stance_p.add_argument("--literature", action="store_true")
    stance_p.add_argument("--json", action="store_true")

    imagine_p = sub.add_parser(
        "imagine",
        help=(
            "Generate quarantined imagined content "
            "(premortem, reformulation, counterfactual, transfer); "
            "offline, never ranked"
        ),
    )
    imagine_p.add_argument(
        "imagine_kind",
        nargs="?",
        default="list",
        help=(
            "Imagination kind (premortem|reformulation|counterfactual|transfer), or omit to list"
        ),
    )
    imagine_p.add_argument("--domain", default="ai", choices=[d.value for d in Domain])
    imagine_p.add_argument("--topic", default="")
    imagine_p.add_argument("--n", type=int, default=6)
    imagine_p.add_argument("--profile", default="humanity_default")
    imagine_p.add_argument(
        "--literature",
        action="store_true",
        help="Optional literature for the ranking step only; generators stay offline",
    )
    imagine_p.add_argument(
        "--corpus",
        default="",
        help="Local corpus (year+concepts JSON) — required for transfer",
    )
    imagine_p.add_argument(
        "--seed",
        default="",
        help="Seed concept for transfer (e.g. 'Fish oil')",
    )
    imagine_p.add_argument("--json", action="store_true")

    validate_p = sub.add_parser(
        "validate",
        help="Retrospective validation: does past-only discovery/transfer predict the future?",
    )
    validate_p.add_argument("--corpus", required=True, help="Corpus with year + concepts")
    validate_p.add_argument("--cutoff", type=int, required=True, help="Hold out this year onward")
    validate_p.add_argument("--seeds", required=True, help="Comma-separated seed concepts")
    validate_p.add_argument(
        "--method",
        default="abc",
        choices=["abc", "transfer"],
        help="abc = Swanson discovery; transfer = structural analogy (B3)",
    )
    validate_p.add_argument("--n", type=int, default=5, help="Max proposals per seed")
    validate_p.add_argument("--baseline", type=int, default=5, help="Random control pairs per seed")
    validate_p.add_argument("--json", action="store_true")

    discover_p = sub.add_parser(
        "discover",
        help="Find links nobody has studied, from real literature (needs network)",
    )
    discover_p.add_argument("seed", help="Concept to start from, e.g. 'gut microbiome'")
    discover_p.add_argument("--n", type=int, default=8, help="Max links to return")
    discover_p.add_argument("--bridges", type=int, default=4, help="Bridging concepts to expand")
    discover_p.add_argument(
        "--ceiling",
        type=int,
        default=400,
        help="Above this many A-and-C works the link is already studied",
    )
    discover_p.add_argument(
        "--cache-dir",
        default=None,
        dest="cache_dir",
        help="Cache OpenAlex responses here (recommended; the API rate-limits)",
    )
    discover_p.add_argument(
        "--corpus",
        default=None,
        help="Run offline against your own corpus (JSON/JSONL of {title, concepts})",
    )
    discover_p.add_argument("--json", action="store_true")

    explore_p = sub.add_parser(
        "explore",
        help="Run the curiosity loop: appraise, feel, modulate, remember, repeat",
    )
    explore_p.add_argument("--domain", default="ai", choices=[d.value for d in Domain])
    explore_p.add_argument("--topic", default="")
    explore_p.add_argument("--steps", type=int, default=5, help="Passes to take (max 12)")
    explore_p.add_argument("--n", type=int, default=5, help="Unknowns per step")
    explore_p.add_argument("--profile", default="humanity_default")
    explore_p.add_argument("--literature", action="store_true", help="Ground gaps in literature")
    explore_p.add_argument(
        "--affect-weights",
        action="store_true",
        dest="affect_weights",
        help="Let affect nudge ValueProfile weights (bounded, logged; off by default)",
    )
    explore_p.add_argument(
        "--no-jump", action="store_true", help="Stay in one domain even when bored"
    )
    explore_p.add_argument(
        "--no-memory",
        action="store_true",
        help=("Do not read/write ~/.artificial_emotions/memory.json (also: CURIOSITY_NO_MEMORY=1)"),
    )
    explore_p.add_argument("--json", action="store_true")

    decompose_p = sub.add_parser(
        "decompose",
        help="Open one unknown into sub-questions, a first step, and falsifiers (never an answer)",
    )
    decompose_p.add_argument("question", help="The unknown to open up")
    decompose_p.add_argument(
        "--ops",
        default="",
        dest="operationalization",
        help="How you'd know it was answered; numeric criteria become falsifiers",
    )
    decompose_p.add_argument("--domain", default="ai", choices=[d.value for d in Domain])
    decompose_p.add_argument(
        "--depth",
        type=int,
        default=1,
        choices=[1, 2, 3],
        help="1 = one layer; 2-3 also split mechanism and confound",
    )
    decompose_p.add_argument("--answerability", type=float, default=None)
    decompose_p.add_argument("--tractability", type=float, default=None)
    decompose_p.add_argument("--risk", type=float, default=None)
    decompose_p.add_argument("--json", action="store_true")

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

    surprise_p = sub.add_parser(
        "surprise-worksheet",
        help="Fill Bayesian-surprise belief-shift worksheet (not EVSI / not axis rename)",
    )
    surprise_p.add_argument("--question-id", default=None)
    surprise_p.add_argument("--profile", default=None, dest="profile_name")
    surprise_p.add_argument("--predicted-surprise", type=float, default=None)
    surprise_p.add_argument("--pilot-result", default="")
    surprise_p.add_argument("--belief-shift", type=int, default=None)
    surprise_p.add_argument("--note", default="", dest="crude_update_note")
    surprise_p.add_argument("--json", action="store_true")

    eval_p = sub.add_parser(
        "eval",
        help="Offline eval harnesses (spotcheck / elicit A/B / gap-status; no vanity %%)",
    )
    eval_p.add_argument(
        "eval_cmd",
        nargs="?",
        default="spotcheck",
        choices=["spotcheck", "elicit", "gap-status", "report", "cooccur"],
        help="Harness: spotcheck (default), elicit, gap-status, report, or cooccur",
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
        mix_p.add_argument(
            "--simulate-feeling",
            type=str,
            default="true",
            help="Include felt_simulation (true|false)",
        )

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

        _add_memory_subparser(emo_sub)
        _add_dream_subparser(emo_sub)

    # Top-level: `emotions memory show` when the binary is `emotions`
    mem_top = sub.add_parser(
        "memory",
        help=(
            "Persistent CLI memory (local JSON; opt-out CURIOSITY_NO_MEMORY=1) "
            "— annotation continuity, does not feel"
        ),
    )
    mem_top_sub = mem_top.add_subparsers(dest="memory_cmd")
    _fill_memory_subcommands(mem_top_sub)

    # Top-level: `emotions dream` — explicit offline reanalysis only
    dream_top = sub.add_parser(
        "dream",
        help=(
            "Offline reanalysis of stored PersistentMemory history "
            "(explicit only — never automatic; does not feel)"
        ),
    )
    _fill_dream_arguments(dream_top)

    return p


def _add_memory_subparser(parent: argparse._SubParsersAction) -> None:
    mem_p = parent.add_parser(
        "memory",
        help=(
            "Persistent CLI memory show|forget|reset|avoiding "
            "(local JSON; never on by default for MCP/HTTP)"
        ),
    )
    mem_sub = mem_p.add_subparsers(dest="memory_cmd")
    _fill_memory_subcommands(mem_sub)


def _add_dream_subparser(parent: argparse._SubParsersAction) -> None:
    dream_p = parent.add_parser(
        "dream",
        help=(
            "Offline reanalysis of stored history "
            "(explicit only — never automatic / background; does not feel)"
        ),
    )
    _fill_dream_arguments(dream_p)


def _fill_dream_arguments(dream_p: argparse.ArgumentParser) -> None:
    dream_p.add_argument("--json", action="store_true")
    dream_p.add_argument(
        "--path",
        default=None,
        help="Override memory JSON path (default ~/.artificial_emotions/memory.json)",
    )


def _fill_memory_subcommands(mem_sub: argparse._SubParsersAction) -> None:
    show_p = mem_sub.add_parser("show", help="Show what is remembered (local JSON)")
    show_p.add_argument("--json", action="store_true")
    show_p.add_argument(
        "--path",
        default=None,
        help="Override memory JSON path (default ~/.artificial_emotions/memory.json)",
    )

    avoid_p = mem_sub.add_parser(
        "avoiding",
        help=(
            "List questions seen many times and picked zero "
            "(pattern only — cannot distinguish avoidance from judgment)"
        ),
    )
    avoid_p.add_argument("--json", action="store_true")
    avoid_p.add_argument("--path", default=None)

    forget_p = mem_sub.add_parser(
        "forget",
        help="Forget a session id, question id, or keyword (sessions|encounters|mood)",
    )
    forget_p.add_argument("what", help="session id, question id, or sessions|encounters|mood|…")
    forget_p.add_argument("--json", action="store_true")
    forget_p.add_argument("--path", default=None)

    reset_p = mem_sub.add_parser("reset", help="Wipe all persistent memory and delete the file")
    reset_p.add_argument("--json", action="store_true")
    reset_p.add_argument("--path", default=None)
