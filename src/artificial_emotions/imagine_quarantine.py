"""Imagination quarantine — sealed container for invented material.

Imagination *asserts*. Every other module in this repo is forbidden from
asserting; ``decompose.assert_free`` enforces that. Quarantine is the one
place assertion is allowed to travel — which makes it the one place that
can poison the repo's credibility.

Rules, enforced by tests:

* Imagined content never shares a list key with ranked questions.
* Every payload carries ``honesty: "imagined_not_retrieved"``.
* ``confidence`` is structurally ``None`` — no number next to a fantasy.
* A one-way valve refuses ranking injection without gap verification.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from artificial_emotions.errors import ERR_VALIDATION, CuriosityError
from artificial_emotions.models import GapEvidence, GapStatus

__all__ = [
    "HONESTY_IMAGINED",
    "IMAGINED_PAYLOAD_KEY",
    "RANKED_PAYLOAD_KEYS",
    "ImaginedContent",
    "admit_imagined_as_candidate",
    "assert_imagined_safe",
    "imagined_payload",
    "refuse_ranking_injection",
]

#: Payload honesty token — every imagined surface must carry this exact string.
HONESTY_IMAGINED = "imagined_not_retrieved"

#: Dedicated key for imagined material. Never reuse ranked-result keys.
IMAGINED_PAYLOAD_KEY = "imagined"

#: Keys reserved for retrieved / ranked questions. Imagined content must not
#: appear under any of these.
RANKED_PAYLOAD_KEYS = frozenset(
    {
        "ranked",
        "items",
        "results",
        "questions",
        "ranking",
        "candidates",
        "top",
        "most_suspect_first",
        "by_risk",
        "by_novelty_pull",
        "by_crowding",
        "worst_formed_first",
        "stop_doing",
    }
)

#: Statuses that count as "gap verification actually ran".
#: ``UNKNOWN_WITH_CAVEAT`` alone is not enough when literature was skipped.
_VERIFIED_GAP_STATUSES = frozenset(
    {
        GapStatus.UNANSWERED,
        GapStatus.PARTIALLY_ANSWERED,
        GapStatus.LIKELY_ANSWERED,
    }
)


@dataclass(frozen=True)
class ImaginedContent:
    """One sealed imagined artefact. Generators emit only this type.

    ``confidence`` is typed as ``None`` and re-checked in ``__post_init__`` so a
    subclass or ``object.__setattr__`` mutation cannot attach a score.
    """

    content: str
    kind: str
    driven_by: tuple[str, ...]
    grounded_in: tuple[str, ...] = ()
    invented: tuple[str, ...] = ()
    status: str = "imagined"
    confidence: None = None

    def __post_init__(self) -> None:
        if self.status != "imagined":
            raise CuriosityError(
                ERR_VALIDATION,
                f"ImaginedContent.status must be 'imagined', got {self.status!r}",
                details={"status": self.status},
            )
        if self.confidence is not None:
            raise CuriosityError(
                ERR_VALIDATION,
                "ImaginedContent.confidence is structurally None — "
                "imagination does not get a score",
                details={"confidence": self.confidence},
            )
        if not (self.content or "").strip():
            raise CuriosityError(
                ERR_VALIDATION,
                "ImaginedContent.content must be non-empty",
            )
        kind = (self.kind or "").strip().lower()
        if not kind:
            raise CuriosityError(
                ERR_VALIDATION,
                "ImaginedContent.kind must be non-empty",
            )
        object.__setattr__(self, "kind", kind)

    def to_dict(self) -> dict[str, Any]:
        """Serialize with confidence explicitly null and status fixed."""
        return {
            "content": self.content,
            "kind": self.kind,
            "driven_by": list(self.driven_by),
            "grounded_in": list(self.grounded_in),
            "invented": list(self.invented),
            "status": "imagined",
            "confidence": None,
        }


def imagined_payload(
    content: ImaginedContent | list[ImaginedContent],
    *,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Wrap imagined material under the quarantine key.

    Ranked questions must never share this list. Callers that also have a
    ranking should place it under a separate key (``ranked`` / ``items``), not
    merge the lists.
    """
    items = content if isinstance(content, list) else [content]
    for item in items:
        if not isinstance(item, ImaginedContent):
            raise CuriosityError(
                ERR_VALIDATION,
                "imagined_payload accepts only ImaginedContent instances",
                details={"got": type(item).__name__},
            )
    payload: dict[str, Any] = {
        IMAGINED_PAYLOAD_KEY: [item.to_dict() for item in items],
        "honesty": HONESTY_IMAGINED,
        "confidence": None,
        "claims_not": [
            "retrieved literature",
            "a ranked finding",
            "a confidence-scored claim",
            "phenomenal feeling or lived experience",
        ],
        "docs": "docs/PLAN_ALIVE.md",
    }
    if extra:
        # Refuse attempts to smuggle ranked keys or override honesty/confidence.
        for key in extra:
            if key in RANKED_PAYLOAD_KEYS:
                raise CuriosityError(
                    ERR_VALIDATION,
                    f"Cannot attach ranked key {key!r} to an imagined payload",
                    details={"key": key},
                )
            if key in ("honesty", "confidence", IMAGINED_PAYLOAD_KEY):
                raise CuriosityError(
                    ERR_VALIDATION,
                    f"Cannot override quarantine field {key!r}",
                    details={"key": key},
                )
        payload.update(extra)
    ok, offenders = assert_imagined_safe(payload)
    if not ok:
        raise CuriosityError(
            ERR_VALIDATION,
            "imagined payload failed quarantine checks",
            details={"offenders": offenders},
        )
    return payload


