"""Backtest stub tests must make no network calls (QA requirement).

Autouse: any attempt to create a socket or open a connection raises.
"""

from __future__ import annotations

import enum
import importlib.util
import pathlib
import socket
import sys
import types

import pytest


def _offline_package_shim() -> None:
    """Only when pydantic is not installed (box without network, see report).

    The backtest uses only ``discover_links`` / ``LocalCorpusClient`` /
    ``gap_score``, which are pure Python. ``artificial_emotions/__init__`` and
    ``models`` pull in pydantic; this registers the package without running its
    ``__init__`` and gives ``discover`` a minimal ``models`` stand-in. With
    pydantic installed (CI), the shim is skipped and the real package is used.
    """
    if importlib.util.find_spec("pydantic") is not None or "artificial_emotions" in sys.modules:
        return
    src = pathlib.Path(__file__).resolve().parents[2] / "src" / "artificial_emotions"
    pkg = types.ModuleType("artificial_emotions")
    pkg.__path__ = [str(src)]
    sys.modules["artificial_emotions"] = pkg
    models = types.ModuleType("artificial_emotions.models")

    class Domain(str, enum.Enum):
        GENERAL = "general"

    class UnansweredQuestion:  # never constructed by the backtest
        def __init__(self, *a, **k):
            raise RuntimeError("models shim: not available offline")

    models.Domain = Domain
    models.UnansweredQuestion = UnansweredQuestion
    sys.modules["artificial_emotions.models"] = models


_offline_package_shim()


class NetworkBlocked(RuntimeError):
    pass


def _blocked(*args, **kwargs):
    raise NetworkBlocked("network access is blocked in backtest tests")


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    monkeypatch.setattr(socket, "socket", _blocked)
    monkeypatch.setattr(socket, "create_connection", _blocked)
    monkeypatch.setattr(socket, "getaddrinfo", _blocked)
    yield
