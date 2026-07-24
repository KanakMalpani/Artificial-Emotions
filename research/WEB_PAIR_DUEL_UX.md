# Suggest-next-duel — web feedback bar UX (research)

**Status:** Companion to sibling “Suggest next duel” (`b7f152a`) and [`SUGGEST_NEXT_PAIR.md`](SUGGEST_NEXT_PAIR.md).  
**Honesty:** Heuristic pairing for **this profile** — not Swiss InfoGain paper fidelity until eval shows lift.

*Generated: 2026-07-25*

---

## 1. Recommended UI

| Element | Copy / behavior |
|---------|-----------------|
| Button | **Suggest next duel** |
| Cards | Side-by-side briefs + Prefer A / Prefer B / Tie / Skip |
| Reason chip | Show strategy (`medium_delta` / `connect_components`) in plain language |
| Footer | “Calibrates this ValueProfile only — not universal science priority.” |
| Exhausted | “No more informative pairs in top-k — try regenerate or another profile.” |

Always show dual-use/risk on both sides if present.

---

## 2. Telemetry (privacy-safe)

Log counts only: pairs shown, ties, skips, prefers — **not** free-text unless user opts into notes. Profile-scoped JSONL already fits PreferenceEvent.

---

## 3. Productize next

1. Tie button → `relation: tie` (if not wired).  
2. Eval: annotation efficiency vs random pairs ([`PREFERENCE_BT_STAGE2.md`](PREFERENCE_BT_STAGE2.md)).  
3. Cap duels/session on `public_demo_*`.  
4. Don’t auto-apply weight hints without “Apply suggested deltas” confirm.

---

## 4. See also

[`PREFERENCE_CALIBRATION.md`](PREFERENCE_CALIBRATION.md) · [`OUTCOME_FLYWHEEL.md`](OUTCOME_FLYWHEEL.md) · [`PROFILE_COMPARE_UX.md`](PROFILE_COMPARE_UX.md)