def assert_imagined_safe(payload: dict[str, Any]) -> tuple[bool, list[str]]:
    """Return ``(ok, offenders)`` — imagined material must stay marked and sealed.

    Checks:
    * ``honesty`` is exactly ``imagined_not_retrieved`` when imagined content
      is present
    * top-level ``confidence`` is ``None``
    * no imagined entry carries a numeric confidence
    * imagined entries are not nested under ranked-result keys
    * every imagined entry has ``status == "imagined"``
    """
    offenders: list[str] = []
    if not isinstance(payload, dict):
        return False, ["payload is not a dict"]

    imagined_nodes = _collect_imagined_nodes(payload)

    if imagined_nodes:
        honesty = payload.get("honesty")
        if honesty != HONESTY_IMAGINED:
            offenders.append(
                f"$.honesty must be {HONESTY_IMAGINED!r} when imagined content "
                f"is present (got {honesty!r})"
            )

    if "confidence" in payload and payload["confidence"] is not None:
        offenders.append("$.confidence must be None on imagined payloads")

    for path, node in imagined_nodes:
        if isinstance(node, dict):
            if node.get("status") != "imagined":
                offenders.append(f"{path}.status must be 'imagined'")
            if "confidence" in node and node["confidence"] is not None:
                offenders.append(f"{path}.confidence must be None")
            if node.get("honesty") not in (None, HONESTY_IMAGINED):
                offenders.append(f"{path}.honesty must be {HONESTY_IMAGINED!r} or omitted")
        elif isinstance(node, ImaginedContent):
            if node.confidence is not None:
                offenders.append(f"{path}.confidence must be None")
            if node.status != "imagined":
                offenders.append(f"{path}.status must be 'imagined'")

    for key in RANKED_PAYLOAD_KEYS:
        if key not in payload:
            continue
        bucket = payload[key]
        if _bucket_contains_imagined(bucket):
            offenders.append(
                f"$.{key} contains imagined content — use {IMAGINED_PAYLOAD_KEY!r} instead"
            )

    return (not offenders), offenders


def refuse_ranking_injection(
    imagined: ImaginedContent,
    ranking: list[Any],
    *,
    gap_verified: bool = False,
    gap_evidence: GapEvidence | None = None,
) -> list[Any]:
    """One-way valve: imagined content cannot enter a ranking list.

    Without gap verification this always raises. With verification, B1 still
    refuses *ranking* injection — verified imagined material may only become a
    candidate via ``admit_imagined_as_candidate``. Mutations that drop the
    ``gap_verified`` check must turn CI red.
    """
    if not isinstance(imagined, ImaginedContent):
        raise CuriosityError(
            ERR_VALIDATION,
            "refuse_ranking_injection requires ImaginedContent",
            details={"got": type(imagined).__name__},
        )

    verified = gap_verified and _gap_verification_holds(gap_evidence)
    if not verified:
        raise CuriosityError(
            ERR_VALIDATION,
            "Imagined content cannot enter ranking without gap verification",
            details={
                "honesty": HONESTY_IMAGINED,
                "kind": imagined.kind,
                "gap_verified": gap_verified,
                "gap_status": (gap_evidence.status.value if gap_evidence is not None else None),
                "valve": "refuse_ranking_injection",
            },
        )

    # Verified still does not mean "drop into the ranked list". Ranking is for
    # retrieved candidates only; imagination stays quarantined.
    raise CuriosityError(
        ERR_VALIDATION,
        "Imagined content cannot be injected into a ranking list — "
        "convert via admit_imagined_as_candidate after gap verification",
        details={
            "honesty": HONESTY_IMAGINED,
            "kind": imagined.kind,
            "valve": "refuse_ranking_injection",
            "ranking_len": len(ranking),
        },
    )


