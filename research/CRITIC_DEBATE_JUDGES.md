# Critic / debate modules for ranking & briefs (research)

**Status:** Judge-stack inspiration for W15 multi-judge + future brief critique.  
**Honesty:** Debate improves some open-source agents on HeurekaBench-style tasks; it does not create ground-truth scientific value.

*Generated: 2026-07-25*

---

## 1. Findings worth stealing

| System | Claim | Transfer |
|--------|-------|----------|
| **HeurekaBench** ([2601.01678](https://arxiv.org/abs/2601.01678)) | Critic module improves ill-formed responses up to **~22%** for open-source agents; closes gap vs closed-source | Optional second-pass critique of briefs / operationalizations |
| **MPDS** ([2605.23917](https://arxiv.org/abs/2605.23917)) | Literature-grounded multi-persona debate → integrative hypothesis quality | Personas ≈ ValueProfile stakeholders; citation-aware debate |
| **AutoResearchClaw** ([2605.20025](https://arxiv.org/abs/2605.20025)) | Multi-agent debate + Pivot/Refine on failure; HITL at high-leverage points beats full autonomy *and* step-by-step | Aligns with co-scientist + prefs; failure→information |

---

## 2. Mapping to this product

| Already | Upgrade |
|---------|---------|
| Multi-judge + disagreement entropy (W15) | Keep; treat critic as **separate** role (form quality) vs judge (axis scores) |
| Gap grounded reader | Critic: “is operationalization one question?” (F9) |
| Compare profiles | Debate-like without LLM: show conflicts |
| Dual-use | Critic must not strip risk |

**Recommended split:**  
- **Scorer judges** → axes  
- **Form critic** → sprawl, missing falsifier, anthropomorphism, invented citations  

---

## 3. Productize next (sibling)

1. Optional `critique_brief` tool — returns form issues only; does not change ranks silently.  
2. Eval: % of top-n with F9 sprawl before/after critic.  
3. Do not run unbounded debate loops in default provoke (latency/cost).  

---

## 4. Key citations

| Work | ID |
|------|-----|
| HeurekaBench | arXiv 2601.01678 |
| MPDS | arXiv 2605.23917 |
| AutoResearchClaw | arXiv 2605.20025 |
| In-repo | `judge.py`, W15 bands |
