"""B5 Dream — offline reanalysis of stored PersistentMemory history.

Explicit ``emotions dream`` only. Never automatic, never background.
Invented no new literature; payload must not call the output a dream.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from artificial_emotions.cli import main
from artificial_emotions.dream import (
    HONESTY_REANALYSIS,
    KIND_REANALYSIS,
    dream_claims_not,
    reanalyze_history,
)
from artificial_emotions.imagine import HONESTY_IMAGINED, IMAGINED_PAYLOAD_KEY, assert_imagined_safe
from artificial_emotions.memory import PersistentMemory


@pytest.fixture
def mem_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "memory.json"
    monkeypatch.setenv("CURIOSITY_MEMORY_PATH", str(path))
    monkeypatch.delenv("CURIOSITY_NO_MEMORY", raising=False)
    return path


def _seed_history(mem: PersistentMemory) -> PersistentMemory:
    """Two unconnected sessions sharing a term; recurring dead end; stale scar."""
    mem.record_session(
        domain="ai",
        topic="sandbagging evaluation protocols",
        session_id="s_ai",
        question_ids=["ai-dead-01", "ai-other"],
        best_question_id="ai-other",
        stopped_because="hit a dead end",
        dead_ends=["ai-dead-01"],
        terms=["sandbagging", "evaluation", "protocols"],
        steps_taken=3,
        primary_feeling="frustration",
    )
    mem.record_session(
        domain="biology",
        topic="sandbagging markers in aging assays",
        session_id="s_bio",
        question_ids=["bio-01", "bio-dead-01"],
        best_question_id="bio-01",
        stopped_because="hit a dead end",
        dead_ends=["bio-dead-01", "ai-dead-01"],
        terms=["sandbagging", "markers", "aging"],
        steps_taken=2,
        primary_feeling="curiosity",
    )
    # Third session so ai-dead-01 recurs without sharing bio's domain/questions.
    mem.record_session(
        domain="ai",
        topic="eval harness failure modes",
        session_id="s_ai2",
        question_ids=["ai-dead-01", "ai-pick"],
        best_question_id="ai-pick",
        stopped_because="hit a dead end",
        dead_ends=["ai-dead-01"],
        terms=["harness", "failure"],
        steps_taken=2,
        primary_feeling="frustration",
    )
    # Scar on biology that later paid off — mismatched.
    mem.scars = [
        {
            "target": "biology",
            "kind": "domain",
            "hits": 3,
            "strength": 0.8,
            "updated_at": "2020-01-01T00:00:00+00:00",
        }
    ]
    mem.affinities = [
        {
            "target": "biology",
            "kind": "domain",
            "hits": 2,
            "strength": 0.5,
            "updated_at": "2026-07-01T00:00:00+00:00",
        }
    ]
    return mem


def test_dream_only_reads_stored_history_and_invents_no_new_literature(
    mem_path: Path,
) -> None:
    """Must-pass B5: reanalysis cites only memory contents; no new literature."""
    mem = PersistentMemory.load(mem_path)
    _seed_history(mem)
    mem.save()

    before = json.loads(mem_path.read_text(encoding="utf-8"))
    payload = reanalyze_history(PersistentMemory.load(mem_path))

    # Read-only — disk unchanged.
    after = json.loads(mem_path.read_text(encoding="utf-8"))
    assert after == before

    # Honest framing: offline reanalysis, not a dream in the payload.
    framing = payload.get("framing") or payload.get("reanalysis_honesty")
    assert framing == HONESTY_REANALYSIS
    assert payload.get("offline") is True
    assert payload.get("network") is False
    assert payload.get("automatic") is False
    assert payload.get("background") is False

    blob = json.dumps(payload)
    # Payload must not label output as a dream (claims_not may deny it).
    for path_key in ("kind", "status", "framing", "note"):
        val = payload.get(path_key)
        if isinstance(val, str):
            tokens = set(val.lower().replace("-", " ").split())
            assert "dream" not in tokens or "not" in val.lower()

    # Quarantine when generative.
    imagined = payload.get(IMAGINED_PAYLOAD_KEY) or []
    assert imagined, "expected generative synthesis under quarantine"
    for entry in imagined:
        assert entry["kind"] == KIND_REANALYSIS
        assert entry["kind"] != "dream"
        assert entry["status"] == "imagined"
        assert entry["confidence"] is None
        assert "dream" not in entry["content"].lower().split()
    assert payload["honesty"] in (HONESTY_IMAGINED, HONESTY_REANALYSIS)
    ok, offenders = assert_imagined_safe(payload)
    assert ok, offenders

    # Findings only reference stored ids / terms.
    findings = (payload.get("analysis") or {}).get("findings") or []
    assert findings
    types = {f["type"] for f in findings}
    assert "recurring_dead_end" in types
    assert "cross_session_term" in types
    assert "mismatched_scar" in types

    stored_ids = {
        "ai-dead-01",
        "ai-other",
        "bio-01",
        "bio-dead-01",
        "ai-pick",
        "biology",
        "sandbagging",
    }
    term_findings = [f for f in findings if f.get("type") == "cross_session_term"]
    assert any(f.get("term") == "sandbagging" for f in term_findings)
    for f in findings:
        if "question_id" in f:
            assert f["question_id"] in stored_ids or f["question_id"] in (
                before.get("encounters") or {}
            )
        if "term" in f:
            # Term must come from stored topic / mined terms / id tokens.
            assert isinstance(f["term"], str) and f["term"]
        if "target" in f:
            assert f["target"] == "biology"

    # No literature invented — no DOI / arxiv / et al. / journal markers.
    lowered = blob.lower()
    for marker in (
        "arxiv.org",
        "doi.org",
        "doi:",
        "et al.",
        "proceedings of",
        "journal of",
        "isbn",
        "pmid:",
    ):
        assert marker not in lowered

    # Does not invent question ids absent from memory.
    assert "brand-new-paper-2026" not in blob
    assert "Invented Study on Quantum Empathy" not in blob

    for claim in dream_claims_not():
        assert claim in (payload.get("claims_not") or [])


def test_dream_cli_says_dream_once_payload_does_not(mem_path: Path, capsys) -> None:
    mem = PersistentMemory.load(mem_path)
    _seed_history(mem)
    mem.save()

    assert main(["dream", "--path", str(mem_path)]) == 0
    out = capsys.readouterr().out
    assert out.lower().startswith("dream")
    assert "offline reanalysis" in out.lower()
    # Only the banner line may use the word.
    assert out.lower().count("dream") == 1

    assert main(["dream", "--path", str(mem_path), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    from artificial_emotions.dream import _dream_label_offenders

    # claims_not may deny being a dream; everything else must stay clean.
    assert _dream_label_offenders(payload) == []
    assert payload.get("kind") == KIND_REANALYSIS
    assert payload["analysis"]["findings"]


def test_dream_never_runs_without_explicit_command(mem_path: Path) -> None:
    """Explore / memory show must not invoke reanalysis."""
    from artificial_emotions import dream as dream_mod

    calls: list[int] = []
    real = dream_mod.reanalyze_history

    def spy(*args, **kwargs):
        calls.append(1)
        return real(*args, **kwargs)

    dream_mod.reanalyze_history = spy  # type: ignore[assignment]
    try:
        mem = PersistentMemory.load(mem_path)
        _seed_history(mem)
        mem.save()
        # Memory show is not dream.
        assert main(["memory", "show", "--path", str(mem_path), "--json"]) == 0
        assert calls == []
    finally:
        dream_mod.reanalyze_history = real  # type: ignore[assignment]


def test_dream_empty_memory_is_honest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "empty.json"
    monkeypatch.setenv("CURIOSITY_MEMORY_PATH", str(path))
    monkeypatch.delenv("CURIOSITY_NO_MEMORY", raising=False)
    payload = reanalyze_history(PersistentMemory.load(path))
    assert payload["analysis"]["findings"] == []
    assert payload["honesty"] == HONESTY_REANALYSIS
    assert payload["automatic"] is False
    assert payload["background"] is False
