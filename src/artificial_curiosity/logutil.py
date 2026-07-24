"""Stdlib logging helpers for Artificial Curiosity.

Optional lit/LLM paths soft-fail by design — log at WARNING so operators see
swallows without crashing demos.
"""

from __future__ import annotations

import logging
from typing import Any


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a namespaced logger (``artificial_curiosity…``)."""
    if name is None or name == __name__:
        return logging.getLogger("artificial_curiosity")
    if name.startswith("artificial_curiosity"):
        return logging.getLogger(name)
    return logging.getLogger(f"artificial_curiosity.{name}")


def soft_fail(
    logger: logging.Logger, msg: str, *args: Any, exc: BaseException | None = None
) -> None:
    """Log a soft-fail (optional path) without raising."""
    if exc is not None:
        logger.warning("%s: %s", msg % args if args else msg, exc, exc_info=False)
    else:
        logger.warning(msg, *args)
