"""Subcommand handlers, one module per group.

Each handler takes the parsed ``argparse.Namespace`` and returns an exit code.
Names keep their leading underscore: this package is internal, and these are
not part of the published API.
"""

from __future__ import annotations

from artificial_emotions.cli_pkg.commands.emotions import _emotions
from artificial_emotions.cli_pkg.commands.evaluation import _eval, _validate
from artificial_emotions.cli_pkg.commands.preferences import _preferences
from artificial_emotions.cli_pkg.commands.profiles import _compare_profiles, _profiles
from artificial_emotions.cli_pkg.commands.ranking import (
    _discover,
    _explore,
    _run_engine,
    _serve,
    _spark,
)
from artificial_emotions.cli_pkg.commands.worksheets import (
    _critique_brief,
    _decompose,
    _surprise_worksheet,
    _voi_worksheet,
)

__all__ = [
    "_compare_profiles",
    "_critique_brief",
    "_decompose",
    "_discover",
    "_emotions",
    "_explore",
    "_eval",
    "_preferences",
    "_profiles",
    "_run_engine",
    "_serve",
    "_spark",
    "_validate",
    "_surprise_worksheet",
    "_voi_worksheet",
]
