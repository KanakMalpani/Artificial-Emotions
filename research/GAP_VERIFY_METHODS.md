# Gap verification methods — related ≠ answered (deepening)

**Status:** Method note for `verify.py` / W12 grounded gap reader. Complements [`GAP_VERIFICATION_COMPETITORS.md`](GAP_VERIFICATION_COMPETITORS.md).  
**Honesty:** SciFact-style systems verify **claims against abstracts**, not “is this research question valuable?” Inversion: we need “does literature **already settle** this question?” which is harder and under-benchmarked.

*Generated: 2026-07-25 | Sources: SciFact, SciFact-Open, DeepSciVerify, SciClops | Confidence: High on claim-verify literature; Medium on direct transfer.*

---

## 1. Executive summary

Scientific **claim verification** (SUPPORTS / REFUTES / NEI) is mature relative to **open-question verification**. Our pipeline correctly refuses to equate retrieval neighborhood with answeredness, using overlap gates + claim/open-gap phrase reading + optional grounded LLM. Borrow from SciFact: evidence pooling, open-domain F1 drops, special-case support. Do **not** treat a SUPPORTS label on a *related* claim as answering our question — require question–claim alignment first.

---

## 2. Literature toolkit

| System | Task | Lesson for us |
|--------|------|---------------|
| **SciFact** ([2004.14974](https://arxiv.org/abs/2004.14974)) | Claim → SUPPORTS/REFUTES + rationales from abstracts | Gold pattern for evidence labels; domain adaptation matters |
| **SciFact-Open** ([2210.13777](https://arxiv.org/abs/2210.13777)) | Same task on ~500K abstracts; pooling annotation | Open-domain ≥15 F1 drop; special-case support phenomena |
| **DeepSciVerify** ([2605.27710](https://arxiv.org/abs/2605.27710)) | Claim–citation alignment; abstract first, escalate to full text | Two-stage escalation mirrors our cheap lexicons → LLM reader |
| **SciClops** ([2110.13090](https://arxiv.org/abs/2110.13090)) | Extract/cluster/contextualize scientific claims for fact-checkers | Clustering related claims — careful not to merge distinct Qs |
| **LitGapFinder** | Structural co-occurrence gaps | Different object (links), not claim settle |

---

## 3. Formal objects (keep distinct)

| Object | Definition | Our status enum cousin |
|--------|------------|------------------------|
| Claim C | Assertive proposition | — |
| Evidence E | Abstract/passage | `LiteratureHit` |
| Verify(C,E) | SUPPORTS / REFUTES / NEI | SciFact |
| Question Q | Interrogative unknown | `UnansweredQuestion` |
| Settled(Q) | ∃C aligned to Q with strong SUPPORTS in lit | `ANSWERED` / `PARTIALLY_ANSWERED` |
| Related(Q) | Hits in embedding/keyword neighborhood | Necessary ≠ sufficient |

**Bug class we already fight:** Related(Q) ∧ ¬Settled(Q) mislabeled as answered.

---

## 4. Mapping to `verify.py`

| Mechanism now | Upgrade path (sibling) |
|---------------|------------------------|
| Token overlap thresholds | Calibrate on labeled fixture (see eval metrics doc) |
| `_ANSWER_CLAIM` / `_OPEN_GAP` lexicons | Expand carefully; measure FP/FN |
| Grounded LLM gap reader (W12) | Require cited titles ∈ retrieved set (already philosophy) |
| Multi-source merge (W11) | Pooling like SciFact-Open |
| — | Optional: map Q→candidate claim paraphrase, then SciFact-style check |

---

## 5. Productize next (sibling)

1. **Fixture:** 15 questions with gold `GapStatus` + 1–3 key abstracts.  
2. **Metric:** status accuracy + “related-but-unanswered” recall.  
3. **Escalation flag:** when lexicon NEI and overlap mid, call LLM reader (DeepSciVerify pattern).  
4. **LIMITS:** cite SciFact-Open generalization drop — our OpenAlex slice is not exhaustive.  
5. Do not ship a public “SciFact-compatible” API unless tests exist.

---

## 6. Key citations

| Work | ID |
|------|-----|
| SciFact | arXiv 2004.14974 |
| SciFact-Open | arXiv 2210.13777 |
| DeepSciVerify | arXiv 2605.27710 |
| SciClops | arXiv 2110.13090 |
| In-repo | `verify.py`, FAILURE_MODES F1/F7 |
