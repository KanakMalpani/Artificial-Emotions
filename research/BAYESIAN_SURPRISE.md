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

### 3.1 Minimal closed-loop worksheet (offline)

When a user later logs PreferenceEvent `outcome` (or lab note):

| Field | Source |
|-------|--------|
| `predicted_surprise` | `scores.surprise` at rank time (snapshot) |
| `pilot_result` | short text / pass-fail / metric |
| `belief_shift` | user Likert 1–5 “how much did this change your belief?” |
| `crude_update_note` | free text — **not** a KL divergence |

Report Spearman(predicted_surprise, belief_shift) offline. If weak, keep axis as lit proxy. Yanagisawa IG / Wundt still inform **cue** design, not this rename.

Neuro/MARL “Bayesian surprise” papers (cultures, ICES) are **different objects** — do not cite as product validation.

**Follow-on:** Non-stationary / evidence-informed LLM beliefs ([`EVIDENCE_INFORMED_BELIEFS.md`](EVIDENCE_INFORMED_BELIEFS.md); arXiv 2606.29182) — static surprisal can be spurious; diversity+belief update matter for continual discovery. Sibling `fill_surprise_worksheet` remains manual logging only.

## 4. See also

- [`EPISTEMIC_ELICITATION.md`](EPISTEMIC_ELICITATION.md) — Yanagisawa Bayesian IG / Wundt curve  
- [`VOI_APPROXIMATIONS.md`](VOI_APPROXIMATIONS.md) — information value after sampling  
- [`OUTCOME_FLYWHEEL.md`](OUTCOME_FLYWHEEL.md) — sparse outcome events  
- ROADMAP lab closed-loop moonshot  
