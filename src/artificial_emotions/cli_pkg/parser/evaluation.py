"""Argparse for offline eval / validation / discovery."""

from __future__ import annotations

import argparse

from artificial_emotions.models import Domain

__all__ = ["add_evaluation_parsers"]


def add_evaluation_parsers(sub: argparse._SubParsersAction) -> None:
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

    eval_p = sub.add_parser(
        "eval",
        help="Offline eval harnesses (spotcheck / elicit / calibration; no vanity %%)",
    )
    eval_p.add_argument(
        "eval_cmd",
        nargs="?",
        default="spotcheck",
        choices=["spotcheck", "elicit", "gap-status", "report", "cooccur", "calibration"],
        help=(
            "Harness: spotcheck (default), elicit, gap-status, report, cooccur, "
            "or calibration (preference JSONL telemetry — not calibrated)"
        ),
    )
    eval_p.add_argument(
        "--fixtures",
        default=None,
        help="Fixture JSON/dir (spotcheck) or gap-status handlabel JSON",
    )
    eval_p.add_argument(
        "--path",
        default=None,
        help=(
            "Preference JSONL for eval calibration "
            "(counts / outcome mix / hint magnitudes / coverage — not calibrated)"
        ),
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
