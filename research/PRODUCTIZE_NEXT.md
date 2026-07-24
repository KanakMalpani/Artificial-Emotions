# Productize next — research → sibling backlog

**Status:** Aggregated, prioritized recommendations from 2026-07-25 research cycles.  
**Owner:** Product/engineering sibling (`src/`, `api.py`, web). Research agent owns notes only.  
**Honesty:** Ordered by leverage × honesty — not a commitment that all ship in v0.x.

*Updated: 2026-07-25*

---

## P0 — high leverage, low overclaim

1. **Elicit A/B eval path** — Implement agent A/B using `examples/elicit_ab_protocol.json` (+ optional rubric rows from [`INVESTIGATION_DESIGN.md`](INVESTIGATION_DESIGN.md)); report investigation-quality deltas. See [`EPISTEMIC_ELICITATION.md`](EPISTEMIC_ELICITATION.md).
2. **Gap-status fixture + metric** — Hand-label 15–30 Qs using `examples/gap_status_fixture_template.json`; report status accuracy and related-but-unanswered recall ([`GAP_VERIFY_METHODS.md`](GAP_VERIFY_METHODS.md), [`CURIOSITY_EVAL_METRICS.md`](CURIOSITY_EVAL_METRICS.md)).
3. **MCP/tool description lint** — Forbid manipulative substrings (`ALWAYS`, `ignore other tools`) in tool schemas ([`AGENT_PLUGIN_UX.md`](AGENT_PLUGIN_UX.md), [`AFFECTIVE_SAFETY.md`](AFFECTIVE_SAFETY.md)).
4. **Prefs summarize + pairwise nudge** — ✅ partially shipped (`0af53f4`); keep pairwise `preferred_over_ids` UX + dual-use clamp ([`PREFERENCE_CALIBRATION.md`](PREFERENCE_CALIBRATION.md), [`DUAL_USE_RANKING.md`](DUAL_USE_RANKING.md)).
5. **Agent card safety blurb** — Not ERS; cues annotation_only; scores not EVSI ([`AFFECTIVE_SAFETY.md`](AFFECTIVE_SAFETY.md), [`VOI_APPROXIMATIONS.md`](VOI_APPROXIMATIONS.md)).

## P1 — clear product value

6. **`compare_profiles` / veto stack** — ✅ core offline compare + productize pass (`0af53f4`); still add Kendall τ + fuller web two-column ([`PROFILE_COMPARE_UX.md`](PROFILE_COMPARE_UX.md)).
7. **Public-demo profile** — Stricter `max_risk` than lab presets ([`DUAL_USE_RANKING.md`](DUAL_USE_RANKING.md)).
8. **Eval report sections** — gap_f1, rank_spearman, elicit_rubric_mean, risk_flags ([`CURIOSITY_EVAL_METRICS.md`](CURIOSITY_EVAL_METRICS.md)).
9. **Inject always includes risk** — Regression test ([`DUAL_USE_RANKING.md`](DUAL_USE_RANKING.md)).
10. **OpenAlex rationale keys only** — `hit_n`, optional `mean_cited_by`, `funder_field_missing_rate` — no silent weight change ([`FUNDING_NEGLECT_SIGNALS.md`](FUNDING_NEGLECT_SIGNALS.md)).
10b. **Mix safety guards** — ✅ soft guards landed (`0af53f4`); keep epistemic-default docs ([`AFFECTIVE_SAFETY.md`](AFFECTIVE_SAFETY.md)).

## P2 — research-facing / moonshot-adjacent

11. **VOI worksheet export** — Emit `examples/voi_worksheet_template.json` filled with question metadata ([`VOI_APPROXIMATIONS.md`](VOI_APPROXIMATIONS.md)).
12. **Cue threshold knobs** on profile for `derive_epistemic_cues` ([`EPISTEMIC_ELICITATION.md`](EPISTEMIC_ELICITATION.md)).
13. **LitGapFinder-style cooccur correlation study** — Offline only vs neglectedness ([`GAP_VERIFICATION_COMPETITORS.md`](GAP_VERIFICATION_COMPETITORS.md)).
14. **Optional cross-model vote** on generate (HybridQuestion-inspired) — costly; offline ([`HYBRID_QUESTION.md`](HYBRID_QUESTION.md)).
15. **Bayesian surprise / lab closed-loop** — Only with posteriors; don’t rename axis ([`BAYESIAN_SURPRISE.md`](BAYESIAN_SURPRISE.md)).
16. **Top-n embedding diversity metric** — Hivemind detector in eval ([`PROBLEM_SELECTION_MCNAMARA.md`](PROBLEM_SELECTION_MCNAMARA.md)).
17. **LIMITS cite McNamara paper** — Why explicit ValueProfile exists ([`PROBLEM_SELECTION_MCNAMARA.md`](PROBLEM_SELECTION_MCNAMARA.md)).

## Explicit non-goals (from research)

- EES runtime API / biometric ERS  
- Fake `scores.evsi`  
- Global preference model across profiles  
- Silent multi-stakeholder “consensus” score  
- Claiming BoxingGym-level experimental design skill  

---

## Research commits this session (main)

| Commit | Topic |
|--------|-------|
| `0eb7581` | Elicitation, competitors, safety, MCP UX, VOI |
| `62c9024` | Preference, ITN, Bayesian surprise |
| `ef47b19` | Dual-use, HybridQuestion |
| `60113b8` | Constitutional curiosity |
| `f487164` | Eval metrics |
| `960160e` | Gap verify methods (SciFact) |
| `f4b62b2` | Funding/OpenAlex neglect |
| `8a78860` | Investigation design / falsifiers |

Index: [`INDEX.md`](INDEX.md) · Sources: [`SOURCES.md`](SOURCES.md)
