"""CLI for Artificial Emotions.

``artificial_emotions.cli:main`` is the stable entry point (the ``curiosity``
console script). This module is a thin re-export; the implementation lives in
``artificial_emotions.cli_pkg``:

    cli_pkg/__init__.py        main() and the subcommand dispatch table
    cli_pkg/parser.py          every argparse definition
    cli_pkg/commands/          handlers, grouped by subcommand
"""

from __future__ import annotations

import sys

from artificial_emotions.cli_pkg import build_parser, main

__all__ = ["build_parser", "main"]


if __name__ == "__main__":
    sys.exit(main())
