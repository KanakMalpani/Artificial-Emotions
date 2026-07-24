# Constitution / veto stack — web UX (research)

**Status:** Near-term constitutional curiosity after `compare_profiles` + `examples/constitution_veto_stack.json`.  
**Honesty:** Veto = hard risk ceiling + side-by-side ranks — not a solved social-choice optimum.

*Generated: 2026-07-25 | Background: [`CONSTITUTIONAL_CURIOSITY.md`](CONSTITUTIONAL_CURIOSITY.md)*

---

## 1. Recommended flow

1. User picks **primary** profile (ranks).  
2. Optional **safety veto** profile (`public_demo_strict_risk` or custom `max_risk`).  
3. Show compare table (Kendall τ + rank deltas).  
4. Apply veto: drop/flag items exceeding strictest `max_risk`.  
5. Advisory profiles: annotate only (`show_conflicts`).

Copy: “Stakeholders can disagree — we show conflicts; we don’t invent consensus.”

---

## 2. Productize next

1. Web: “Compare + veto” using existing API.  
2. Load `examples/constitution_veto_stack.json` as preset.  
3. Moonshot only: LLM critique of top-n vs constitution text — eval required ([`INNOEVAL_JUDGES.md`](INNOEVAL_JUDGES.md)).  
4. Credal VOI note when utilities contested ([`VOI_IMPRECISE.md`](VOI_IMPRECISE.md)).

---

## 3. See also

[`PROFILE_COMPARE_UX.md`](PROFILE_COMPARE_UX.md) · `compare.py` veto_tip
