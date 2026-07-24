# Bayesian surprise ↔ open-ended discovery (moonshot pointer)

**Status:** Short spike for ROADMAP §7.6 *Bayesian surprise search*.  
**Honesty:** AutoDiscovery’s surprisal is **prior→posterior shift after experiments**. Our `surprise` axis is a **literature/prior-belief proxy**, not measured experimental Bayesian update.

*Generated: 2026-07-25 | Source: AutoDiscovery NeurIPS 2025 (arXiv [2507.00310](https://arxiv.org/abs/2507.00310)) | Confidence: High on paper claims; Low on port without lab loop.*

---

## 1. What AutoDiscovery does

- Open-ended ASD: choose hypotheses by **Bayesian surprise** (epistemic shift from LLM prior to posterior after gathering experimental results), not diversity heuristics alone.
- Nested hypotheses explored with **MCTS + progressive widening**; surprisal as reward.
- Eval: 21 real datasets; 5–29% more LLM-judged “surprising” discoveries under fixed budget; ~2/3 surprising to domain experts in human eval.

## 2. Mapping to Artificial Curiosity

| AutoDiscovery | This repo | Gap |
|---------------|-----------|-----|
| Prior beliefs about hypothesis | Generator + lit neighborhood | Soft |
| Posterior after experiment | — | **Missing** (no lab closed-loop) |
| Surprisal reward | `ScoreAxes.surprise` | Proxy only |
| MCTS over nested hyps | Rank + diversify list | No tree search |
| Expert surprisingness | Prefs / SciMuse-like interest | Optional |

## 3. Productize next (only if moonshot requested)

1. Log “predicted surprise” at rank time; after user marks `outcome`, compute crude update note (manual).  
2. Do **not** rename axis to `bayesian_surprise` without posterior evidence.  
3. Pair with provoke: treat high-surprise items as candidates for cheap pilot experiments that *could* yield measurable updates.

## 4. See also

- [`EPISTEMIC_ELICITATION.md`](EPISTEMIC_ELICITATION.md) — Yanagisawa Bayesian IG / Wundt curve  
- [`VOI_APPROXIMATIONS.md`](VOI_APPROXIMATIONS.md) — information value after sampling  
- ROADMAP lab closed-loop moonshot  
