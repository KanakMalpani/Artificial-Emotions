# Outcome tracking flywheel (research)

**Status:** Extends [`PREFERENCE_CALIBRATION.md`](PREFERENCE_CALIBRATION.md) toward HANDOFF “longitudinal calibration.”  
**Honesty:** Sparse outcomes; selection bias (users only report some results); not a closed-loop lab.

*Generated: 2026-07-25*

---

## 1. Event types that close the loop

| `event_type` | Meaning | Downstream use |
|--------------|---------|----------------|
| `prefer` / `reject` | Ranking taste | Weight hints / BT later |
| `already_answered` | Verify false-unknown (F1) | Gap eval negatives |
| `keep` | Neutral keep in shortlist | Weak positive |
| `outcome` | Something happened after pursue | Calibration gold (rare) |
| `note` | Free text | Human audit only |

---

## 2. Outcome schema nudge

```json
{
  "event_type": "outcome",
  "question_id": "q_…",
  "profile_name": "alignment_lab",
  "labels": {
    "result": "partial_progress | null | contradicted | answered_elsewhere | abandoned",
    "months_elapsed": "6"
  },
  "notes": "Pilot showed X; enabling question Y remains."
}
```

---

## 3. Metrics (when n≥20 outcomes)

| Metric | Definition |
|--------|------------|
| Prefer→progress rate | Among preferred, fraction with non-abandoned outcomes |
| High-score miss rate | Top-quartile curiosity_score later `already_answered` |
| Risk false negative | `dual_use_high` later pursued without review |

Report with huge confidence intervals; never ship as “calibration certificate.”

---

## 4. Productize next (sibling)

1. Document outcome labels in prefs docs / example JSONL.  
2. `prefs summarize` includes outcome breakdown.  
3. Annual (or N≥20) calibration report generator — v1.x flywheel.  
4. Do not auto-retrain ranks from outcomes without human review.  

---

## 5. See also

- Ideation–execution gap ([`CURIOSITY_EVAL_METRICS.md`](CURIOSITY_EVAL_METRICS.md))  
- AutoResearchClaw Pivot/Refine ([`CRITIC_DEBATE_JUDGES.md`](CRITIC_DEBATE_JUDGES.md))  
- `preferences.py`  
