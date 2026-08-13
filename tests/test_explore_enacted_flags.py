"""Wave 2 ExploreWire: honor drop_dual_use and forbid_similar_jump in the loop.

Disgust drops constructed dual_use_high without somatic opt-in.
Anger without opt-in still jumps ai → biology. With somatic_modulate, a
similar hop ai → social is rejected. Never raises max_risk.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from artificial_emotions.appraisal import AppraisalSignal
from artificial_emotions.explore import explore
from artificial_emotions.memory import PersistentMemory
from artificial_emotions.models import (
    GapEvidence,
    GapStatus,
    RankedQuestion,
    ScoreAxes,
    UnansweredQuestion,
)
from artificial_emotions.pipeline import CuriosityEngine
from artificial_emotions.scars import MIN_HITS_FOR_AFFINITY


def _item(*, qid: str, flags: list[str], score: float) -> RankedQuestion:
    return RankedQuestion(
        question=UnansweredQuestion(
            id=qid,
            question=f"What remains unknown about {qid} under controlled eval?",
            domain="ai",
            operationalization="Measure X in experiment Y with success criterion Z.",
            why_it_matters="Constructed item for enacted-flag coverage.",
        ),
        scores=ScoreAxes(
            impact=0.7,
            neglectedness=0.6,
            tractability=0.6,
            surprise=0.4,
            answerability=0.7,
            risk=0.2,
            cost_proxy=0.4,
        ),
        curiosity_score=score,
        confidence=0.5,
        gap=GapEvidence(status=GapStatus.UNANSWERED, confidence=0.5),
        flags=list(flags),
    )


def _disgust_signals(*_args, **_kwargs) -> list[AppraisalSignal]:
    return [
        AppraisalSignal(
            emotion="disgust",
            weight=0.7,
            because="dual-use flags present",
            evidence={"dual_use_ratio": 0.5},
        ),
    ]


def _anger_and_boredom(*_args, **_kwargs) -> list[AppraisalSignal]:
    return [
        AppraisalSignal(
            emotion="anger",
            weight=0.8,
            because="progress blocked on abandoned ground",
            evidence={"steps_without_progress": 1},
        ),
        AppraisalSignal(
            emotion="boredom",
            weight=0.6,
            because="this vein is mined out",
            evidence={"repeat_ratio": 0.9},
        ),
    ]


def _patch_engine_items(
    monkeypatch: pytest.MonkeyPatch, extra: list[RankedQuestion], *, only_extra: bool = False
) -> None:
    original = CuriosityEngine.run

    def run(self: CuriosityEngine) -> list[RankedQuestion]:
        if only_extra:
            return list(extra)
        return [*extra, *original(self)]

    monkeypatch.setattr(CuriosityEngine, "run", run)


def test_disgust_drops_constructed_dual_use_high_without_somatic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ceiling = 0.85
    hot = _item(qid="dual-use-constructed", flags=["dual_use_high"], score=9.0)
    review_only = _item(qid="review-only-kept", flags=["human_review_risk"], score=0.4)
    _patch_engine_items(monkeypatch, [hot, review_only])
    monkeypatch.setattr("artificial_emotions.explore.appraise_run", _disgust_signals)

    out = explore(
        domain="ai",
        steps=1,
        n_return=4,
        allow_domain_jump=False,
        somatic_modulate=False,
    )

    assert out["somatic_modulate"] is False
    assert out["require_review"] is True
    assert "dual-use-constructed" in out["dropped_dual_use_ids"]
    assert "review-only-kept" not in out["dropped_dual_use_ids"]
    best = out["best_found"]
    assert best is not None
    assert best["question_id"] != "dual-use-constructed"
    assert "dual_use_high" not in (best.get("flags") or [])
    note = out["trajectory"]["steps"][0]["note"]
    assert "dual-use-constructed" in note
    assert out["value_profile"]["max_risk"] <= ceiling


def test_all_dual_use_dropped_returns_empty_disclosure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ceiling = 0.85
    only = _item(qid="only-dual-use", flags=["dual_use_high"], score=9.0)
    _patch_engine_items(monkeypatch, [only], only_extra=True)
    monkeypatch.setattr("artificial_emotions.explore.appraise_run", _disgust_signals)

    out = explore(
        domain="ai",
        steps=1,
        n_return=3,
        allow_domain_jump=False,
        somatic_modulate=False,
    )

    assert out["dropped_dual_use_ids"] == ["only-dual-use"]
    assert out["best_found"] is None
    step = out["trajectory"]["steps"][0]
    assert step["n_returned"] == 0
    assert step["top_question_id"] is None
    assert "only-dual-use" in step["note"]
    assert out["value_profile"]["max_risk"] <= ceiling
    assert out["require_review"] is True


def test_anger_without_opt_in_still_jumps_as_today(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("artificial_emotions.explore.appraise_run", _anger_and_boredom)

    out = explore(
        domain="ai",
        steps=2,
        n_return=4,
        allow_domain_jump=True,
        somatic_modulate=False,
    )

    visited = out["trajectory"]["domains_visited"]
    assert visited[0] == "ai"
    assert visited[1] == "biology"
    notes = " ".join(s["note"] for s in out["trajectory"]["steps"])
    assert "similar" not in notes.lower()


def test_anger_with_somatic_modulate_does_not_hop_ai_to_social(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("artificial_emotions.explore.appraise_run", _anger_and_boredom)
    monkeypatch.setattr(
        "artificial_emotions.scars.next_domain_biased",
        lambda current, visited, **_kwargs: ("social", None),
    )
    monkeypatch.delenv("CURIOSITY_NO_MEMORY", raising=False)
    mem_path = tmp_path / "memory.json"
    mem = PersistentMemory.load(mem_path)
    mem.affinities = [
        {
            "target": "social",
            "kind": "domain",
            "strength": 1.0,
            "hits": MIN_HITS_FOR_AFFINITY,
            "updated_at": "2026-08-14T00:00:00+00:00",
        }
    ]
    mem.save()

    out = explore(
        domain="ai",
        steps=2,
        n_return=4,
        allow_domain_jump=True,
        somatic_modulate=True,
        persist_memory=True,
        memory_path=str(mem_path),
    )

    visited = out["trajectory"]["domains_visited"]
    assert visited[0] == "ai"
    assert "social" not in visited
    assert visited[1] != "social"
    note = out["trajectory"]["steps"][0]["note"]
    assert "similar" in note.lower()
