# Multi-stakeholder feasible sets & value pluralism (research)

**Status:** Deepens [`CONSTITUTIONAL_CURIOSITY.md`](CONSTITUTIONAL_CURIOSITY.md) / [`CONSTITUTION_WEB_UX.md`](CONSTITUTION_WEB_UX.md).  
**Honesty:** Hiring RS fairness literature ≠ science priority — steal **pluralism mechanics**, not domain metrics.

*Generated: 2026-07-25*

---

## 1. Behavioural feasible set (Park 2026) — [2603.21435](https://arxiv.org/abs/2603.21435)

When orgs adopt commercial AI decision support, they inherit **vendor-embedded values**. Park formalizes a **behavioural feasible set**: recommendations reachable under vendor alignment constraints. Alignment **compresses** the set; multi-stakeholder ranking tasks show alignment **shifts** implied stakeholder priorities rather than neutralizing them. Prompting cannot fully recover lost trade-offs.

**Transfer:** Explicit `ValueProfile` + compare/veto is our way to make the feasible set **user-declared**. Hidden default profiles would be vendor-style compression. Public demo strict risk = intentional compression for safety.

---

## 2. Multi-sided fairness in recommenders

Kaya & Bogers ([2508.00908](https://arxiv.org/abs/2508.00908)): algorithmic hiring needs **multi-stakeholder** fairness definitions co-designed with job seekers, companies, recruiters — single-side fairness insufficient.

Schellingerhout ([2410.00654](https://arxiv.org/abs/2410.00654)): explainable multi-stakeholder job RS — explainability + pluralism.

**Transfer:** `compare_profiles` + veto_tip + advisory annotations ≈ multi-sided view without fake consensus score.

---

## 3. Productize next

1. Web constitution flow using `examples/constitution_veto_stack.json`.  
2. Agent card: “Selecting a profile selects which trade-offs are negotiable.”  
3. Never ship silent consensus blend.  
4. Document that LLM alignment (host model) further compresses feasible ranks — curiosity layer can’t undo host refusals.

---

## 4. Key citations

| Work | ID |
|------|-----|
| Behavioural feasible set | arXiv 2603.21435 |
| Multi-sided hiring fairness | arXiv 2508.00908 |
| Explainable multi-stakeholder job RS | arXiv 2410.00654 |
| In-repo | `compare.py`, constitution example JSON |
