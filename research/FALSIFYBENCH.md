# FALSIFYBENCH — negative testing for scientific agents (research)

**Status:** Eval inspiration for falsifier-first investigation quality.  
**Honesty:** Game task ≠ lab science; still the **negative-testing** finding transfers to our elicit rubric.

*Generated: 2026-07-25 | Paper: Bertolazzi et al. arXiv [2606.04751](https://arxiv.org/abs/2606.04751)*

---

## 1. Finding

FALSIFYBENCH adapts Wason 2-4-6–style rule discovery: agents propose examples, get feedback, must discover hidden properties. Across 12 LLMs:

- Reasoning models > instruction-tuned on this scientific-reasoning proxy.
- **No model near optimal.**
- Primary success driver: **capacity for negative testing** — actively seeking to falsify hypotheses beats confirmation-seeking.
- Turn-level failures map to identifiable hypothesis-space navigation patterns.

---

## 2. Transfer to Artificial Curiosity

| FALSIFYBENCH | Our stack |
|--------------|-----------|
| Seek disconfirming evidence | Elicit rubric: falsifier / discriminating observation |
| Confirmation bias failure | `critique_brief` `missing_falsifier` |
| Hypothesis-space navigation | Rank unknowns → investigate one; don’t sprawl |
| Not optimal LLMs | Don’t claim BoxingGym / co-scientist execution skill |

**Productize:** Weight falsifier presence higher in elicit A/B primary metric; optional “propose one falsifying observation” line in provoke inject when `confusion_risk` or missing_falsifier.

---

## 3. Sibling note on hybrid vote

`hybrid_vote.py` uses form-critic heuristics as CI-safe stand-in for multi-LLM vote ([`HYBRID_VOTE_OFFLINE.md`](HYBRID_VOTE_OFFLINE.md)). Aligns with negative-testing: sprawl/anthropomorphism → drop; missing falsifier → rewrite. Live multi-model remains offline/costly.

---

## 4. Key citations

| Work | ID |
|------|-----|
| FALSIFYBENCH | arXiv 2606.04751 |
| In-repo | [`INVESTIGATION_DESIGN.md`](INVESTIGATION_DESIGN.md), `examples/elicit_ab_protocol.json` |
