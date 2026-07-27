"""Retrospective validation: does the discovery method actually find anything?

Every other check in this repo asks whether the code behaves as written. This
one asks a harder question — whether the method *works* — and it is the only
falsifiable claim the project makes about its own usefulness.

The design is a time split. Take a corpus with publication years, hide
everything from a cutoff year onward, run ABC discovery on the past alone, then
check which of its proposed A–C links actually show up in the hidden future. A
proposal that later became real literature is a hit.

**Why the baseline is not optional.** A bare hit rate is exactly the vanity
metric ``evals/METHODOLOGY.md`` forbids: with a dense corpus you could "confirm"
most random pairs and look brilliant. So every run also pairs A against
randomly drawn concepts from the same pool and measures how often *those* show
up. Lift is the honest number. Lift near 1.0 means the method is doing nothing
that shuffling would not.

This measures the method against **your corpus**, at one cutoff, at small N. It
is evidence, not a benchmark, and the report says so.

Deterministic given a seed. No network.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from artificial_emotions.discover import LocalCorpusClient, _norm, discover_links

__all__ = [
    "ValidationReport",
    "split_by_year",
    "validate_retrospective",
]


@dataclass
class ValidationReport:
    """Outcome of one time-split validation."""

    cutoff_year: int
    n_past_docs: int
    n_future_docs: int
    proposals: list[dict[str, Any]] = field(default_factory=list)
    baseline: list[dict[str, Any]] = field(default_factory=list)

    @property
    def n_proposals(self) -> int:
        return len(self.proposals)

    @property
    def n_confirmed(self) -> int:
        return sum(1 for p in self.proposals if p["confirmed"])

    @property
    def hit_rate(self) -> float | None:
        return (self.n_confirmed / self.n_proposals) if self.proposals else None

    @property
    def baseline_hit_rate(self) -> float | None:
        if not self.baseline:
            return None
        return sum(1 for b in self.baseline if b["confirmed"]) / len(self.baseline)

    @property
    def lift(self) -> float | None:
        """Hit rate over baseline. None when the baseline is empty or zero."""
        hit, base = self.hit_rate, self.baseline_hit_rate
        if hit is None or base is None or base <= 0.0:
            return None
        return hit / base

    def to_dict(self) -> dict[str, Any]:
        base = self.baseline_hit_rate
        lift = self.lift
        return {
            "cutoff_year": self.cutoff_year,
            "corpus": {"past_docs": self.n_past_docs, "future_docs": self.n_future_docs},
            "n_proposals": self.n_proposals,
            "n_confirmed": self.n_confirmed,
            "hit_rate": round(self.hit_rate, 4) if self.hit_rate is not None else None,
            "baseline_hit_rate": round(base, 4) if base is not None else None,
            "lift_over_baseline": round(lift, 3) if lift is not None else None,
            "proposals": self.proposals,
            "baseline_samples": self.baseline,
            "how_to_read": (
                "Proposals were generated from pre-cutoff literature only, then "
                "checked against the held-out post-cutoff literature. Compare "
                "hit_rate against baseline_hit_rate: lift near 1.0 means the "
                "method is doing no better than random pairing."
            ),
            "baseline_note": (
                "The random pool is not filtered to exclude concepts the method "
                "also proposed, so the control can draw the same pairs and score "
                "hits of its own. That makes the baseline harder to beat and lift "
                "a floor rather than a ceiling — deliberately the conservative "
                "direction to err in."
            ),
            "honesty": "retrospective_small_n",
            "claims_not": [
                "a benchmark result — this is one corpus at one cutoff",
                "statistical significance at this sample size",
                "that confirmed links were caused by anything the method knew",
                "generalisation beyond the corpus you supplied",
            ],
            "docs": "evals/METHODOLOGY.md",
        }

    def summary(self) -> str:
        hit = self.hit_rate
        base = self.baseline_hit_rate
        lift = self.lift
        parts = [
            f"cutoff {self.cutoff_year}: "
            f"{self.n_past_docs} past docs → {self.n_proposals} proposals, "
            f"{self.n_confirmed} confirmed in {self.n_future_docs} held-out docs"
        ]
        if hit is not None:
            parts.append(f"hit_rate={hit:.2f}")
        if base is not None:
            parts.append(f"baseline={base:.2f}")
        if lift is not None:
            parts.append(f"lift={lift:.2f}x")
        elif base == 0.0:
            parts.append("lift=undefined (baseline never hit)")
        return " | ".join(parts)


def split_by_year(
    documents: list[dict[str, Any]],
    cutoff_year: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split into ``(past, future)`` at ``cutoff_year``.

    Documents without a usable year are dropped rather than guessed at — a
    validation that silently assumes dates is worse than one that reports a
    smaller corpus.
    """
    past: list[dict[str, Any]] = []
    future: list[dict[str, Any]] = []
    for doc in documents:
        raw = doc.get("year")
        try:
            year = int(raw)
        except (TypeError, ValueError):
            continue
        (past if year < cutoff_year else future).append(doc)
    return past, future


