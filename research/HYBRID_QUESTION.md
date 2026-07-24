# HybridQuestion — human–AI future-question selection

**Status:** Competitor / method note for [`GAP_VERIFICATION_COMPETITORS.md`](GAP_VERIFICATION_COMPETITORS.md).  
**Paper:** Zhao, Xu, Li et al., *HybridQuestion: Human-AI Collaboration for Identifying High-Impact Research Questions* (arXiv [2602.03849](https://arxiv.org/abs/2602.03849), Dec 2025).

*Generated: 2026-07-25 | Confidence: High on abstract claims; Medium on unreproduced details.*

---

## 1. What they claim

Three-phase hybrid pipeline:

1. **AI-accelerated information gathering** — literature → hybrid information base  
2. **Candidate question proposing** — ensemble of **six** LLMs; cross-model **voting** filter  
3. **Hybrid question selection** — multi-stage filter with **progressively more human oversight**

Validation framing: identify Top-10 breakthroughs of 2025 and Top-10 questions for 2026 across five disciplines.

**Key empirical claim:** AI agents align well with humans on **established breakthroughs**, but **diverge more on prospective questions** — human judgment remains crucial for forward-looking value.

---

## 2. Implications for Artificial Curiosity

| HybridQuestion idea | Our analog | Gap / borrow |
|---------------------|------------|--------------|
| Multi-LLM propose + vote | Generator + diversity + multi-judge (W15) | Voting on *candidates* before score — optional |
| Progressive human oversight | ValueProfile + prefs + human_review_risk | Their stage-3 is heavier human; we stay agent-first |
| Breakthrough vs future Q divergence | Surprise/neglectedness for futures | Supports honesty: don’t treat LLM interest = human strategic foresight |
| Hybrid information base | OpenAlex/S2 lit cache | Keep related≠answered |

**Product lesson:** Ensemble agreement is a **confidence** signal, not a value signal. Use disagreement entropy (already) more than “majority LLM likes it.”

---

## 3. Productize next (sibling)

1. Optional **cross-model vote** stage in generate (research flag): keep items with ≥k/6 model mentions — cost heavy; offline only.  
2. Eval split: retrospective “was this answered within 12 months?” vs prospective human rank (HybridQuestion-style divergence study).  
3. Docs: cite HybridQuestion when explaining why prefs/humans still required for foresight.

---

## 4. Non-claims

- We did not re-run their Top-10 experiment.  
- Voting ensembles do not replace ValueProfile.  
