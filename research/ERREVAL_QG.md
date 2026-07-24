# ErrEval — error-aware question generation eval (research)

**Status:** Eval adjacency for generated unknowns / briefs.  
**Honesty:** ErrEval targets **QG for answering** (hallucinations, answer mismatch). Our unknowns are not exam questions — steal the **diagnose-then-score** pattern.

*Generated: 2026-07-25 | Paper: Fu et al. arXiv [2601.10406](https://arxiv.org/abs/2601.10406)*

---

## 1. Finding

Automatic QG eval often black-box/holistic → neglects structural/linguistic/content defects → overestimates quality.

ErrEval: (1) lightweight Error Identifier categorizes errors; (2) diagnostics guide LLM scoring. Improves human alignment; reduces overestimation of low-quality questions.

---

## 2. Transfer

| ErrEval | Our stack |
|---------|-----------|
| Error Identifier | `critique_brief` + `soundness_pass` |
| Informed scoring | Elicit rubric after diagnostics |
| Overestimation risk | Don’t use holistic LLM “novelty” alone ([`CURIOSITY_EVAL_METRICS.md`](CURIOSITY_EVAL_METRICS.md)) |

**Productize:** Eval report should show diagnostics **before** any mean quality score (already partially true with soundness/critique sections).

---

## 3. Related honesty signal

Country-level publication incentives can **narrow topic curiosity** (Chelikavada & Bennett [2501.17150](https://arxiv.org/abs/2501.17150)) — cousin to McNamara/hivemind: external incentives warp what gets asked. Explicit ValueProfile remains the antidote for *our* ranks.

---

## 4. See also

[`SOUNDNESS_PASS_UX.md`](SOUNDNESS_PASS_UX.md) · [`FALSIFYBENCH.md`](FALSIFYBENCH.md) · [`PROBLEM_SELECTION_MCNAMARA.md`](PROBLEM_SELECTION_MCNAMARA.md)
