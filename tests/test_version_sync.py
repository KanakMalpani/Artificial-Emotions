"""Ratchet: the six release-version copies must stay in lockstep.

Release bumps touch independent files. Drift ships wrong banners, wrong
``AppConfig.version`` defaults, or docs that disagree with the package.
This guard fails the moment any copy diverges.

Sources (must all equal the same ``X.Y.Z`` string; doc banners may use a ``v`` prefix):

1. ``pyproject.toml`` ``[project].version``
2. ``src/artificial_emotions/__init__.py`` ``__version__``
3. ``src/artificial_emotions/config.py`` ``AppConfig.version`` field default
4. ``docs/LIMITS.md`` banner (``vX.Y.Z``)
5. ``docs/INDEX.md`` banner (``vX.Y.Z``)
6. ``docs/ROADMAP.md`` ``Product version today`` (``X.Y.Z``)

Also checked at runtime: ``get_config().version`` and the dataclass field
default must match ``__version__``.

Mutation proof (2026-08-02): temporarily set LIMITS.md to ``v9.9.9``,
ran ``pytest tests/test_version_sync.py::test_six_version_copies_agree -q``,
watched it FAIL (``LIMITS.md: 9.9.9`` vs ``0.4.1`` elsewhere), then restored.
``test_version_guard_fails_on_intentional_mismatch`` re-enacts that failure
mode without dirtying the tree.

*A guard you have not seen fail is not a guard.*
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import fields
from pathlib import Path

import pytest

from artificial_emotions import __version__
from artificial_emotions.config import AppConfig, clear_config_cache, get_config

_ROOT = Path(__file__).resolve().parents[1]

_SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def _pyproject_version() -> str:
    data = tomllib.loads((_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def _init_version() -> str:
    text = (_ROOT / "src" / "artificial_emotions" / "__init__.py").read_text(encoding="utf-8")
    m = re.search(r'^__version__\s*=\s*"([^"]+)"', text, re.MULTILINE)
    assert m, "__version__ assignment missing in __init__.py"
    return m.group(1)


def _config_default_version() -> str:
    text = (_ROOT / "src" / "artificial_emotions" / "config.py").read_text(encoding="utf-8")
    m = re.search(r'version:\s*str\s*=\s*"([^"]+)"', text)
    assert m, "AppConfig.version default missing in config.py"
    return m.group(1)


def _limits_banner_version() -> str:
    text = (_ROOT / "docs" / "LIMITS.md").read_text(encoding="utf-8")
    m = re.search(r"Honest bounds for \*\*v(\d+\.\d+\.\d+)\*\*", text)
    assert m, "LIMITS.md version banner missing or malformed"
    return m.group(1)


def _index_banner_version() -> str:
    text = (_ROOT / "docs" / "INDEX.md").read_text(encoding="utf-8")
    m = re.search(r"\(v(\d+\.\d+\.\d+)\s*—", text)
    assert m, "INDEX.md version banner missing or malformed"
    return m.group(1)


def _roadmap_banner_version() -> str:
    text = (_ROOT / "docs" / "ROADMAP.md").read_text(encoding="utf-8")
    m = re.search(r"Product version today:\*\*\s*`(\d+\.\d+\.\d+)`", text)
    assert m, "ROADMAP.md Product version today missing or malformed"
    return m.group(1)


def _version_copies() -> dict[str, str]:
    return {
        "pyproject.toml": _pyproject_version(),
        "__init__.__version__": _init_version(),
        "AppConfig.version default": _config_default_version(),
        "LIMITS.md": _limits_banner_version(),
        "INDEX.md": _index_banner_version(),
        "ROADMAP.md": _roadmap_banner_version(),
    }


def test_six_version_copies_agree():
    copies = _version_copies()
    for name, ver in copies.items():
        assert _SEMVER.match(ver), f"{name} is not X.Y.Z: {ver!r}"

    unique = sorted(set(copies.values()))
    assert len(unique) == 1, "version drift across the six release copies:\n" + "\n".join(
        f"  {k}: {v}" for k, v in copies.items()
    )


def test_runtime_version_mirrors_package():
    clear_config_cache()
    assert get_config().version == __version__
    field = next(f for f in fields(AppConfig) if f.name == "version")
    assert field.default == __version__
    assert field.default == _config_default_version()


def test_version_guard_fails_on_intentional_mismatch(monkeypatch: pytest.MonkeyPatch):
    """Companion mutation: prove the ratchet catches drift.

    "A guard you have not seen fail is not a guard."

    Live proof (agent run 2026-08-02): LIMITS.md banner was set to
    ``v9.9.9``, ``test_six_version_copies_agree`` failed with version drift,
    then restored.
    """
    monkeypatch.setattr(
        f"{__name__}._limits_banner_version",
        lambda: "0.0.0",
    )
    with pytest.raises(AssertionError, match="version drift"):
        test_six_version_copies_agree()
