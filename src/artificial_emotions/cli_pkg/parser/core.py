"""Argparse for ranking / serve / preference surfaces.

``run``, ``spark``, ``serve``, ``export``, ``profiles``, ``preferences``,
``compare-profiles``. Flag names, defaults, and help text are the contract —
do not "clean up" wording here.
"""

from __future__ import annotations

import argparse

from artificial_emotions.models import (
    Domain,
    list_profile_names,
)

__all__ = ["add_core_parsers"]


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
            "(profile-scoped; not calibrated; CLI only; preview unless "
            "--preference-learn-apply)"
        ),
    )
    p.add_argument(
        "--preference-learn-apply",
        action="store_true",
        help=(
            "Apply --preference-learn hints onto this run's ValueProfile copy "
            "(default: preview only; never overwrites a named preset)"
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


def add_core_parsers(sub: argparse._SubParsersAction) -> None:
    run_p = sub.add_parser("run", help="Rank unanswered questions (default)")
    _add_run_args(run_p)

    serve_p = sub.add_parser(
        "serve",
        help=(
            "Start the HTTP API (CORS deny-by-default; auth opt-in via "
            "CURIOSITY_API_KEY; rate limit via CURIOSITY_API_RATE_LIMIT_PER_MINUTE; "
            "opt-in per-key quota via CURIOSITY_API_QUOTA_REQUESTS; "
            "opt-in audit JSONL via CURIOSITY_AUDIT_LOG; "
            "non-loopback bind requires CURIOSITY_ALLOW_NONLOCAL_BIND=1)"
        ),
    )
    serve_p.add_argument(
        "--host",
        default=None,
        help=(
            "Bind address (default: CURIOSITY_HOST or 127.0.0.1). "
            "Non-loopback (0.0.0.0) requires CURIOSITY_ALLOW_NONLOCAL_BIND=1."
        ),
    )
    serve_p.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port (default: CURIOSITY_PORT or 8000)",
    )
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
    spark_p.add_argument(
        "--compact",
        action="store_true",
        help="Print rank-1 compact_unknown as JSON (not the full inject pack)",
    )
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
        help=(
            "Preview (default) or apply tiny ValueProfile weight deltas from "
            "labeled JSONL — not calibrated learning"
        ),
    )
    hints_p.add_argument("--path", required=True, help="Labeled preference JSONL path")
    hints_p.add_argument(
        "--profile",
        default="humanity_default",
        help=f"ValueProfile preset ({', '.join(list_profile_names())})",
    )
    hints_p.add_argument(
        "--apply",
        action="store_true",
        help=(
            "Apply hints onto a profile copy (default: preview). "
            "Never overwrites a named preset. Not calibrated learning."
        ),
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

    export_p = sub.add_parser(
        "export",
        help=(
            "Export a ranked unknowns JSON document (file / stdout). "
            "Webhook URLs are not accepted (SSRF)"
        ),
    )
    export_sub = export_p.add_subparsers(dest="export_cmd")
    unk_p = export_sub.add_parser(
        "unknowns",
        help=(
            "Export a ranked set (runs the pipeline, or --from a previous "
            "run --json). File --out is the v1 path; no webhooks"
        ),
    )
    _add_run_args(unk_p)
    unk_p.add_argument(
        "--out",
        default=None,
        help="Write the JSON document to this file (v1 delivery path)",
    )
    unk_p.add_argument(
        "--from",
        dest="from_path",
        default=None,
        help=(
            "Reuse a previous `emotions run --json` or HTTP questions file instead of ranking again"
        ),
    )
