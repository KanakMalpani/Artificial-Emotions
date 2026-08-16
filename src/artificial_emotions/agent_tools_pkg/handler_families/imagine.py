"""Imagination tools: quarantined kinds, apply, corpus-gated transfer."""

from __future__ import annotations

from typing import Any

__all__ = [
    "handle_apply_imagination",
    "handle_imagine_transfer",
    "handle_list_imagination_kinds",
]


def handle_list_imagination_kinds(**_extra: Any) -> dict[str, Any]:
    """List imagination kinds and which generators are wired."""
    from artificial_emotions.imagine import list_imagination_kinds
    from artificial_emotions.transfer import TRANSFER_SHIP_STATUS

    payload = list_imagination_kinds()
    # Document transfer as corpus_gated — never apply_imagination.
    transfer_entry = next(
        (k for k in payload.get("kinds") or [] if k.get("kind") == "transfer"),
        None,
    )
    if transfer_entry is not None:
        transfer_entry["generator"] = "corpus_gated" if TRANSFER_SHIP_STATUS == "shipped" else "cut"
        transfer_entry["entry"] = "imagine_transfer"
        transfer_entry["not"] = "apply_imagination"
    payload["transfer"] = {
        "generator": "corpus_gated" if TRANSFER_SHIP_STATUS == "shipped" else "cut",
        "ship_status": TRANSFER_SHIP_STATUS,
        "tool": "imagine_transfer",
        "note": (
            "Transfer is corpus_gated: call imagine_transfer with seed + corpus. "
            "Never routed through apply_imagination; never ranked injection. "
            "Decision aid under quarantine — does not feel."
        ),
    }
    return payload


def handle_apply_imagination(
    *,
    kind: str,
    domain: str = "ai",
    topic: str = "",
    n_return: int = 6,
    profile_name: str | None = None,
    use_literature: bool = False,
    **_extra: Any,
) -> dict[str, Any]:
    """Rank once offline, then generate quarantined imagined content."""
    from artificial_emotions.imagine import apply_imagination
    from artificial_emotions.models import CuriosityConfig, resolve_value_profile
    from artificial_emotions.pipeline import CuriosityEngine

    key = (kind or "").strip().lower()
    if key == "transfer":
        return {
            "ok": False,
            "kind": "transfer",
            "refused": True,
            "reason": (
                "transfer is corpus_gated — use imagine_transfer with seed + corpus; "
                "never apply_imagination"
            ),
            "honesty": "imagined_not_retrieved",
            "confidence": None,
            "imagined": [],
            "note": (
                "Decision aid under quarantine — does not feel; not ranked findings. "
                "Related literature ≠ answered."
            ),
        }

    items = CuriosityEngine(
        CuriosityConfig(
            domain=domain,
            topic=topic,
            n_return=int(n_return or 6),
            use_llm=False,
            use_literature=bool(use_literature),
            value_profile=resolve_value_profile(profile_name=profile_name),
        )
    ).run()
    return apply_imagination(kind, items)


def handle_imagine_transfer(
    *,
    seed: str = "",
    corpus: Any = None,
    max_bridges: int = 4,
    max_links: int = 8,
    **_extra: Any,
) -> dict[str, Any]:
    """Corpus-gated structural transfer — refuse when ship status is not cleared."""
    from artificial_emotions.transfer import (
        TRANSFER_SHIP_STATUS,
        imagine_transfer,
    )

    seed_text = (seed or "").strip()
    if not seed_text:
        return {
            "ok": False,
            "refused": True,
            "reason": "seed is required",
            "kind": "transfer",
            "honesty": "imagined_not_retrieved",
            "confidence": None,
            "imagined": [],
            "note": (
                "Corpus-gated transfer decision aid — does not feel; "
                "never ranked injection. Related literature ≠ answered."
            ),
        }
    if corpus is None or corpus == "" or corpus == []:
        return {
            "ok": False,
            "refused": True,
            "reason": "corpus path or document list is required",
            "kind": "transfer",
            "honesty": "imagined_not_retrieved",
            "confidence": None,
            "imagined": [],
            "ship_status": TRANSFER_SHIP_STATUS,
            "note": (
                "Corpus-gated transfer decision aid — does not feel; "
                "never ranked injection. Related literature ≠ answered."
            ),
        }

    # imagine_transfer itself refuses when TRANSFER_SHIP_STATUS != "shipped".
    payload = imagine_transfer(
        seed_text,
        corpus=corpus,
        max_bridges=int(max_bridges or 4),
        max_links=int(max_links or 8),
    )
    payload.setdefault("generator", "corpus_gated")
    payload.setdefault(
        "note",
        (
            "Imagined structural analogies — not ranked, not confidence-scored. "
            "Does not feel; computational generation under quarantine. "
            "Related literature ≠ answered."
        ),
    )
    return payload
