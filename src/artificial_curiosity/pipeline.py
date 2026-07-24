"""End-to-end Artificial Curiosity engine."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from artificial_curiosity.brief import feasibility_note, write_brief
from artificial_curiosity.diversity import diversify
from artificial_curiosity.generate import generate_candidates
from artificial_curiosity.judge import llm_refine_gap, llm_score_ensemble
from artificial_curiosity.literature import build_literature_client
from artificial_curiosity.models import CuriosityConfig, GapEvidence, RankedQuestion, UnansweredQuestion
from artificial_curiosity.preferences import (
    PreferenceEvent,
    append_preference_event,
    apply_preference_rerank,
    apply_weight_hints_to_profile,
    learn_profile_weight_hints,
    preference_score_adjustments,
)
from artificial_curiosity.scoring import (
    aggregate_curiosity,
    confidence_from_signals,
    dual_use_flags,
    heuristic_score,
    lit_rationale_keys,
    passes_gates,
    score_uncertainty_band,
)
from artificial_curiosity.verify import verify_gap


class CuriosityEngine:
    def __init__(self, config: CuriosityConfig | None = None):
        self.config = config or CuriosityConfig()
        self._client = None
        if self.config.use_literature:
            self._client = build_literature_client(
                self.config.literature_backend,
                timeout_s=self.config.literature_timeout_s,
                cache_dir=self.config.literature_cache_dir,
                cache_ttl_s=self.config.literature_cache_ttl_s,
            )

    def _verify_one(self, question: UnansweredQuestion) -> GapEvidence:
        return verify_gap(
            question,
            client=self._client,
            use_literature=self.config.use_literature,
            literature_backend=self.config.literature_backend
            if self.config.use_literature
            else "none",
        )

    def _verify_all(self, candidates: list[UnansweredQuestion]) -> list[GapEvidence]:
        """Fetch gap evidence; parallelize literature calls when workers > 1."""
        workers = int(self.config.literature_workers or 1)
        if (
            self.config.use_literature
            and self._client is not None
            and workers > 1
            and len(candidates) > 1
        ):
            with ThreadPoolExecutor(max_workers=min(workers, len(candidates))) as pool:
                return list(pool.map(self._verify_one, candidates))
        return [self._verify_one(q) for q in candidates]

    def run(self) -> list[RankedQuestion]:
        # Optional profile-scoped weight hints from labeled JSONL (CLI/config only).
        weight_hint_meta: dict | None = None
        if self.config.preference_learn_path:
            hints = learn_profile_weight_hints(
                self.config.preference_learn_path,
                profile_name=self.config.value_profile.name.split("+", 1)[0],
                base_profile=self.config.value_profile,
            )
            if hints.get("ok"):
                self.config.value_profile = apply_weight_hints_to_profile(
                    self.config.value_profile, hints
                )
                weight_hint_meta = {
                    "deltas": hints.get("deltas"),
                    "n_prefer": hints.get("n_prefer"),
                    "n_reject": hints.get("n_reject"),
                }

        candidates = generate_candidates(self.config)
        scored: list[RankedQuestion] = []
        rejected_for_log: list[RankedQuestion] = []

        gaps = self._verify_all(candidates)
        for q, gap in zip(candidates, gaps):
            refined = llm_refine_gap(q, gap, self.config)
            if refined is not None:
                gap = refined

            related_count = len(gap.related_works)
            avg_cites = (
                sum((h.cited_by_count or 0) for h in gap.related_works) / related_count
                if related_count
                else 0.0
            )

            llm_axes, judge_members, disagree = llm_score_ensemble(q, gap, self.config)
            axes = llm_axes or heuristic_score(
                q,
                gap.status,
                related_count,
                avg_cites,
                self.config.value_profile,
                strong_match_count=gap.strong_match_count,
            )
            # Attach OpenAlex transparency keys without changing numeric weights.
            keys = lit_rationale_keys(gap.related_works)
            axes.rationale = {**(axes.rationale or {}), **keys}

            ok, flags = passes_gates(axes, gap.status, self.config.value_profile)
            text_blob = f"{q.question} {q.why_it_matters} {q.operationalization}"
            flags = list(set(flags + dual_use_flags(text_blob, self.config.value_profile)))

            curiosity = aggregate_curiosity(axes, self.config.value_profile)
            conf = confidence_from_signals(
                judge_members if judge_members else ([axes] if llm_axes else None),
                gap.confidence,
                related_count,
                heuristic=llm_axes is None,
                gap_status=gap.status,
                disagreement_entropy=disagree,
            )
            if llm_axes is None:
                flags = list(set(flags + ["heuristic_scoring"]))
            if refined is not None:
                flags = list(set(flags + ["llm_gap_reader"]))
                if gap.llm_grounded is False:
                    flags = list(set(flags + ["llm_gap_ungrounded"]))
                elif gap.llm_grounded is True:
                    flags = list(set(flags + ["llm_gap_grounded"]))
            if not self.config.use_literature:
                flags = list(set(flags + ["no_literature"]))
            if disagree >= 0.35:
                flags = list(set(flags + ["judge_disagreement"]))
            if self.config.use_literature and int(self.config.literature_workers or 1) > 1:
                flags = list(set(flags + ["lit_parallel"]))
            if weight_hint_meta:
                flags = list(set(flags + ["preference_weight_hints"]))

            score_low, score_high = score_uncertainty_band(
                curiosity,
                conf,
                heuristic=llm_axes is None,
                disagreement_entropy=disagree,
            )

            meta = {
                "passed_gates": ok,
                "judge_disagreement_entropy": disagree,
                "n_judges": len(judge_members),
                "literature_backend": gap.literature_backend or self.config.literature_backend,
                "literature_workers": int(self.config.literature_workers or 1),
            }
            if weight_hint_meta:
                meta["preference_weight_hints"] = weight_hint_meta

            item = RankedQuestion(
                question=q,
                scores=axes,
                curiosity_score=curiosity,
                confidence=conf,
                gap=gap,
                flags=flags,
                metadata=meta,
                score_low=score_low,
                score_high=score_high,
            )
            if ok:
                item.investigation_brief = write_brief(item)
                item.metadata["feasibility_note"] = feasibility_note(item)
                scored.append(item)
            else:
                # Keep rejected for transparency but do not rank in top set.
                item.flags = list(set(item.flags + ["gate_failed"]))
                item.metadata["rejected"] = True
                rejected_for_log.append(item)

        scored.sort(key=lambda r: r.curiosity_score, reverse=True)
        backend = self.config.diversity_backend  # type: ignore[assignment]
        result = diversify(
            scored,
            threshold=self.config.diversity_threshold,
            n_return=self.config.n_return,
            backend=backend if backend in ("jaccard", "embedding") else "jaccard",
        )

        # Thin preference re-rank (opt-in): prefer/reject JSONL → small score deltas.
        # Does NOT learn universal ValueProfile weights — profile-scoped only.
        # Paths come from CuriosityConfig / CLI only (not HTTP body — path injection).
        if self.config.preference_rerank_path:
            adj = preference_score_adjustments(
                self.config.preference_rerank_path,
                profile_name=self.config.value_profile.name,
            )
            if adj:
                result = apply_preference_rerank(result, adj)
                for item in result:
                    delta = float(item.metadata.get("preference_delta") or 0.0)
                    if not delta:
                        continue
                    item.score_low, item.score_high = score_uncertainty_band(
                        item.curiosity_score,
                        item.confidence,
                        heuristic="heuristic_scoring" in (item.flags or []),
                        disagreement_entropy=float(
                            item.metadata.get("judge_disagreement_entropy") or 0.0
                        ),
                    )

        # Opt-in preference JSONL snapshot (W13) — ranks only, unlabeled.
        if self.config.preference_log_path:
            for r in result:
                axes = {}
                if r.scores is not None:
                    dumped = r.scores.model_dump(mode="json")
                    axes = {
                        k: float(dumped[k])
                        for k in ("impact", "neglectedness", "tractability", "surprise")
                        if k in dumped and dumped[k] is not None
                    }
                append_preference_event(
                    self.config.preference_log_path,
                    PreferenceEvent(
                        event_type="note",
                        profile_name=self.config.value_profile.name,
                        domain=str(q.domain) if (q := r.question) else None,
                        question_id=getattr(r.question, "id", None),
                        question_text=getattr(r.question, "question", None),
                        rank=r.rank,
                        curiosity_score=r.curiosity_score,
                        score_axes=axes,
                        notes="auto_snapshot_from_run",
                        metadata={
                            "flags": r.flags,
                            "literature_backend": r.metadata.get("literature_backend"),
                        },
                    ),
                )

        return result

    def run_dict(self) -> list[dict]:
        return [r.model_dump(mode="json") for r in self.run()]
