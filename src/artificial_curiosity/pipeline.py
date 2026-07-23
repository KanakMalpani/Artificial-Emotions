"""End-to-end Artificial Curiosity engine."""

from __future__ import annotations

from artificial_curiosity.brief import write_brief
from artificial_curiosity.diversity import diversify
from artificial_curiosity.generate import generate_candidates
from artificial_curiosity.judge import llm_refine_gap, llm_score
from artificial_curiosity.models import CuriosityConfig, RankedQuestion
from artificial_curiosity.openalex import OpenAlexClient
from artificial_curiosity.scoring import (
    aggregate_curiosity,
    confidence_from_signals,
    heuristic_score,
    passes_gates,
    score_uncertainty_band,
)
from artificial_curiosity.verify import verify_gap


class CuriosityEngine:
    def __init__(self, config: CuriosityConfig | None = None):
        self.config = config or CuriosityConfig()
        self._client = (
            OpenAlexClient(timeout_s=self.config.literature_timeout_s)
            if self.config.use_literature
            else None
        )

    def run(self) -> list[RankedQuestion]:
        candidates = generate_candidates(self.config)
        scored: list[RankedQuestion] = []

        for q in candidates:
            gap = verify_gap(
                q,
                client=self._client,
                use_literature=self.config.use_literature,
            )
            refined = llm_refine_gap(q, gap, self.config)
            if refined is not None:
                gap = refined

            related_count = len(gap.related_works)
            avg_cites = (
                sum((h.cited_by_count or 0) for h in gap.related_works) / related_count
                if related_count
                else 0.0
            )

            llm_axes = llm_score(q, gap, self.config)
            axes = llm_axes or heuristic_score(
                q,
                gap.status,
                related_count,
                avg_cites,
                self.config.value_profile,
                strong_match_count=gap.strong_match_count,
            )

            ok, flags = passes_gates(axes, gap.status, self.config.value_profile)
            curiosity = aggregate_curiosity(axes, self.config.value_profile)
            conf = confidence_from_signals(
                [axes] if llm_axes else None,
                gap.confidence,
                related_count,
                heuristic=llm_axes is None,
                gap_status=gap.status,
            )
            if llm_axes is None:
                flags = list(set(flags + ["heuristic_scoring"]))
            if refined is not None:
                flags = list(set(flags + ["llm_gap_reader"]))
            if not self.config.use_literature:
                flags = list(set(flags + ["no_literature"]))

            score_low, score_high = score_uncertainty_band(
                curiosity, conf, heuristic=llm_axes is None
            )

            item = RankedQuestion(
                question=q,
                scores=axes,
                curiosity_score=curiosity,
                confidence=conf,
                gap=gap,
                flags=flags,
                metadata={"passed_gates": ok},
                score_low=score_low,
                score_high=score_high,
            )
            if ok:
                item.investigation_brief = write_brief(item)
                scored.append(item)
            else:
                # Keep rejected for transparency but do not rank in top set.
                item.flags = list(set(item.flags + ["gate_failed"]))
                item.metadata["rejected"] = True

        scored.sort(key=lambda r: r.curiosity_score, reverse=True)
        backend = self.config.diversity_backend  # type: ignore[assignment]
        return diversify(
            scored,
            threshold=self.config.diversity_threshold,
            n_return=self.config.n_return,
            backend=backend if backend in ("jaccard", "embedding") else "jaccard",
        )

    def run_dict(self) -> list[dict]:
        return [r.model_dump(mode="json") for r in self.run()]
