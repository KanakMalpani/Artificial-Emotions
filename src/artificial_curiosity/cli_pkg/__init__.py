"""CLI entry point and command dispatch.

Public surface stays ``artificial_curiosity.cli`` — this package is the
implementation behind it. Parser definitions live in ``parser.py``, handlers in
``commands/``.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable

from artificial_curiosity.cli_pkg.commands import (
    _compare_profiles,
    _critique_brief,
    _emotions,
    _eval,
    _preferences,
    _profiles,
    _run_engine,
    _serve,
    _spark,
    _surprise_worksheet,
    _voi_worksheet,
)
from artificial_curiosity.cli_pkg.parser import build_parser

__all__ = ["build_parser", "main"]

Handler = Callable[[argparse.Namespace], int]

# `run` is absent on purpose — it is the fallback when no subcommand matches.
_DISPATCH: dict[str, Handler] = {
    "serve": _serve,
    "spark": _spark,
    "profiles": _profiles,
    "preferences": _preferences,
    "compare-profiles": _compare_profiles,
    "critique-brief": _critique_brief,
    "voi-worksheet": _voi_worksheet,
    "surprise-worksheet": _surprise_worksheet,
    "eval": _eval,
    "emotions": _emotions,
    "epistemic": _emotions,
}


def _subcommand_names(parser: argparse.ArgumentParser) -> set[str]:
    """Read subcommand names off the parser instead of hardcoding them.

    Keeps the bare-flag fallback below in sync automatically — a new subcommand
    used to need editing in two places.
    """
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return set(action.choices)
    return set()


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()

    # Bare flags → default `run` so `curiosity --domain ai` still works.
    known = _subcommand_names(parser) | {"-h", "--help"}
    if not argv or argv[0] not in known:
        argv = ["run", *argv]

    args = parser.parse_args(argv)
    handler = _DISPATCH.get(args.command, _run_engine)
    return handler(args)
