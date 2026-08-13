"""Trajectory: what this session has already looked at.

Without a past there is no boredom, because boredom requires having already
looked. There is also no being *drawn back* to what surprised you, because that
requires remembering the surprise.

This is the memory the appraisal layer reads to distinguish "a fresh open gap"
from "the third pass over the same ground". It is deliberately small: ids seen,
vocabulary mined, dead ends hit, surprises worth returning to.

In-process and serialisable. No database, no network.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from artificial_emotions.models import GapStatus, RankedQuestion

__all__ = ["Trajectory", "TrajectoryStep", "question_terms"]

_STOPWORDS = frozenset(
    """
    a an the of to in on for by with and or if is are was were be do does did what which how why
    when where who can could should would will may might must under over into from at as that this
    these those it its their there here than then most more less least much many any all some each
    every no not
    """.split()
)


def question_terms(text: str, *, limit: int = 8) -> list[str]:
    """Content words used to measure how mined a vein of questions already is."""
    out: list[str] = []
    for w in re.findall(r"[A-Za-z][A-Za-z0-9\-]+", text or ""):
        lw = w.lower()
        if lw in _STOPWORDS or len(lw) < 4:
            continue
        if lw not in out:
            out.append(lw)
        if len(out) >= limit:
            break
    return out


@dataclass
class TrajectoryStep:
    """One completed step of an exploration."""

    step: int
    domain: str
    topic: str
    n_returned: int
    top_question_id: str | None
    top_question: str
    top_score: float
    new_question_ids: list[str] = field(default_factory=list)
    appraisal: list[dict[str, Any]] = field(default_factory=list)
    modulation: list[dict[str, Any]] = field(default_factory=list)
    costs: list[dict[str, Any]] = field(default_factory=list)
    primary_feeling: str = ""
    ambivalence: float = 0.0
    made_progress: bool = True
    note: str = ""
    claims: list[str] = field(default_factory=list)
    because: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "step": self.step,
            "domain": self.domain,
            "topic": self.topic,
            "n_returned": self.n_returned,
            "top_question_id": self.top_question_id,
            "top_question": self.top_question,
            "top_score": round(float(self.top_score), 4),
            "new_question_ids": list(self.new_question_ids),
            "primary_feeling": self.primary_feeling,
            "ambivalence": round(float(self.ambivalence), 4),
            "appraisal": list(self.appraisal),
            "modulation": list(self.modulation),
            "costs": list(self.costs),
            "made_progress": self.made_progress,
            "note": self.note,
            "claims": list(self.claims),
            "because": self.because,
        }


@dataclass
class Trajectory:
    """Everything this exploration has seen so far."""

    steps: list[TrajectoryStep] = field(default_factory=list)
    seen_question_ids: set[str] = field(default_factory=set)
    term_counts: dict[str, int] = field(default_factory=dict)
    dead_ends: list[str] = field(default_factory=list)
    surprises: list[dict[str, Any]] = field(default_factory=list)
    domains_visited: list[str] = field(default_factory=list)

    # --- reads used by appraisal / modulation ---------------------------------

    def term_saturation(self, terms: list[str]) -> float:
        """0..1 — how much of this vocabulary has already been mined.

        1.0 means every content word has been seen before; 0.0 means the run is
        entirely new ground.
        """
        if not terms:
            return 0.0
        repeated = sum(1 for t in terms if self.term_counts.get(t, 0) > 0)
        return repeated / len(terms)

    def steps_without_progress(self) -> int:
        """Consecutive trailing steps that surfaced nothing new."""
        count = 0
        for step in reversed(self.steps):
            if step.made_progress:
                break
            count += 1
        return count

    def is_exhausted(self, *, threshold: int = 3) -> bool:
        return self.steps_without_progress() >= threshold

    # --- write ----------------------------------------------------------------

    def observe(self, items: list[RankedQuestion]) -> list[str]:
        """Fold a run into memory. Returns the ids that were new."""
        new_ids: list[str] = []
        for item in items:
            qid = item.question.id
            if qid not in self.seen_question_ids:
                new_ids.append(qid)
                self.seen_question_ids.add(qid)
            for term in question_terms(item.question.question):
                self.term_counts[term] = self.term_counts.get(term, 0) + 1
            if item.gap.status == GapStatus.LIKELY_ANSWERED or "gate_failed" in (item.flags or []):
                if qid not in self.dead_ends:
                    self.dead_ends.append(qid)
            if item.scores.surprise >= 0.6 and item.gap.status != GapStatus.LIKELY_ANSWERED:
                self.surprises.append(
                    {
                        "question_id": qid,
                        "question": item.question.question,
                        "surprise": round(float(item.scores.surprise), 4),
                    }
                )
        return new_ids

    def record(self, step: TrajectoryStep) -> None:
        self.steps.append(step)
        if step.domain and step.domain not in self.domains_visited:
            self.domains_visited.append(step.domain)

    # --- output ---------------------------------------------------------------

    def most_surprising(self) -> dict[str, Any] | None:
        """The strongest surprise worth returning to."""
        if not self.surprises:
            return None
        return max(self.surprises, key=lambda s: s["surprise"])

    def mined_terms(self, *, top: int = 10) -> list[dict[str, Any]]:
        ordered = sorted(self.term_counts.items(), key=lambda kv: (-kv[1], kv[0]))
        return [{"term": t, "seen": c} for t, c in ordered[:top]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "n_steps": len(self.steps),
            "steps": [s.to_dict() for s in self.steps],
            "questions_seen": len(self.seen_question_ids),
            "domains_visited": list(self.domains_visited),
            "dead_ends": list(self.dead_ends),
            "most_surprising": self.most_surprising(),
            "mined_terms": self.mined_terms(),
            "steps_without_progress": self.steps_without_progress(),
            "note": (
                "Session memory only — nothing persists between processes unless "
                "PersistentMemory is enabled (CLI explore; opt-out "
                "CURIOSITY_NO_MEMORY=1). Not a model of the field, and not "
                "evidence that anything here was answered."
            ),
        }
