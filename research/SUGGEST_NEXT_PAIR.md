# Suggest-next-pair UX — active preference collection (research)

**Status:** Thin UX wedge bridging [`PREFERENCE_BT_STAGE2.md`](PREFERENCE_BT_STAGE2.md) and shipped prefs summarize.  
**Honesty:** Info-gain pairing is a **heuristic**; not Swiss InfoGain paper fidelity until eval proves lift.

*Generated: 2026-07-25*

---

## 1. Job to be done

User (or agent) has a ranked top-k under a profile. Instead of random “which do you prefer?”, propose **one duel** that most reduces uncertainty about weight hints / future BT skills.

---

## 2. Minimal algorithm (v0)

Inputs: top-k `RankedQuestion`s with axis scores; existing `preferred_over_ids` graph.

1. Build undirected graph of compared pairs.  
2. Candidate edges = pairs among top-k not yet compared (and not tied).  
3. Score each candidate by a simple **disagreement proxy**:
   - Absolute difference in weighted total score (large Δ → easy; prefer **medium Δ** for info), **or**
   - Axes where profile weights are highest but items disagree most.  
4. Prefer pairs that connect **disconnected components** (identifiability for later BT).  
5. Return `{left_id, right_id, reason, profile_name}` — UI shows both briefs + Prefer A / Prefer B / Tie / Skip.

Swiss InfoGain (arXiv [2511.12796](https://arxiv.org/abs/2511.12796)) is the north-star name; v0 = connectivity + medium score-gap is enough.

---

## 3. API / MCP sketch (sibling)

```text
suggest_next_pair(profile_name, question_ids[] | top_k=10) ->
  { left, right, strategy: "medium_delta"|"connect_components", honesty }
```

- Does not change ranks.  
- Logs nothing until user submits PreferenceEvent.  
- Refuse if k<2 or all pairs exhausted → `{done: true}`.

---

## 4. Copy / safety

- “Helps calibrate **this profile’s** weights — not a universal science ranking.”  
- Always show dual-use/risk badges on both sides if present.  
- Public demo: cap duels / session.

---

## 5. Productize next

1. `suggest_next_pair` tool + web duel widget.  
2. PreferenceEvent `relation: tie`.  
3. Eval: annotation efficiency — Spearman stability vs #pairs for random vs suggest_next_pair.

---

## 6. See also

[`PREFERENCE_CALIBRATION.md`](PREFERENCE_CALIBRATION.md) · [`OUTCOME_FLYWHEEL.md`](OUTCOME_FLYWHEEL.md) · [`PROFILE_COMPARE_UX.md`](PROFILE_COMPARE_UX.md)