def admit_imagined_as_candidate(
    imagined: ImaginedContent,
    *,
    gap_verified: bool = False,
    gap_evidence: GapEvidence | None = None,
) -> dict[str, Any]:
    """Admit imagined material as a *candidate* only after gap verification.

    Returns a marked candidate stub (not a ``RankedQuestion``). Without
    verification this raises — the same gate ``refuse_ranking_injection`` uses.
    """
    if not isinstance(imagined, ImaginedContent):
        raise CuriosityError(
            ERR_VALIDATION,
            "admit_imagined_as_candidate requires ImaginedContent",
            details={"got": type(imagined).__name__},
        )

    verified = gap_verified and _gap_verification_holds(gap_evidence)
    if not verified:
        raise CuriosityError(
            ERR_VALIDATION,
            "Imagined content cannot become a candidate without gap verification",
            details={
                "honesty": HONESTY_IMAGINED,
                "kind": imagined.kind,
                "gap_verified": gap_verified,
                "gap_status": (gap_evidence.status.value if gap_evidence is not None else None),
                "valve": "admit_imagined_as_candidate",
            },
        )

    return {
        "candidate_from": "imagined",
        "source_kind": imagined.kind,
        "content": imagined.content,
        "grounded_in": list(imagined.grounded_in),
        "invented": list(imagined.invented),
        "driven_by": list(imagined.driven_by),
        "status": "candidate_pending_rank",
        "confidence": None,
        "honesty": HONESTY_IMAGINED,
        "gap": gap_evidence.model_dump() if gap_evidence is not None else None,
        "claims_not": [
            "a ranked finding",
            "retrieved literature presented as imagined",
            "a confidence score",
        ],
    }


def _gap_verification_holds(gap_evidence: GapEvidence | None) -> bool:
    """True only when real gap evidence shows verification ran."""
    if gap_evidence is None:
        return False
    status = gap_evidence.status
    if isinstance(status, str):
        try:
            status = GapStatus(status)
        except ValueError:
            return False
    return status in _VERIFIED_GAP_STATUSES


def _collect_imagined_nodes(payload: dict[str, Any]) -> list[tuple[str, Any]]:
    """Find imagined entries under the quarantine key or typed instances."""
    found: list[tuple[str, Any]] = []
    bucket = payload.get(IMAGINED_PAYLOAD_KEY)
    if isinstance(bucket, list):
        for i, item in enumerate(bucket):
            found.append((f"$.{IMAGINED_PAYLOAD_KEY}[{i}]", item))
    elif bucket is not None:
        found.append((f"$.{IMAGINED_PAYLOAD_KEY}", bucket))

    def walk(node: Any, path: str) -> None:
        if isinstance(node, ImaginedContent):
            found.append((path, node))
        elif isinstance(node, dict):
            if node.get("status") == "imagined" and path != "$":
                # Avoid double-counting the quarantine list entries.
                if not path.startswith(f"$.{IMAGINED_PAYLOAD_KEY}"):
                    found.append((path, node))
            for k, v in node.items():
                walk(v, f"{path}.{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]")

    walk(payload, "$")
    # De-dupe by path while preserving order.
    seen: set[str] = set()
    unique: list[tuple[str, Any]] = []
    for path, node in found:
        if path in seen:
            continue
        seen.add(path)
        unique.append((path, node))
    return unique


def _bucket_contains_imagined(bucket: Any) -> bool:
    if isinstance(bucket, ImaginedContent):
        return True
    if isinstance(bucket, dict):
        if bucket.get("status") == "imagined":
            return True
        return any(_bucket_contains_imagined(v) for v in bucket.values())
    if isinstance(bucket, list):
        return any(_bucket_contains_imagined(v) for v in bucket)
    return False
