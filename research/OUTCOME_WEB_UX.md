# Outcome labels — web / prefs summarize UX (research)

**Status:** Extends [`OUTCOME_FLYWHEEL.md`](OUTCOME_FLYWHEEL.md) after sibling outcome-in-summarize landing.  
**Honesty:** Sparse, selection-biased; not a lab closed-loop or calibration certificate.

*Generated: 2026-07-25*

---

## 1. Recommended capture UI

| Control | Behavior |
|---------|----------|
| Outcome picker | `partial_progress` / `null` / `contradicted` / `answered_elsewhere` / `abandoned` |
| Months elapsed | Optional int |
| Note | Optional short text |
| Confirm | Explicit submit → PreferenceEvent |

Show only on items user previously preferred/kept — reduces noise.

---

## 2. Summarize panel

- Counts by outcome label (not averages of curiosity_score as “accuracy”).  
- Link high-score → `already_answered` as **verify miss** candidates.  
- Disclaimer: “n is small; not a performance certificate.”

Archive honesty cousin: public evals are selective time series ([2606.17005](https://arxiv.org/abs/2606.17005)) — don’t present terminal snapshots as destiny.

---

## 3. Productize next

1. Web outcome picker if missing.  
2. Pair with Bayesian surprise worksheet optionally ([`BAYESIAN_SURPRISE.md`](BAYESIAN_SURPRISE.md)).  
3. Never auto-tune weights from n<20 outcomes.

---

## 4. See also

[`PREFERENCE_CALIBRATION.md`](PREFERENCE_CALIBRATION.md) · [`WEB_PAIR_DUEL_UX.md`](WEB_PAIR_DUEL_UX.md)
