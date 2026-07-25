"""Locate bundled data files (worksheet templates, eval fixtures).

These files live at the repo root under ``examples/`` and ``evals/fixtures/``
for editing, and are force-included into the wheel under
``artificial_curiosity/data/`` so installed users get them too.

Resolution order is package-first, then repo checkout. Package-first matters
because an editable install has *both*, and the shipped copy is the one whose
behaviour we test.
"""

from __future__ import annotations

from pathlib import Path

__all__ = [
    "data_dir",
    "find_data_dir",
    "find_data_file",
    "repo_root",
]

_PACKAGE_DIR = Path(__file__).resolve().parent


def data_dir() -> Path:
    """Package-local data root (present in built wheels/sdists)."""
    return _PACKAGE_DIR / "data"


def repo_root() -> Path:
    """Source-checkout root — only meaningful when running from a clone."""
    return _PACKAGE_DIR.parents[1]


def find_data_file(relative: str) -> Path:
    """Resolve a data file such as ``examples/voi_worksheet_template.json``.

    Returns the packaged copy when present, else the repo-checkout copy. When
    neither exists the packaged path is returned so the caller's own
    ``FileNotFoundError`` names a stable location.
    """
    packaged = data_dir() / relative
    if packaged.is_file():
        return packaged
    source = repo_root() / relative
    if source.is_file():
        return source
    return packaged


def find_data_dir(relative: str) -> Path:
    """Directory counterpart of :func:`find_data_file` (e.g. ``evals/fixtures``)."""
    packaged = data_dir() / relative
    if packaged.is_dir():
        return packaged
    source = repo_root() / relative
    if source.is_dir():
        return source
    return packaged
