"""Stdlib logging helpers for Artificial Emotions.

Optional lit/LLM paths soft-fail by design — log at WARNING so operators see
swallows without crashing demos.
"""

from __future__ import annotations

import logging
from typing import Any


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a namespaced logger (``artificial_emotions…``)."""
    if name is None or name == __name__:
        return logging.getLogger("artificial_emotions")
    if name.startswith("artificial_emotions"):
        return logging.getLogger(name)
    return logging.getLogger(f"artificial_emotions.{name}")


def soft_fail(
    logger: logging.Logger, msg: str, *args: Any, exc: BaseException | None = None
) -> None:
    """Log a soft-fail (optional path) without raising."""
    if exc is not None:
        logger.warning("%s: %s", msg % args if args else msg, exc, exc_info=False)
    else:
        logger.warning(msg, *args)
