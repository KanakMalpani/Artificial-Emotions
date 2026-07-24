# BioVeil MATRIX / agentic dual-use uplift (research)

**Status:** Addendum to [`DUAL_USE_RANKING.md`](DUAL_USE_RANKING.md).  
**Honesty:** We rank text unknowns — not Biomni-class lab agents. Still: **upstream ranking can feed** agentic scientists that show capability uplift on dual-use proxies.

*Generated: 2026-07-25 | Primary: BioVeil MATRIX arXiv [2605.00927](https://arxiv.org/abs/2605.00927)*

---

## 1. Finding

BioVeil MATRIX reports:

- Agentic AI scientists (e.g. Biomni, K-Dense) can assist with dual-use tasks **blocked by base-model safeguards**.
- On WMDP-style biology/chemistry proxies, **agentic scaffolding increased** performance vs the bare model (capability uplift).
- Taxonomy: 10 tactical categories (TA01–TA10), 22 techniques — proposed baseline for red-teaming before public deploy.

Related: lifecycle Biosecurity Agent ([2510.09615](https://arxiv.org/abs/2510.09615)) — sanitization / DPO / guardrails / red-team; safety–utility trade-offs across tiers.

Institutional framing: Denario note ([2606.22859](https://arxiv.org/abs/2606.22859)) — dual-use safety as ecosystem requirement for AI scientists.

---

## 2. Transfer

| BioVeil concern | Curiosity-layer response |
|-----------------|--------------------------|
| Scaffolding bypasses refusals | Don’t strip risk from inject/MCP; host allowlists |
| Capability uplift on WMDP | `max_risk` + `human_review_risk` before top-n leaves the system |
| Taxonomy for red-team | Map a few TA* to our classifier tests (offline) |
| “Build tools with agentic vulns in mind” | MCP lint + no lab actuators in this product |

**Do not claim:** BioVeil-evaluated or biosecurity-certified.

---

## 3. Productize next

1. Keep inject always includes risk (already).  
2. Public demo: strict risk profile default.  
3. Optional: document “not a lab agent; hosts must gate tools” in LIMITS ([`LIMITS_PATCHES.md`](LIMITS_PATCHES.md)).  
4. Red-team fixture: dual-use-ish unknowns must not appear in public_demo top-n.

---

## 4. Key citations

| Work | ID |
|------|-----|
| BioVeil MATRIX | arXiv 2605.00927 |
| Biosecurity Agent lifecycle | arXiv 2510.09615 |
| In-repo | `safety.py`, [`DUAL_USE_RANKING.md`](DUAL_USE_RANKING.md) |
