# Evidence-informed LLM beliefs — AutoDiscovery follow-on (research)

**Status:** Addendum to [`BAYESIAN_SURPRISE.md`](BAYESIAN_SURPRISE.md).  
**Honesty:** Still requires **experimental evidence loop**. Our `fill_surprise_worksheet` only logs belief-shift Likert — not non-stationary LLM surprisal.

*Generated: 2026-07-25 | Paper: Agarwal et al. arXiv [2606.29182](https://arxiv.org/abs/2606.29182)*

---

## 1. Finding

AutoDiscovery treats surprisal as **static** (prior→posterior for one hypothesis). Human surprisal is **non-stationary** — beliefs evolve with experience.

Evidence-informed LLM beliefs:

- Update priors with evidence from previous hypotheses.
- Embedding RAG over prior discoveries best anticipates posteriors; flags **~37.5% of static surprisals as spurious**.
- Search changes: belief-update filtering + diversity maximization → **+30.6%** accumulated non-stationary surprisal vs original search (5 domains).

---

## 2. Transfer

| Claim | Product implication |
|-------|---------------------|
| Static surprise over-rewards repeats | Hivemind + diversity already relevant |
| Need evolving beliefs | Outcome flywheel + worksheet history — not axis rename |
| Spurious surprisal | Don’t chase high `scores.surprise` alone |
| Continual discovery needs search change | Co-scientist / lab moonshot — not v0.x ranking |

Sibling `bayesian.py` / `fill_surprise_worksheet` stays **manual logging**. Future: store worksheets as RAG corpus for human belief notes only.

---

## 3. Productize next

1. Wire worksheet fill to API/MCP with honesty string.  
2. Optional: list prior outcome notes when filling a new worksheet (human RAG).  
3. Still never rename `ScoreAxes.surprise` to Bayesian surprise.

---

## 4. Key citations

| Work | ID |
|------|-----|
| AutoDiscovery | arXiv 2507.00310 |
| Evidence-informed beliefs | arXiv 2606.29182 |
| In-repo | `bayesian.py`, `examples/bayesian_surprise_worksheet.json` |
