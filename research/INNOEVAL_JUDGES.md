# InnoEval / personalized judges / method graphs (research)

**Status:** Eval & competitor adjacency for idea *evaluation* (downstream of our ranking).  
**Honesty:** These systems evaluate **ideas/proposals**. We rank **unknowns under ValueProfile**. Steal judge design; don’t replace gap verify.

*Generated: 2026-07-25*

---

## 1. InnoEval (ICML 2026) — [2602.14367](https://arxiv.org/abs/2602.14367)

- Frames idea evaluation as **knowledge-grounded, multi-perspective** reasoning.
- Heterogeneous deep knowledge search + “innovation review board” with distinct academic backgrounds.
- Multi-dimensional **decoupled** metrics; claims alignment with human experts on point/pair/group tasks.
- Targets: narrow knowledge horizons, flattened dimensions, LLM-as-judge bias.

**Transfer:** Our W15 multi-judge + ValueProfile stakeholders ≈ review board; keep dimensions decoupled (don’t collapse to one Insight Score). Ground judges in lit hits we already fetch.

---

## 2. Personalized vs aggregate judges — [2604.22517](https://arxiv.org/abs/2604.22517)

- Business-idea setting: experts disagree on fine ordinals; agree more on coarse selection.
- **Personalized** judges (conditioned on target evaluator history) beat aggregate/consensus judges.
- Pooled labels are a **fragile** target under pluralism.

**Transfer:** Strong support for profile-scoped prefs/BT ([`PREFERENCE_BT_STAGE2.md`](PREFERENCE_BT_STAGE2.md)) and against global preference models. `compare_profiles` > fake consensus.

---

## 3. Intern-Atlas method evolution graph — [2604.28158](https://arxiv.org/abs/2604.28158)

- Method-level entities + lineage edges from >1M papers; grounded verbatim evidence.
- Downstream: idea evaluation + generation.

**Transfer:** Cousin to idea-graph export and LitGap co-occurrence — **methods lineage** ≠ unanswered questions. Optional future adapter for “is this unknown about a stalled method lineage?”

---

## 4. ScholarEval reminder — [2510.16234](https://arxiv.org/abs/2510.16234)

Soundness + contribution with retrieval; ScholarIdeas expert set. Best as **post-rank** critique of investigation briefs, not generate gate.

---

## 5. Productize next

1. Keep multi-judge axes decoupled; report disagreement.  
2. Never train one global “science judge” across profiles.  
3. Optional: ScholarEval/InnoEval-style soundness pass on top-n briefs offline.  
4. Idea-graph stays display-only ([`IDEA_GRAPH_UX.md`](IDEA_GRAPH_UX.md)).

---

## 6. Key citations

| Work | ID |
|------|-----|
| InnoEval | arXiv 2602.14367 |
| Personalized judges | arXiv 2604.22517 |
| Intern-Atlas | arXiv 2604.28158 |
| ScholarEval | arXiv 2510.16234 |
| In-repo | [`CURIOSITY_EVAL_METRICS.md`](CURIOSITY_EVAL_METRICS.md), `judge.py` |
