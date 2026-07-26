"""Structured errors with stable machine-readable codes.

HTTP handlers map these (and plain ``ValueError``) into a consistent JSON body::

    {"error": {"code": "unknown_emotion", "message": "...", "details": {…}}}

Codes are part of the public contract — do not rename lightly.
"""

from __future__ import annotations

from typing import Any

# Stable public error codes (API / MCP / Python).
ERR_VALIDATION = "validation_error"
ERR_UNKNOWN_EMOTION = "unknown_emotion"
ERR_UNKNOWN_FAMILY = "unknown_family"
ERR_UNKNOWN_PACK = "unknown_pack"
ERR_UNKNOWN_PROFILE = "unknown_profile"
ERR_UNKNOWN_GAP_STATUS = "unknown_gap_status"
ERR_EMPTY_MIX = "empty_mix"
ERR_NEGATIVE_WEIGHT = "negative_weight"
ERR_MIX_TOO_LARGE = "mix_too_large"
ERR_AUTH_REQUIRED = "auth_required"
ERR_NOT_FOUND = "not_found"
ERR_INTERNAL = "internal_error"
ERR_BAD_REQUEST = "bad_request"


class CuriosityError(ValueError):
    """Typed application error with a stable ``code`` (also a ``ValueError``)."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        http_status: int = 400,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details: dict[str, Any] = details or {}
        self.http_status = http_status

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.details:
            body["details"] = self.details
        return body


def error_payload(
    code: str,
    message: str,
    *,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the stable ``{"error": …}`` envelope used by HTTP handlers."""
    err: dict[str, Any] = {"code": code, "message": message}
    if details:
        err["details"] = details
    return {"error": err}


def classify_value_error(exc: ValueError) -> CuriosityError:
    """Map legacy ``ValueError`` messages to stable codes (compat bridge)."""
    if isinstance(exc, CuriosityError):
        return exc
    msg = str(exc)
    lower = msg.lower()
    # Pack check must precede the emotion check: "unknown emotion pack" contains
    # "unknown emotion", so the general branch would otherwise shadow it.
    if "unknown emotion pack" in lower or "unknown pack" in lower:
        return CuriosityError(ERR_UNKNOWN_PACK, msg)
    if "unknown emotion" in lower:
        return CuriosityError(ERR_UNKNOWN_EMOTION, msg)
    if "unknown family" in lower:
        return CuriosityError(ERR_UNKNOWN_FAMILY, msg)
    if "unknown profile" in lower or "unknown valueprofile" in lower:
        return CuriosityError(ERR_UNKNOWN_PROFILE, msg)
    if "unknown gap_status" in lower or "unknown gap status" in lower:
        return CuriosityError(ERR_UNKNOWN_GAP_STATUS, msg)
    if "empty mix" in lower or "all mix weights are zero" in lower:
        return CuriosityError(ERR_EMPTY_MIX, msg)
    if "negative weight" in lower:
        return CuriosityError(ERR_NEGATIVE_WEIGHT, msg)
    if "too many components" in lower:
        return CuriosityError(ERR_MIX_TOO_LARGE, msg)
    return CuriosityError(ERR_VALIDATION, msg)
