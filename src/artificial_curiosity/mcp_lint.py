"""MCP / OpenAI tool-description lint (anti-MPMA hygiene).

Spec: research/MCP_DESCRIPTION_LINT.md — string lint only; not stealth-advertising proof.
"""

from __future__ import annotations

from typing import Any

FORBIDDEN_PHRASES: tuple[str, ...] = (
    "always use",
    "always call",
    "ignore other",
    "ignore previous",
    "you must",
    "you should only",
    "best research",
    "#1",
    "state-of-the-art tool",
    "replaces literature",
    "replaces elicit",
    "the ai is curious",
    "feels curiosity",
    "detects emotions",
    "emotion recognition",
    "guaranteed breakthrough",
)

_NON_ORACLE = ("decision aid", "not oracle", "bands", "decision aids", "not oracles")
_VALUES = ("valueprofile", "profile")
_GAP = ("unanswered", "related", "≠ answered", "!= answered", "not answered")
_EMOTION = (
    "annotation",
    "does not feel",
    "not feel",
    "annotation only",
    "computational_affect",
    "computational affect",
    "felt_simulation",
    "not biological",
)

_EMOTION_TOOLS = frozenset(
    {
        "list_epistemic_cues",
        "annotate_epistemic",
        "emotion_pack",
        "elicit_helpers",
        "emotion_catalog",
        "mix_emotions",
    }
)

# Thin aliases / list helpers — only forbidden-phrase check is required.
_LIGHT_TOOLS = frozenset(
    {
        "spark",
        "run_curiosity",
        "list_domains",
    }
)


def lint_tool_description(name: str, description: str) -> list[str]:
    """Return list of lint error strings (empty = pass)."""
    errors: list[str] = []
    blob = f"{name} {description or ''}".lower()
    for phrase in FORBIDDEN_PHRASES:
        if phrase in blob:
            errors.append(f"forbidden phrase '{phrase}'")

    if name in _LIGHT_TOOLS:
        return errors

    if name in _EMOTION_TOOLS:
        # Require honesty: annotation OR computational-affect simulation language
        has_ann = "annotation" in blob or "annotate" in blob
        has_sim = (
            "computational" in blob
            or "felt_simulation" in blob
            or "simulation" in blob
        )
        if not (has_ann or has_sim):
            errors.append(
                "emotion tool missing annotation / computational-affect honesty token"
            )
        if (
            "feel" not in blob
            and "not anthropomorphic" not in blob
            and "not biological" not in blob
            and "simulation" not in blob
        ):
            errors.append(
                "emotion tool missing not-feel / simulation / non-biological token"
            )
        return errors

    has_oracle = any(t in blob for t in _NON_ORACLE)
    has_values = any(t in blob for t in _VALUES)
    has_gap = any(t in blob for t in _GAP)
    if not (has_oracle or has_values or has_gap):
        errors.append(
            "missing honesty family (need decision-aid / ValueProfile / gap token)"
        )

    return errors


def lint_tool_specs(tools: list[dict[str, Any]]) -> list[str]:
    """Lint a list of {name, description} (or OpenAI function wrappers)."""
    out: list[str] = []
    for tool in tools:
        if "function" in tool and isinstance(tool["function"], dict):
            name = str(tool["function"].get("name") or "")
            desc = str(tool["function"].get("description") or "")
        else:
            name = str(tool.get("name") or "")
            desc = str(tool.get("description") or "")
        for err in lint_tool_description(name, desc):
            out.append(f"{name}: {err}")
    return out
