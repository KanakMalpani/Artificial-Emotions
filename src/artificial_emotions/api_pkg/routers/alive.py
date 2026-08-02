"""Alive continuity surfaces: imagination, memory, dream, transfer.

HTTP defaults match MCP/library: no auto-persist memory. GET /v1/memory is
read-only (never creates the file). Destructive memory ops and dream reanalysis
require explicit POST. Transfer is corpus-gated — never via GET /{kind}.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query

from artificial_emotions.api_pkg.schemas import (
    DreamRequest,
    MemoryForgetRequest,
    MemoryIntentRequest,
    MemoryResetRequest,
    TransferImaginationRequest,
    safe_profile,
)
from artificial_emotions.errors import ERR_VALIDATION, CuriosityError
from artificial_emotions.models import CuriosityConfig
from artificial_emotions.pipeline import CuriosityEngine

router = APIRouter()

_MEMORY_OPT_OUT = (
    "HTTP never auto-persists memory (same as MCP/library). "
    "Opt out of all read/write: CURIOSITY_NO_MEMORY=1. "
    "CLI explore may persist; see docs/LIMITS.md."
)


# --- imagination --------------------------------------------------------------------


@router.get("/v1/imagination")
def list_imagination_route() -> dict[str, Any]:
    """List imagination kinds, wired generators, and transfer ship status."""
    from artificial_emotions.imagine import list_imagination_kinds
    from artificial_emotions.transfer import TRANSFER_GATE_NOTE, TRANSFER_SHIP_STATUS

    payload = list_imagination_kinds()
    payload["transfer"] = {
        "ship_status": TRANSFER_SHIP_STATUS,
        "gate_note": TRANSFER_GATE_NOTE,
        "method": "POST",
        "path": "/v1/imagination/transfer",
        "note": (
            "Corpus-gated structural analogy — not available via "
            "GET /v1/imagination/{kind}. Seed + local corpus only; offline."
        ),
    }
    return payload


@router.post("/v1/imagination/transfer")
def imagination_transfer_route(req: TransferImaginationRequest) -> dict[str, Any]:
    """Corpus-gated analogical transfer. Never ranks; never uses GET /{kind}."""
    from artificial_emotions.transfer import imagine_transfer

    corpus = _resolve_transfer_corpus(req)
    return imagine_transfer(
        req.seed,
        corpus=corpus,
        max_bridges=req.max_bridges,
        max_links=req.max_links,
        cooccurrence_ceiling=req.cooccurrence_ceiling,
    )


@router.get("/v1/imagination/{kind}")
def apply_imagination_route(
    kind: str,
    domain: str = Query("ai"),
    topic: str = Query(""),
    n: int = Query(6, ge=1, le=16),
    profile_name: str | None = Query(None),
    use_literature: bool = Query(False),
) -> dict[str, Any]:
    """Rank once, then run a wired imagination generator over the result.

    Stubs and ``transfer`` return 400 — transfer is POST /v1/imagination/transfer.
    """
    key = (kind or "").strip().lower()
    if key == "transfer":
        raise CuriosityError(
            ERR_VALIDATION,
            (
                "Imagination kind 'transfer' is corpus-gated. "
                "POST /v1/imagination/transfer with seed + corpus "
                "(path, JSON text, or documents) — not GET /v1/imagination/transfer."
            ),
            details={
                "kind": "transfer",
                "path": "POST /v1/imagination/transfer",
            },
        )

    from artificial_emotions.imagine import apply_imagination

    items = CuriosityEngine(
        CuriosityConfig(
            domain=domain,
            topic=topic,
            n_return=n,
            use_llm=False,
            use_literature=use_literature,
            value_profile=safe_profile(None, profile_name),
        )
    ).run()
    return apply_imagination(kind, items)


def _resolve_transfer_corpus(
    req: TransferImaginationRequest,
) -> str | Path | list[dict[str, Any]]:
    if req.corpus is not None:
        return list(req.corpus)
    if req.corpus_text is not None and str(req.corpus_text).strip():
        try:
            docs = json.loads(req.corpus_text)
        except json.JSONDecodeError as exc:
            raise CuriosityError(
                ERR_VALIDATION,
                "corpus_text must be JSON (a list of documents)",
                details={"error": str(exc)},
            ) from exc
        if not isinstance(docs, list):
            raise CuriosityError(
                ERR_VALIDATION,
                "corpus_text must decode to a list of documents",
            )
        return docs
    if req.corpus_path is not None and str(req.corpus_path).strip():
        # Local/trusted use — same as CLI. Agents should prefer inline corpus.
        return Path(str(req.corpus_path).strip()).expanduser()
    raise CuriosityError(
        ERR_VALIDATION,
        "Provide corpus (documents), corpus_text (JSON), or corpus_path",
        details={"fields": ["corpus", "corpus_text", "corpus_path"]},
    )


# --- memory -------------------------------------------------------------------------


@router.get("/v1/memory")
def memory_show_route(
    path: str | None = Query(
        None,
        description="Optional local memory JSON path (tests / local). Never creates the file.",
    ),
) -> dict[str, Any]:
    """Read-only dump of local memory JSON if present. Never writes or creates."""
    from artificial_emotions.memory import (
        ENV_NO_MEMORY,
        PersistentMemory,
        default_memory_path,
        memory_disabled,
    )

    if memory_disabled():
        return {
            "disabled": True,
            "reason": f"{ENV_NO_MEMORY} is set — no read or write",
            "env": ENV_NO_MEMORY,
            "path": str(Path(path).expanduser() if path else default_memory_path()),
            "privacy": _MEMORY_OPT_OUT,
            "note": "GET /v1/memory never persists. HTTP/library defaults: no auto-write.",
        }

    mem = PersistentMemory.load(path)
    payload = mem.show()
    payload["disabled"] = False
    payload["env_opt_out"] = ENV_NO_MEMORY
    payload["wrote"] = False
    payload["privacy"] = _MEMORY_OPT_OUT
    payload["note"] = (
        "Read-only. GET never creates or updates the memory file. "
        "Destructive ops: POST /v1/memory/forget|reset. "
        "Avoidance patterns: POST /v1/memory/avoiding. " + _MEMORY_OPT_OUT
    )
    return payload


@router.post("/v1/memory/forget")
def memory_forget_route(req: MemoryForgetRequest) -> dict[str, Any]:
    """Explicit forget — requires confirm=true. Writes only when something matched."""
    from artificial_emotions.memory import ENV_NO_MEMORY, PersistentMemory, memory_disabled

    if memory_disabled():
        return {
            "disabled": True,
            "forgot": False,
            "reason": f"{ENV_NO_MEMORY} is set — no read or write",
            "env": ENV_NO_MEMORY,
        }
    if not req.confirm:
        raise CuriosityError(
            ERR_VALIDATION,
            "forget requires confirm=true (explicit intent)",
            details={"confirm": False},
        )

    mem = PersistentMemory.load(req.path)
    result = mem.forget(req.what)
    wrote = False
    if result.get("forgot"):
        wrote = bool(mem.save())
    result["wrote"] = wrote
    result["path"] = str(mem.path)
    result["privacy"] = _MEMORY_OPT_OUT
    return result


@router.post("/v1/memory/reset")
def memory_reset_route(req: MemoryResetRequest) -> dict[str, Any]:
    """Wipe remembered state and delete the file — requires confirm=true."""
    from artificial_emotions.memory import ENV_NO_MEMORY, PersistentMemory, memory_disabled

    if memory_disabled():
        return {
            "disabled": True,
            "reset": False,
            "reason": f"{ENV_NO_MEMORY} is set — no read or write",
            "env": ENV_NO_MEMORY,
        }
    if not req.confirm:
        raise CuriosityError(
            ERR_VALIDATION,
            "reset requires confirm=true (explicit intent)",
            details={"confirm": False},
        )

    mem = PersistentMemory.load(req.path)
    mem.reset()
    deleted = mem.delete_file()
    return {
        "reset": True,
        "deleted_file": deleted,
        "path": str(mem.path),
        "wrote": False,
        "privacy": _MEMORY_OPT_OUT,
        "note": "Memory wiped. HTTP still does not auto-persist on explore.",
    }


@router.post("/v1/memory/avoiding")
def memory_avoiding_route(req: MemoryIntentRequest) -> dict[str, Any]:
    """Surface persistent non-selection patterns (pattern ≠ motive). Read-only."""
    from artificial_emotions.avoidance import avoiding_payload
    from artificial_emotions.memory import ENV_NO_MEMORY, PersistentMemory, memory_disabled

    if memory_disabled():
        return {
            "disabled": True,
            "avoiding": [],
            "count": 0,
            "reason": f"{ENV_NO_MEMORY} is set — no read or write",
            "env": ENV_NO_MEMORY,
            "privacy": _MEMORY_OPT_OUT,
        }

    mem = PersistentMemory.load(req.path)
    payload = avoiding_payload(
        encounters=mem.encounters,
        selections=mem.selections,
    )
    payload["disabled"] = False
    payload["wrote"] = False
    payload["path"] = str(mem.path)
    payload["privacy"] = _MEMORY_OPT_OUT
    payload["intent"] = "avoiding"
    return payload


# --- dream --------------------------------------------------------------------------


@router.post("/v1/dream")
def dream_reanalyze_route(req: DreamRequest) -> dict[str, Any]:
    """Explicit offline reanalysis of stored history — never automatic."""
    from artificial_emotions.dream import HONESTY_REANALYSIS, reanalyze_history
    from artificial_emotions.memory import ENV_NO_MEMORY, memory_disabled

    if memory_disabled():
        return {
            "disabled": True,
            "reason": f"{ENV_NO_MEMORY} is set — no history to reanalyze",
            "env": ENV_NO_MEMORY,
            "framing": HONESTY_REANALYSIS,
            "wrote": False,
            "note": (
                "Explicit POST only — not a background dream. "
                "Payload framing is offline reanalysis, not evidence of dreaming."
            ),
        }

    payload = reanalyze_history(path=req.path)
    payload["wrote"] = False
    payload["intent"] = "reanalyze"
    payload.setdefault(
        "note",
        (
            "Offline reanalysis of stored history on explicit POST. "
            "Not a dream, not background, invents no literature."
        ),
    )
    return payload
