"""Wave 1 MCP Alive tools — registry, lint honesty, no explore persistence."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from artificial_emotions.agent_tools import dispatch_tool, mcp_tool_list
from artificial_emotions.dream import HONESTY_REANALYSIS
from artificial_emotions.mcp_lint import lint_tool_specs
from artificial_emotions.memory import PersistentMemory
from artificial_emotions.transfer import TRANSFER_SHIP_STATUS

_ALIVE_TOOLS = frozenset(
    {
        "memory_show",
        "memory_forget",
        "memory_reset",
        "memory_avoiding",
        "dream_reanalyze",
        "imagine_transfer",
        "list_imagination_kinds",
        "apply_imagination",
    }
)


def test_alive_tools_registered_by_name():
    names = {t["name"] for t in mcp_tool_list()}
    assert _ALIVE_TOOLS <= names


def test_alive_tool_descriptions_pass_mcp_lint():
    tools = [t for t in mcp_tool_list() if t["name"] in _ALIVE_TOOLS]
    errors = lint_tool_specs(tools)
    assert errors == [], errors


def test_list_imagination_kinds_documents_transfer_corpus_gated():
    out = dispatch_tool("list_imagination_kinds", {})
    assert out["transfer"]["generator"] in {"corpus_gated", "cut"}
    assert out["transfer"]["tool"] == "imagine_transfer"
    transfer = next(k for k in out["kinds"] if k["kind"] == "transfer")
    assert transfer["generator"] in {"corpus_gated", "cut"}
    assert transfer["entry"] == "imagine_transfer"
    assert transfer["not"] == "apply_imagination"


def test_apply_imagination_refuses_transfer_kind():
    out = dispatch_tool("apply_imagination", {"kind": "transfer", "domain": "ai", "n_return": 2})
    assert out["refused"] is True
    assert out["imagined"] == []
    assert out["confidence"] is None


def test_explore_curiosity_refuses_persist_memory_side_effect(tmp_path: Path, monkeypatch):
    mem_path = tmp_path / "mcp_should_not_write.json"
    monkeypatch.setenv("CURIOSITY_MEMORY_PATH", str(mem_path))
    monkeypatch.delenv("CURIOSITY_NO_MEMORY", raising=False)

    out = dispatch_tool(
        "explore_curiosity",
        {
            "domain": "ai",
            "steps": 2,
            "n_return": 3,
            "persist_memory": True,
            "memory_path": str(mem_path),
        },
    )
    assert out["trajectory"]["steps"]
    assert not mem_path.exists()


def test_memory_show_never_creates_file(tmp_path: Path):
    path = tmp_path / "absent_memory.json"
    assert not path.exists()
    out = dispatch_tool("memory_show", {"path": str(path)})
    assert out["created_file"] is False
    assert out["present"] is False
    assert "privacy_notice" in out
    assert not path.exists()


def test_memory_show_reads_existing(tmp_path: Path):
    path = tmp_path / "memory.json"
    mem = PersistentMemory(path=path)
    mem.encounters = {"q-seen": 3}
    mem.privacy_ack = True
    mem.save()
    out = dispatch_tool("memory_show", {"path": str(path)})
    assert out["present"] is True
    assert out["created_file"] is False
    assert out["encounters"]["q-seen"] == 3
    assert "privacy_notice" in out


def test_memory_forget_requires_confirm(tmp_path: Path):
    path = tmp_path / "memory.json"
    mem = PersistentMemory(path=path)
    mem.encounters = {"q1": 2}
    mem.privacy_ack = True
    mem.save()

    refused = dispatch_tool("memory_forget", {"what": "encounters", "path": str(path)})
    assert refused["refused"] is True
    assert refused["forgot"] is False
    assert PersistentMemory.load(path).encounters == {"q1": 2}

    ok = dispatch_tool(
        "memory_forget",
        {"what": "encounters", "confirm": True, "path": str(path)},
    )
    assert ok["forgot"] is True
    assert PersistentMemory.load(path).encounters == {}


def test_memory_reset_requires_confirm(tmp_path: Path):
    path = tmp_path / "memory.json"
    mem = PersistentMemory(path=path)
    mem.encounters = {"q1": 2}
    mem.privacy_ack = True
    mem.save()

    refused = dispatch_tool("memory_reset", {"path": str(path)})
    assert refused["refused"] is True
    assert path.exists()

    ok = dispatch_tool("memory_reset", {"confirm": True, "path": str(path)})
    assert ok["reset"] is True
    assert ok["deleted_file"] is True
    assert not path.exists()


def test_memory_avoiding_surfaces_pattern_not_motive(tmp_path: Path):
    path = tmp_path / "memory.json"
    mem = PersistentMemory(path=path)
    mem.encounters = {"avoid-me": 8, "picked": 4}
    mem.selections = {"picked": 1}
    mem.privacy_ack = True
    mem.save()

    out = dispatch_tool("memory_avoiding", {"path": str(path)})
    assert out["honesty"] == "pattern_not_motive"
    assert out["count"] >= 1
    assert any(p["question_id"] == "avoid-me" for p in out["avoiding"])
    assert out["created_file"] is False
    blob = json.dumps(out).lower()
    assert "motive" in blob


def test_dream_reanalyze_payload_not_labeled_dream(tmp_path: Path):
    path = tmp_path / "memory.json"
    mem = PersistentMemory(path=path)
    mem.privacy_ack = True
    mem.save()

    out = dispatch_tool("dream_reanalyze", {"path": str(path)})
    assert out.get("framing") == HONESTY_REANALYSIS or out.get("honesty") == HONESTY_REANALYSIS
    # Semantic labels must not call the output a dream (paths excluded).
    for key in ("kind", "framing", "note", "honesty", "reanalysis_honesty"):
        val = out.get(key)
        if isinstance(val, str):
            tokens = set(val.lower().replace("-", " ").replace("_", " ").split())
            assert "dream" not in tokens, f"{key}={val!r}"


def test_imagine_transfer_corpus_path(tmp_path: Path):
    corpus = [
        {
            "year": 1979,
            "title": "Fish oil and blood viscosity",
            "concepts": ["Fish oil", "Blood viscosity"],
        },
        {
            "year": 1976,
            "title": "Blood viscosity in Raynaud's",
            "concepts": ["Blood viscosity", "Raynaud disease"],
        },
        {
            "year": 1980,
            "title": "Erythrocyte deformability and fish oil",
            "concepts": ["Fish oil", "Erythrocyte deformability"],
        },
        {
            "year": 1981,
            "title": "Erythrocyte deformability in Raynaud's",
            "concepts": ["Erythrocyte deformability", "Raynaud disease"],
        },
    ]
    corpus_path = tmp_path / "corpus.json"
    corpus_path.write_text(json.dumps(corpus), encoding="utf-8")

    out = dispatch_tool(
        "imagine_transfer",
        {"seed": "Fish oil", "corpus": str(corpus_path)},
    )
    if TRANSFER_SHIP_STATUS != "shipped":
        assert out.get("ok") is False
        assert out.get("ship_status") == TRANSFER_SHIP_STATUS
        assert out["imagined"] == []
    else:
        assert out.get("ok") is True
        assert out.get("kind") == "transfer"
        assert out.get("confidence") is None
        assert out.get("generator") == "corpus_gated"
        # Never ranked-shaped injection keys.
        assert "questions" not in out
        assert "ranked" not in out


def test_imagine_transfer_refuses_missing_seed():
    out = dispatch_tool(
        "imagine_transfer", {"seed": "", "corpus": [{"year": 1, "concepts": ["a"]}]}
    )
    assert out["refused"] is True
    assert out["imagined"] == []


@pytest.mark.parametrize(
    "name",
    sorted(_ALIVE_TOOLS - {"list_imagination_kinds", "apply_imagination"}),
)
def test_alive_tools_dispatchable(name: str):
    """Smoke: every new tool name is in HANDLERS and callable with safe args."""
    args: dict = {}
    if name == "memory_forget":
        args = {"what": "mood", "confirm": False}
    elif name == "memory_reset":
        args = {"confirm": False}
    elif name == "imagine_transfer":
        args = {"seed": "x", "corpus": []}
    out = dispatch_tool(name, args)
    assert isinstance(out, dict)
