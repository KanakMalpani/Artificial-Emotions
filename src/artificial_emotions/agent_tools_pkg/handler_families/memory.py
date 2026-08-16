"""Memory and dream tools: show / forget / reset / avoiding / reanalyze."""

from __future__ import annotations

from typing import Any

__all__ = [
    "handle_dream_reanalyze",
    "handle_memory_avoiding",
    "handle_memory_forget",
    "handle_memory_reset",
    "handle_memory_show",
]


def handle_memory_show(
    *,
    path: str | None = None,
    **_extra: Any,
) -> dict[str, Any]:
    """Read-only dump of local memory JSON if present — never creates the file."""
    from artificial_emotions.memory import PersistentMemory, memory_disabled

    if memory_disabled():
        return {
            "disabled": True,
            "reason": "CURIOSITY_NO_MEMORY is set — no read or write",
            "created_file": False,
            "note": (
                "MCP does not persist by default. Annotation continuity — "
                "does not feel; decision aid only."
            ),
        }

    mem = PersistentMemory.load(path or None)
    exists = mem.path.is_file()
    payload = (
        mem.show()
        if exists
        else {
            "present": False,
            "path": str(mem.path),
            "privacy_notice": mem.to_dict()["privacy_notice"],
            "sessions": [],
            "encounters": {},
            "selections": {},
            "scars": [],
            "affinities": [],
            "mood_carryover": mem.mood_carryover.to_dict(),
        }
    )
    payload["present"] = exists
    payload["created_file"] = False
    payload["mcp_persists"] = False
    payload["note"] = (
        "Read-only MCP surface — never creates or writes memory.json. "
        "CLI explore may persist; MCP/HTTP do not by default. "
        "Annotation continuity — does not feel; decision aid only. "
        "Related literature ≠ answered."
    )
    return payload


def handle_memory_forget(
    *,
    what: str = "",
    confirm: bool = False,
    path: str | None = None,
    **_extra: Any,
) -> dict[str, Any]:
    """Explicit forget — requires confirm=true; still no auto-write from explore."""
    from artificial_emotions.memory import PersistentMemory, memory_disabled

    if not confirm:
        return {
            "forgot": False,
            "refused": True,
            "reason": "confirm must be true — destructive ops are explicit only",
            "note": ("MCP does not auto-persist from explore. Decision aid only — does not feel."),
        }
    if memory_disabled():
        return {
            "forgot": False,
            "disabled": True,
            "reason": "CURIOSITY_NO_MEMORY is set — no read or write",
        }

    mem = PersistentMemory.load(path or None)
    result = mem.forget(what or "")
    if result.get("forgot"):
        mem.save()
    result["mcp_persists_default"] = False
    result["note"] = (
        "Explicit forget only. Explore-style MCP tools never auto-write. "
        "Annotation continuity — does not feel; decision aid only."
    )
    return result


def handle_memory_reset(
    *,
    confirm: bool = False,
    path: str | None = None,
    **_extra: Any,
) -> dict[str, Any]:
    """Wipe remembered state + delete file — requires confirm=true."""
    from artificial_emotions.memory import PersistentMemory, memory_disabled

    if not confirm:
        return {
            "reset": False,
            "refused": True,
            "reason": "confirm must be true — destructive ops are explicit only",
            "note": ("MCP does not auto-persist from explore. Decision aid only — does not feel."),
        }
    if memory_disabled():
        return {
            "reset": False,
            "disabled": True,
            "reason": "CURIOSITY_NO_MEMORY is set — no read or write",
        }

    mem = PersistentMemory.load(path or None)
    mem.reset()
    deleted = mem.delete_file()
    return {
        "reset": True,
        "deleted_file": deleted,
        "path": str(mem.path),
        "mcp_persists_default": False,
        "note": (
            "Explicit reset only. Explore-style MCP tools never auto-write. "
            "Annotation continuity — does not feel; decision aid only."
        ),
    }


def handle_memory_avoiding(
    *,
    path: str | None = None,
    min_encounters: int | None = None,
    **_extra: Any,
) -> dict[str, Any]:
    """Surface avoidance patterns from local memory (pattern ≠ motive)."""
    from artificial_emotions.avoidance import avoiding_payload
    from artificial_emotions.memory import PersistentMemory, memory_disabled

    if memory_disabled():
        return {
            "disabled": True,
            "avoiding": [],
            "count": 0,
            "honesty": "pattern_not_motive",
            "reason": "CURIOSITY_NO_MEMORY is set — no read or write",
            "note": ("Pattern ≠ motive. Annotation only — does not feel; decision aid only."),
        }

    mem = PersistentMemory.load(path or None)
    kwargs: dict[str, Any] = {
        "encounters": mem.encounters,
        "selections": mem.selections,
    }
    if min_encounters is not None:
        kwargs["min_encounters"] = int(min_encounters)
    payload = avoiding_payload(**kwargs)
    payload["path"] = str(mem.path)
    payload["created_file"] = False
    payload["mcp_persists"] = False
    return payload


def handle_dream_reanalyze(
    *,
    path: str | None = None,
    **_extra: Any,
) -> dict[str, Any]:
    """Thin wrap of dream.reanalyze_history — offline reanalysis, not a dream."""
    from artificial_emotions.dream import HONESTY_REANALYSIS, reanalyze_history
    from artificial_emotions.memory import memory_disabled

    if memory_disabled():
        return {
            "disabled": True,
            "reason": "CURIOSITY_NO_MEMORY is set — no history to reanalyze",
            "framing": HONESTY_REANALYSIS,
            "honesty": HONESTY_REANALYSIS,
            "confidence": None,
            "note": (
                "Offline reanalysis of stored history — does not feel; "
                "decision aid only. Related literature ≠ answered."
            ),
        }

    return reanalyze_history(path=path or None)
