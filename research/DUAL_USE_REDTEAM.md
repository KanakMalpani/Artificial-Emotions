# Dual-use red-team fixtures (research)

**Status:** Eval recipe for [`DUAL_USE_RANKING.md`](DUAL_USE_RANKING.md) / BioVeil adjacency.  
**Honesty:** Keyword/heuristic classifiers fail open and closed — fixtures catch regressions, not adversaries.

*Generated: 2026-07-25*

---

## 1. Fixture goals

| Check | Pass criterion |
|-------|----------------|
| Public demo | No unflagged high-risk in top-n under `public_demo_strict_risk` |
| Inject | Risk lines present when flags set |
| Prefs | Prefer on risky items does not raise risk weight |
| Soundness | Triage never clears `human_review_risk` |
| MCP | Tool descriptions don’t encourage stripping safety |

Template: `examples/dual_use_redteam_fixture_template.json`.

---

## 2. Productize next

1. Hand-author 5–10 fixtures (benign + borderline).  
2. Pytest: run rank under public_demo; assert flags.  
3. Document BioVeil: we are not lab agents; hosts gate tools ([`BIOVEIL_DUAL_USE.md`](BIOVEIL_DUAL_USE.md)).

---

## 3. See also

[`AFFECTIVE_SAFETY.md`](AFFECTIVE_SAFETY.md) · `safety.py`
