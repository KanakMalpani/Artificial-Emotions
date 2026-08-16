"""Argparse for Alive continuity: explore, loop, emotions, memory, dream."""

from __future__ import annotations

import argparse

from artificial_emotions.models import Domain

__all__ = ["add_alive_parsers"]


def add_alive_parsers(sub: argparse._SubParsersAction) -> None:
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
        "--somatic-modulate",
        action="store_true",
        dest="somatic_modulate",
        help=(
            "Let high-coercion affect (fear, anger, disgust, joy, sadness) change "
            "search knobs. Off by default: those ids still appraise and surface. "
            "Never raises the risk ceiling."
        ),
    )
    explore_p.add_argument(
        "--no-jump", action="store_true", help="Stay in one domain even when bored"
    )
    explore_p.add_argument(
        "--no-memory",
        action="store_true",
        help=("Do not read/write ~/.artificial_emotions/memory.json (also: CURIOSITY_NO_MEMORY=1)"),
    )
    explore_p.add_argument(
        "--preference-log",
        default=None,
        help=(
            "Opt-in JSONL path; matching outcome events feed pride/shame appraisal "
            "(silent if none match)"
        ),
    )
    explore_p.add_argument("--json", action="store_true")

    loop_p = sub.add_parser(
        "loop",
        help=(
            "Dry-run: outcome JSONL → suggested re-rank / next explore "
            "(does not run experiments; not a lab closed-loop)"
        ),
        description=(
            "Dry-run: read event_type=outcome rows from preference JSONL and "
            "suggest a re-rank plus a next explore step. Does not run "
            "experiments. Not a lab closed-loop."
        ),
    )
    loop_p.add_argument(
        "--outcomes",
        required=True,
        help="Preference JSONL path with event_type=outcome rows",
    )
    loop_p.add_argument(
        "--profile",
        default=None,
        help="Optional ValueProfile filter (default: all events in the file)",
    )
    loop_p.add_argument("--json", action="store_true")

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

        pack_p = emo_sub.add_parser(
            "pack",
            help="Load a bundled domain pack, or `check` against the CONTRIBUTING bar",
        )
        pack_p.add_argument(
            "pack_cmd",
            nargs="?",
            default=None,
            choices=["check", "load"],
            help=(
                "check = lint operationalization + why_it_matters; omit or load = print pack seeds"
            ),
        )
        pack_p.add_argument(
            "--name",
            default=None,
            help="Pack id (load default: affective_science; check: filter bundled pack)",
        )
        pack_p.add_argument(
            "--path",
            action="append",
            default=None,
            dest="pack_paths",
            help="Pack JSON to lint (repeatable; check only). Omit to lint bundled packs.",
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
