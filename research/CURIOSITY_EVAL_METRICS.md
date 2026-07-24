# Curiosity / idea-ranking eval metrics (research)

**Status:** Eval-design spike for W10 expert harness and future calibration reports.  
**Honesty:** LLM-as-judge novelty often **aligns in rationale text but not in scores** with humans (RINoBench). Ideation-stage “wins” can reverse after execution (ideation–execution gap). Prefer multi-metric + human spot-checks.

*Generated: 2026-07-25 | Sources: Academia (RINoBench, IdeaBench, RND, IAScore, ideation-execution) | Confidence: High on published caveats.*

---

## 1. Executive summary

Do not optimize a single “novelty” LLM score. Use a **metric stack**: (1) gap-status correctness (answered vs not), (2) ranking agreement with held-out humans/prefs under a fixed ValueProfile, (3) investigation-quality from provoke A/B ([`EPISTEMIC_ELICITATION.md`](EPISTEMIC_ELICITATION.md)), (4) optional literature-structure novelty (RND / co-occurrence), (5) deferred outcome metrics when execution exists. Treat GPT-ranked “Insight Score” (IdeaBench) as **personalized proxy**, not ground truth.

---

## 2. Benchmarks & metrics to know

| Resource | What it measures | Caution |
|----------|------------------|---------|
| **RINoBench** ([2603.10303](https://arxiv.org/abs/2603.10303)) | Novelty *judgment* vs expert gold; 9 automated metrics on scores + justifications | LLM reasoning can look human while judgments diverge |
| **IdeaBench** ([2411.02429](https://arxiv.org/abs/2411.02429)) | Idea generation; GPT ranks by user-chosen indicators → Insight Score | Judge model = generator family risk |
| **AI Idea Bench 2025** ([2504.14191](https://arxiv.org/abs/2504.14191)) | Alignment to inspired follow-on papers + refs | Leakage / training contamination |
| **RND** ([2503.01508](https://arxiv.org/abs/2503.01508)) | Relative Neighbor Density novelty; cross-domain AUROC | Novelty ≠ VOI; good as *one* axis check |
| **IAScore / Distinctness** ([2409.06185](https://arxiv.org/abs/2409.06185)) | Alignment + diversity of future ideas | Still need human novelty/feasibility |
| **Ideation–execution gap** ([2506.20803](https://arxiv.org/abs/2506.20803)) | Expert execution of LLM vs human ideas; post-exec reviews | LLM ideas look better pre-exec; gap closes/flips after |
| **ScholarEval** | Soundness + contribution vs expert rubrics | Downstream of ideation |
| **SciMuse** | Expert *interest* prediction | Interest ≠ ITN/VOI |
| **EIG** ([2605.04922](https://arxiv.org/abs/2605.04922)) | Evolving idea graphs; edit-and-commit | Architecture inspiration for tracking conflicts |

---

## 3. Recommended metric stack for *this* product

| Layer | Metric | How |
|-------|--------|-----|
| **F1 gap** | Precision/recall of unanswered vs hand labels | Seed fixture set |
| **Rank quality** | Spearman / NDCG vs human or pref BT skills | Per `ValueProfile` |
| **Judge stability** | Disagreement entropy (W15) | Already partially shipped |
| **Elicit quality** | Rubric from `examples/elicit_ab_protocol.json` | Provoke A/B |
| **Novelty proxy (optional)** | RND or LitGapFinder-style gap score correlation with our surprise/neglectedness | Research log only |
| **Safety** | Dual-use red-team P/R | [`DUAL_USE_RANKING.md`](DUAL_USE_RANKING.md) |
| **Outcome (slow)** | Prefer → later `already_answered` / paper exists | Prefs JSONL |

**Primary north star for v0.x:** gap correctness + profile-conditioned human rank correlation — not SciMuse AUC or RINoBench alone.

---

## 4. Productize next (sibling)

1. Expand `curiosity eval` report sections: gap_f1, rank_spearman, elicit_rubric_mean, risk_flags.  
2. Add `evals/fixtures/gap_labels.jsonl` (10–30 hand labels).  
3. Document that LLM novelty judges are **secondary**.  
4. Optional offline RND/cooccur correlation notebook — not in default pytest.  
5. Cite ideation–execution gap in LIMITS: ranked unknowns are not guaranteed good after execution.

---

## 5. Key citations

| Work | ID |
|------|-----|
| RINoBench | arXiv 2603.10303 |
| IdeaBench | arXiv 2411.02429 |
| RND novelty | arXiv 2503.01508 |
| IAScore / Distinctness | arXiv 2409.06185 |
| Ideation–execution gap | arXiv 2506.20803 |
| EIG idea graphs | arXiv 2605.04922 |
| ScholarEval | arXiv 2510.16234 |
| SciMuse | arXiv 2405.17044 |
