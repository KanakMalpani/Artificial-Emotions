# Idea Novelty Checker vs gap verify (research)

**Status:** Competitor clarity for literature-grounded **novelty of ideas**.  
**Honesty:** Novelty ≠ unansweredness ≠ VOI. Related papers can make an idea “not novel” while the operationalized unknown remains unanswered.

*Generated: 2026-07-25 | Paper: Shahid et al. arXiv [2506.22026](https://arxiv.org/abs/2506.22026)*

---

## 1. What Idea Novelty Checker does

RAG pipeline: broad keyword/snippet retrieve → embedding filter → facet-based LLM re-rank → literature-grounded novelty reasoning with expert-labeled examples. Reports ~13% higher agreement vs prior novelty checkers.

AgentEconomist ([2604.27725](https://arxiv.org/abs/2604.27725)): intuition → lit-grounded hypotheses → simulator experiments (econ) — downstream of ranking.

---

## 2. Differentiation table

| Object | Novelty Checker | Artificial Curiosity |
|--------|-----------------|----------------------|
| Unit | Research *idea* / claim | *Unknown* / question |
| Lit role | “Has this idea been done?” | “Is this question settled?” (related≠answered) |
| Output | Novelty judgment + reasoning | Gap status + value ranks |
| Risk | Reject valuable but non-novel unknowns | Promote novel-sounding answered Qs |

**Productize:** Optional offline novelty note on briefs — **never** replace gap status. If both fire: “related and overlapping ideas exist; question still open under ops.”

---

## 3. Productize next

1. Keep verify gate primary.  
2. Optional `novelty_note` display-only (like feasibility_note) — only after calibration.  
3. Don’t optimize for Novelty Checker agreement as north star.

---

## 4. See also

[`GAP_VERIFY_METHODS.md`](GAP_VERIFY_METHODS.md) · [`GUIDE_ADVISING.md`](GUIDE_ADVISING.md) · [`SCHOLAR` / ScholarEval in competitors]
