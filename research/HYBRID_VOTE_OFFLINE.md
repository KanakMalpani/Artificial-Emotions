# HybridQuestion-style cross-model vote — offline protocol (research)

**Status:** P2 moonshot protocol for [`HYBRID_QUESTION.md`](HYBRID_QUESTION.md).  
**Honesty:** Multi-model vote measures **agreement**, not truth or VOI. Hivemind risk rises with vote ([`HIVEMIND.md`](HIVEMIND.md)). Default product path stays single-generator + diversity stage.

*Generated: 2026-07-25*

---

## 1. Goal

Offline, measure how often model A’s top-n unknowns are endorsed by models B/C under the **same** ValueProfile + domain pack — inspired by HybridQuestion’s AI↔human divergence on *future* questions.

**Sibling landing:** `hybrid_vote.py` implements a **form-critic heuristic proxy** (keep/drop/rewrite + hivemind) for CI — not live multi-LLM. Treat as scaffold until real judges are wired offline.

---

## 2. Protocol

1. Fix seed pack, profile, temperature, `n_candidates`, `n_return`.  
2. Generate with model family set \(\{M_1,\ldots,M_k\}\) (k≤3 to control cost).  
3. For each \(M_i\) top-n, ask other models to **vote** (keep / drop / rewrite) with rubric: specificity, falsifier present, related≠answered respect.  
4. Metrics:
   - Mean keep-rate across judges  
   - Embedding hivemind_mean_cosine within and across models  
   - Spearman of axis scores vs vote rank (expect weak)  
5. Human subsample (n≥20): interest vs keep-rate (SciMuse cousin).

---

## 3. Decision rules for product

| Finding | Action |
|---------|--------|
| High keep-rate + high hivemind | Vote adds little; skip shipping |
| Low keep-rate, better human interest | Optional offline “second opinion” tool — not default provoke |
| Judges prefer high-surprise sprawl | Keep critique_brief gate |

---

## 4. Productize next

- Offline script only (sibling may place under `evals/`).  
- Never silent re-rank from votes in API default.  
- If exposed: `cross_model_vote` tool returns annotations + honesty string.

---

## 5. See also

[`HYBRID_QUESTION.md`](HYBRID_QUESTION.md) · [`CRITIC_DEBATE_JUDGES.md`](CRITIC_DEBATE_JUDGES.md) · [`HIVEMIND_METRIC_SPEC.md`](HIVEMIND_METRIC_SPEC.md)
