# Multi-profile comparison UX (research companion)

**Status:** Companion to shipped `compare_profiles` ([`CONSTITUTIONAL_CURIOSITY.md`](CONSTITUTIONAL_CURIOSITY.md)).  
**Honesty:** Offline heuristic re-rank is a **decision aid** — not proof either profile is “correct.”

*Generated: 2026-07-25 | Aligns with `src/artificial_emotions/compare.py`*

---

## 1. What good comparison UX shows

| Element | Why |
|---------|-----|
| Shared candidate pool | Isolates profile effect from generation noise |
| Side-by-side ranks + scores | Path B constitutional — no silent merge |
| Rank-move list (↑↓) | Human-readable conflicts |
| Kendall τ / Spearman ρ | Compact disagreement summary |
| `max_risk` tip | min(a,b) as hard ceiling when composing veto |
| Honesty line | Offline / no lit unless flagged |

---

## 2. Disagreement metrics

| Metric | Interpretation |
|--------|----------------|
| **Kendall τ** | Pairwise concordant/discordant rank pairs; classic for ordinal assoc |
| **Spearman ρ** | Rank-transformed Pearson |
| **Top-k Jaccard** | Overlap of top-k id sets (easy UI) |
| **Biggest movers** | Items with largest |rank_a − rank_b| |

Ship τ or Spearman once n≥5; always show top movers even for small n.

---

## 3. Productize next (sibling — partial already done)

1. ✅ `compare_profiles` offline heuristic — keep honesty notes.  
2. **Return Kendall τ** in compare payload when len≥5.  
3. **CLI / MCP / API** surface + web two-column ranks.  
4. Optional: lit-on mode later (expensive; same pool verified once).  
5. Never auto-average the two rankings into one list.

---

## 4. See also

- [`CONSTITUTIONAL_CURIOSITY.md`](CONSTITUTIONAL_CURIOSITY.md)  
- `examples/constitution_veto_stack.json`  
- [`PROBLEM_SELECTION_MCNAMARA.md`](PROBLEM_SELECTION_MCNAMARA.md) — profiles as demand-pull  
