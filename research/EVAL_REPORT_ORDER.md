# Eval report — diagnose-before-score ordering (research)

**Status:** ErrEval pattern applied to `curiosity eval report` ([`ERREVAL_QG.md`](ERREVAL_QG.md)).  
**Honesty:** Section order is UX for readers of the report — not a claim that diagnostics are complete ScholarEval.

*Generated: 2026-07-25*

---

## 1. Recommended section order

1. Honesty / profile / n  
2. **Diagnostics:** critique issue rates, soundness pass/revise/fail, dual-use flags  
3. **Gap:** status accuracy / related≠answered metrics  
4. **Rank:** Spearman / Kendall vs labels or prefs  
5. **Elicit:** rubric means  
6. **Hivemind:** mean/max pairwise similarity  
7. Holistic means last (if any)

Do not lead with a single “quality score.”

---

## 2. Productize next

1. Sibling `eval_report.py` — enforce order if not already.  
2. CI: fail if report omits dual-use section when fixtures present.  
3. Link ErrEval + RINoBench caveats in report footer.

---

## 3. See also

[`CURIOSITY_EVAL_METRICS.md`](CURIOSITY_EVAL_METRICS.md) · [`SOUNDNESS_PASS_UX.md`](SOUNDNESS_PASS_UX.md) · [`HIVEMIND_METRIC_SPEC.md`](HIVEMIND_METRIC_SPEC.md)
