# SFBench-inspired feasibility note — offline calibration (research)

**Status:** Extends [`ANSWERABILITY_FEASIBILITY.md`](ANSWERABILITY_FEASIBILITY.md).  
**Honesty:** SFBench scores **de novo materials claims**, not open scientific questions. Any `feasibility_1to5` we add is a **cousin judge**, not SFBench replication.

*Generated: 2026-07-25 | SFBench arXiv [2606.29630](https://arxiv.org/abs/2606.29630)*

---

## 1. Why calibrate offline

Our heuristics for answerability/tractability are cheap and honest as heuristics. Folding an LLM 1–5 feasibility into the **aggregate curiosity score** without calibration risks McNamara (optimize the number). Keep optional field **display-only** until Spearman vs expert subsample is known.

---

## 2. Offline protocol (materials pack first)

1. Sample 30–50 materials_catalysis unknowns (or SFBench claims if licensed/available).  
2. Collect expert or strong-amateur 1–5 feasibility + one-sentence why (SFBench style).  
3. Score with: (a) our tractability heuristic, (b) optional LLM judge with SFBench-like rubric.  
4. Report Spearman(a, expert), Spearman(b, expert); confusion matrices on bins low/mid/high.  
5. Ship UI tooltip only if |ρ| is reported; never silent weight.

---

## 3. Rubric language to steal (not scores)

Judge prompt dimensions (paraphrase, don’t claim SFBench):

- Physical / chemical plausibility of the claim as stated  
- Required resources / infrastructure realism  
- Whether the claim is answerable as posed vs program-sprawl  
- Confidence and what evidence would move the score  

Pair with falsifier ask ([`FALSIFYBENCH.md`](FALSIFYBENCH.md)).

---

## 4. Productize next

1. UI tooltips for answerability vs tractability (already recommended).  
2. Optional `feasibility_note` string on briefs — free text, not axis.  
3. Do **not** add `scores.feasibility` to weighted sum in v0.x.

---

## 5. See also

[`PROBLEM_SELECTION_MCNAMARA.md`](PROBLEM_SELECTION_MCNAMARA.md) · [`DOMAIN_PACK_QUALITY.md`](DOMAIN_PACK_QUALITY.md)
