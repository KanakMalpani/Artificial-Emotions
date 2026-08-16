"""Emotions catalog/mix split: stable re-export, catalog contract unchanged."""

from __future__ import annotations

import ast
from pathlib import Path

from artificial_emotions import emotions, emotions_catalog, emotions_mix
from artificial_emotions.emotions import emotion_catalog, mix_emotions

_SRC = Path(__file__).resolve().parents[1] / "src" / "artificial_emotions"

_STABLE_CALLERS = (
    "appraisal.py",
    "appraisal_interpreter.py",
    "modulate_effects.py",
    "explore.py",
    "__init__.py",
)


def test_emotions_reexport_catalog_and_mix_objects():
    assert emotions.emotion_catalog is emotions_catalog.emotion_catalog
    assert emotions.mix_emotions is emotions_mix.mix_emotions
    assert emotions.feel is emotions_mix.feel


def test_catalog_payload_contract_unchanged():
    cat = emotion_catalog()
    assert cat["honesty"] == "computational_affect"
    assert cat["count"] >= 54
    assert "emotions" in cat and "ids" in cat and "families" in cat
    assert cat["docs"] == "docs/EMOTIONS.md"
    curiosity = next(e for e in cat["emotions"] if e["id"] == "curiosity")
    for key in ("when", "effects", "use_for", "coercion", "requires"):
        assert key in curiosity
    mix = mix_emotions({"curiosity": 40, "confusion": 30, "awe": 30}, simulate_feeling=False)
    assert mix["honesty"] == "computational_affect"
    assert mix["sum_weights"] == 1.0
    assert mix["primary"] == "curiosity"


def test_callers_import_emotions_not_catalog_mix():
    """Appraisal / modulate / package surface stay on emotions.py."""
    for rel in _STABLE_CALLERS:
        src = (_SRC / rel).read_text(encoding="utf-8")
        tree = ast.parse(src)
        imported: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)
        assert "artificial_emotions.emotions" in imported, rel
        assert "artificial_emotions.emotions_catalog" not in imported, rel
        assert "artificial_emotions.emotions_mix" not in imported, rel
