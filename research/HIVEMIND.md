# Artificial Hivemind → generator diversity (research)

**Status:** Companion to [`PROBLEM_SELECTION_MCNAMARA.md`](PROBLEM_SELECTION_MCNAMARA.md) / [`FAILURE_KNOWLEDGE.md`](FAILURE_KNOWLEDGE.md).  
**Paper:** Jiang et al., *Artificial Hivemind* (NeurIPS 2025 D&B Oral; arXiv [2510.22954](https://arxiv.org/abs/2510.22954)).

*Generated: 2026-07-25 | Confidence: High on abstract claims.*

---

## 1. Takeaway

Open-ended LM generation shows **intra-model repetition** and **inter-model homogeneity** (Infinity-Chat: 26K real open-ended queries; taxonomy incl. brainstorm/ideation). Human prefs are idiosyncratic; LM judges/reward models are **poorly calibrated** when annotators disagree despite similar “quality.”

For curiosity: generating unknowns is an open-ended ideation task — exactly where hivemind bites. Multi-provider ensembles without diversity metrics may **feel** plural while collapsing.

---

## 2. Product implications

| Practice | Hivemind risk | Mitigation |
|----------|---------------|------------|
| Multi-LLM generate + vote | Inter-model homogeneity | Measure embedding similarity; prefer disagreement |
| High-temperature single model | Intra-model mode collapse | Diversity stage (already); n_candidates >> n_return |
| LLM-as-judge ranking | Mis-calibrated on idiosyncratic prefs | Keep ValueProfile + human prefs primary |
| Infinity-Chat-style eval | — | Optional: sample open-ended unknown prompts; score top-n similarity |

---

## 3. Productize next (sibling)

Full recipe: [`HIVEMIND_METRIC_SPEC.md`](HIVEMIND_METRIC_SPEC.md).

1. Eval: mean pairwise cosine of top-n question embeddings (hivemind score).  
2. Flag runs when similarity > threshold.  
3. Do not advertise “6 models = 6× creativity.”  

---

## 4. See also

- Bisht hypothesis-hivemind experiment (arXiv 2605.08956)  
- Agent Economics BPF entropy control (arXiv 2606.09039) — conceptual cousin  