def _concept_pool(documents: list[dict[str, Any]]) -> list[str]:
    pool: dict[str, None] = {}
    for doc in documents:
        for concept in doc.get("concepts") or []:
            name = str(concept).strip()
            if name:
                pool[name] = None
    return sorted(pool)


def validate_retrospective(
    corpus: str | Path | list[dict[str, Any]],
    *,
    seeds: list[str],
    cutoff_year: int,
    max_links_per_seed: int = 5,
    cooccurrence_ceiling: int = 400,
    baseline_samples_per_seed: int = 5,
    seed: int = 42,
) -> ValidationReport:
    """Run discovery on pre-cutoff literature and score it against the future.

    Args:
        corpus: documents (or a path) carrying ``year`` and ``concepts``.
        seeds: concepts to start discovery from.
        cutoff_year: everything from this year onward is held out.
        baseline_samples_per_seed: random A–C pairs per seed, for the control.
        seed: RNG seed, so the baseline is reproducible.

    Returns:
        A :class:`ValidationReport` with proposals, baseline, and lift.
    """
    documents = (
        LocalCorpusClient.from_file(corpus).documents
        if isinstance(corpus, str | Path)
        else list(corpus)
    )
    past, future = split_by_year(documents, cutoff_year)
    past_client = LocalCorpusClient(documents=past)
    future_client = LocalCorpusClient(documents=future)

    report = ValidationReport(
        cutoff_year=cutoff_year,
        n_past_docs=len(past),
        n_future_docs=len(future),
    )
    pool = _concept_pool(past)
    rng = random.Random(seed)

    for a in seeds:
        links = discover_links(
            a,
            client=past_client,
            max_links=max_links_per_seed,
            cooccurrence_ceiling=cooccurrence_ceiling,
        )
        for link in links:
            future_cooc = future_client.cooccurrence_count(link.a, link.c)
            report.proposals.append(
                {
                    "a": link.a,
                    "b": link.b,
                    "c": link.c,
                    "question": link.question,
                    "past_cooccurrence": link.cooccurrence,
                    "future_cooccurrence": future_cooc,
                    "confirmed": future_cooc > 0,
                    "gap_score": round(link.gap, 6),
                }
            )

        # Control: same A, random C from the same pool, same confirmation test.
        # Anything the method beats here it beats on structure, not on the corpus
        # simply being dense.
        options = [
            c
            for c in pool
            if _norm(c) != _norm(a) and past_client.cooccurrence_count(a, c) <= cooccurrence_ceiling
        ]
        rng.shuffle(options)
        for c in options[: max(0, baseline_samples_per_seed)]:
            future_cooc = future_client.cooccurrence_count(a, c)
            report.baseline.append(
                {
                    "a": a,
                    "c": c,
                    "future_cooccurrence": future_cooc,
                    "confirmed": future_cooc > 0,
                }
            )

    report.proposals.sort(key=lambda p: (-p["gap_score"], p["a"], p["c"]))
    return report
