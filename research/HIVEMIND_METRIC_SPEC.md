# Hivemind metric — eval specification (research)

**Status:** Concrete eval recipe for [`HIVEMIND.md`](HIVEMIND.md) / Jiang et al. arXiv [2510.22954](https://arxiv.org/abs/2510.22954).  
**Honesty:** High embedding similarity ≠ “bad science”; it flags **mode collapse risk** in open-ended unknown generation. Report alongside quality metrics; never optimize similarity alone to zero (that rewards gibberish diversity).

*Generated: 2026-07-25*

---

## 1. Primary metric: mean pairwise cosine (top-n)

Given ranked unknowns \(q_1,\ldots,q_n\) (recommend \(n\in\{5,10\}\)):

1. Embed question text (optionally `question + operationalization`) with a fixed encoder (same model across runs).  
2. L2-normalize vectors.  
3. Compute mean pairwise cosine over \(\binom{n}{2}\) pairs → **`hivemind_mean_cosine`**.  
4. Also report **`hivemind_max_cosine`** (near-duplicate detector) and **`hivemind_min_cosine`**.

Optional: embedding of `domain` + profile name as conditioning check (should not dominate).

---

## 2. Secondary metrics

| Metric | Purpose |
|--------|---------|
| Lexical Jaccard / n-gram overlap | Cheap offline without embeddings |
| Distinct-1 / Distinct-2 | Token diversity |
| Cluster count (HDBSCAN / k-means elbow) | Collapse into few themes |
| Cross-run Jaccard of top-n ids | Intra-model repetition across seeds |
| Cross-provider mean cosine | Inter-model homogeneity (HybridQuestion path) |

Bisht et al. hypothesis-hivemind (arXiv [2605.08956](https://arxiv.org/abs/2605.08956)): multi-model without diversity control still collapses — use cross-provider cosine when ensembles ship.

---

## 3. Suggested flags (starting points — calibrate later)

| Flag | Heuristic |
|------|-----------|
| `near_duplicate` | max pairwise cosine ≥ 0.92 (encoder-dependent) |
| `hivemind_warn` | mean pairwise ≥ 0.75 for n=10 question-only embeds |
| `ok` | mean in mid band **and** elicit/gap metrics hold |

**Calibrate** on a hand-labeled set of “diverse” vs “same idea rephrased” packs before publishing numbers in marketing.

---

## 4. Placement in eval report

Sibling `eval_report.py` should grow a section:

```text
hivemind:
  n: 10
  embedder: <id>
  mean_pairwise_cosine: …
  max_pairwise_cosine: …
  flag: ok | hivemind_warn | near_duplicate
```

Do not fail CI solely on hivemind without quality gates (gap_f1 / rubric).

---

## 5. Productize next

1. Implement embedding pairwise metric in eval (optional dependency / hash-embedding fallback for offline CI).  
2. For CI without network: character n-gram TF-IDF cosine as **proxy** (document as weaker).  
3. Dashboard: show flag on generate runs when `n_return≥5`.  
4. Copy: never “N models = N× creativity.”

---

## 6. Key citations

| Work | ID |
|------|-----|
| Artificial Hivemind | arXiv 2510.22954 |
| Bisht McNamara / hivemind | arXiv 2605.08956 |
| In-repo | [`HIVEMIND.md`](HIVEMIND.md), [`CURIOSITY_EVAL_METRICS.md`](CURIOSITY_EVAL_METRICS.md) |
