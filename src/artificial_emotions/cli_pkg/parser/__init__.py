"""Argparse definitions for every `curiosity` subcommand.

Kept apart from the handlers so the full command surface can be read without
pulling in the pipeline. Group modules (`core`, `evaluation`, `alive`,
`worksheets`) own the flags; ``build_parser`` is the stable facade.

``from artificial_emotions.cli_pkg.parser import build_parser`` and
``artificial_emotions.cli.build_parser`` stay the public import paths.
"""

from __future__ import annotations

import argparse

from artificial_emotions.cli_pkg.parser.alive import add_alive_parsers
from artificial_emotions.cli_pkg.parser.core import add_core_parsers
from artificial_emotions.cli_pkg.parser.evaluation import add_evaluation_parsers
from artificial_emotions.cli_pkg.parser.worksheets import add_worksheet_parsers

__all__ = ["build_parser"]


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="curiosity",
        description="Generate and rank valuable unanswered questions.",
    )
    sub = p.add_subparsers(dest="command")
    add_core_parsers(sub)
    add_worksheet_parsers(sub)
    add_evaluation_parsers(sub)
    add_alive_parsers(sub)
    return p
