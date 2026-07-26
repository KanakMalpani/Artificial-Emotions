# Constitutional / multi-stakeholder curiosity (moonshot)

**Status:** Spike for ROADMAP §7.6 *Constitutional curiosity* — multi-stakeholder `ValueProfile` negotiation.  
**Honesty:** Multiple stakeholders disagree on what is “valuable.” A constitution is a **declared constraint set**, not a solved social-choice problem. Do not ship “the one true science priority.”

*Generated: 2026-07-25 | Sources: Multi-stakeholder recsys; Constitutional AI uses; FIRST_PRINCIPLES | Confidence: Medium — thin direct literature on science-question constitutions.*

---

## 1. Executive summary

Artificial Emotions already requires an explicit `ValueProfile`. Constitutional curiosity would let **several** profiles (funder, lab, public safety, domain community) constrain or blend ranks — similar in spirit to Constitutional AI’s principle lists and to multi-stakeholder recommender systems (providers, consumers, society). Practical near-term: **profile sets + veto rules** (e.g. safety profile `max_risk` is a hard floor) rather than opaque scalar blends of incompatible values.

---

## 2. Analogies that help

| Field | Idea | Transfer |
|-------|------|----------|
| **Constitutional AI** | Critique/revise against written principles | Profiles as readable principles; optional LLM critique of ranked lists vs constitution text |
| **Multi-stakeholder RS** (Abdollahpouri & Burke [1907.13158](https://arxiv.org/abs/1907.13158)) | Fairness across parties | Separate objectives; avoid single utility |
| **EthicAlly / REC support** ([2508.00856](https://arxiv.org/abs/2508.00856)) | Structured ethics without replacing humans | Same stance: assist ValueProfile design, don’t automate ethics boards |
| **MimiTalk dual-agent CAI** ([2511.03731](https://arxiv.org/abs/2511.03731)) | Supervisor + worker agents | Optional: “constitution supervisor” checks provoke injects |

---

## 3. Design options (honesty-ordered)

### A. Hard veto stack (recommended first)

```text
rank under primary_profile
then drop/flag items failing safety_profile.max_risk
then optionally annotate conflict with community_profile
```

No fake Pareto optimum.

### B. Explicit multi-score table

Return per-profile scores side-by-side; human/agent picks. Matches HybridQuestion “human foresight” need.

### C. Soft weight blend

Average weights across stakeholders — **only** when stakeholders agree they share a utility scale (rare). Document as experimental.

### D. Forbidden

Silent merge into one score labeled “consensus.”

---

## 4. Minimal constitution schema (research)

```json
{
  "constitution_id": "lab_public_demo",
  "stakeholders": [
    {"role": "primary", "profile_name": "alignment_lab"},
    {"role": "safety_veto", "profile_name": "public_demo_strict_risk"},
    {"role": "advisory", "profile_name": "funder_10y"}
  ],
  "rules": [
    "safety_veto.max_risk is hard ceiling",
    "primary drives ranking weights",
    "advisory scores shown but do not reorder unless flag show_conflicts"
  ]
}
```

---

## 5. Productize next (sibling)

1. **Document veto pattern** — ✅ `compare.py` veto_tip + docs.  
2. **`compare_profiles` tool** — ✅ landed.  
3. **Constitution JSON example** — ✅ `examples/constitution_veto_stack.json`.  
4. **Web compare + veto UX** — [`CONSTITUTION_WEB_UX.md`](CONSTITUTION_WEB_UX.md).  
5. Moonshot only: LLM self-critique of top-n against constitution text — eval required.

---

## 6. See also

- [`FIRST_PRINCIPLES.md`](FIRST_PRINCIPLES.md) — no value-free ranking  
- [`PREFERENCE_CALIBRATION.md`](PREFERENCE_CALIBRATION.md) — per-profile learning only  
- [`DUAL_USE_RANKING.md`](DUAL_USE_RANKING.md) — safety as stakeholder  
- [`HYBRID_QUESTION.md`](HYBRID_QUESTION.md) — human oversight stages  
