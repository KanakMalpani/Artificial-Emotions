# GUIDE — scalable research-idea advising (research)

**Status:** Competitor note for post-rank critique / advising.  
**Honesty:** GUIDE advises on **hypotheses & experimental designs** toward venue acceptance proxies. We rank **unanswered questions** under ValueProfile. Different job; overlapping “feedback” UX.

*Generated: 2026-07-25 | Paper: Liu et al. arXiv [2507.08870](https://arxiv.org/abs/2507.08870)*

---

## 1. Finding

GUIDE: small model + compressed literature DB + structured reasoning can beat large general LLMs on self-ranked top-30% ICLR 2025 acceptance-rate proxies; high-confidence slice >90% acceptance on their test set.

Factors studied: model size, context length, confidence estimation, structured reasoning.

---

## 2. Transfer

| GUIDE | Artificial Curiosity |
|-------|----------------------|
| Advise / refine ideas | Optional after rank (critique, soundness, feasibility_note) |
| Lit DB grounding | OpenAlex neighborhood — related≠answered still primary |
| Confidence estimation | Uncertainty bands on scores |
| Acceptance-rate proxy | **Dangerous north star** — McNamara / venue gaming ([`PROBLEM_SELECTION_MCNAMARA.md`](PROBLEM_SELECTION_MCNAMARA.md)) |

**Do not** optimize curiosity ranks for predicted conference acceptance.

---

## 3. Ideation–execution reminder

Si et al. ([2506.20803](https://arxiv.org/abs/2506.20803)): LLM ideas look better pre-exec; scores drop more than human ideas after execution. Reinforces outcome flywheel + LIMITS “not guaranteed programs.”

---

## 4. Productize next

1. Keep soundness/critique as **advise layer**, not rank objective.  
2. Optional confidence on soundness triage (already pass/revise/fail).  
3. Never add `predicted_acceptance` axis.

---

## 5. See also

[`INNOEVAL_JUDGES.md`](INNOEVAL_JUDGES.md) · [`GAP_VERIFICATION_COMPETITORS.md`](GAP_VERIFICATION_COMPETITORS.md) · [`OUTCOME_FLYWHEEL.md`](OUTCOME_FLYWHEEL.md)
