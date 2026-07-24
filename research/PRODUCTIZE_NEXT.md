# Productize next — research → sibling backlog

**Status:** Aggregated, prioritized recommendations from 2026-07-25 research cycles.  
**Owner:** Product/engineering sibling (`src/`, `api.py`, web). Research agent owns notes only.  
**Honesty:** Ordered by leverage × honesty — not a commitment that all ship in v0.x.

*Updated: 2026-07-25*

---

## P0 — high leverage, low overclaim

1. **Elicit A/B eval path** — ✅ landed (`874dd7a`); keep rubric optional rows ([`EPISTEMIC_ELICITATION.md`](EPISTEMIC_ELICITATION.md)).
2. **Gap-status fixture + metric** — ✅ gap-status metric (`874dd7a`); grow hand-labels + VERITAS cousins ([`GAP_VERIFY_METHODS.md`](GAP_VERIFY_METHODS.md), [`VERITAS_EPISTEMIC_LABELS.md`](VERITAS_EPISTEMIC_LABELS.md)).
3. **MCP/tool description lint** — ✅ landed (`2a33786` / `mcp_lint.py`); keep CI green ([`MCP_DESCRIPTION_LINT.md`](MCP_DESCRIPTION_LINT.md), [`MCP_THREAT_TAXONOMY.md`](MCP_THREAT_TAXONOMY.md)).
4. **Prefs summarize + pairwise nudge** — ✅ ties + suggest-pair + gated BT (`27eb346`) ([`SUGGEST_NEXT_PAIR.md`](SUGGEST_NEXT_PAIR.md), [`PREFERENCE_BT_STAGE2.md`](PREFERENCE_BT_STAGE2.md)).
5. **Agent card safety blurb** — Still open: merge [`AGENT_CARD_COPY.md`](AGENT_CARD_COPY.md) into `/v1/agent` + LIMITS patches ([`LIMITS_PATCHES.md`](LIMITS_PATCHES.md)).

## P1 — clear product value

6. **`compare_profiles` / veto stack** — ✅ (`bc7ffa9`, `874dd7a`).
7. **Public-demo profile** — ✅ `public_demo_strict_risk` (`bc7ffa9`).
8. **Eval report sections** — ✅ (`2a33786`); ensure hivemind section wired ([`HIVEMIND_METRIC_SPEC.md`](HIVEMIND_METRIC_SPEC.md)).
9. **Inject always includes risk** — ✅ (`bc7ffa9`).
10. **OpenAlex rationale keys only** — ✅ (`874dd7a`).
10b. **Mix safety guards** — ✅ (`0af53f4`).
10c. **Top-n hivemind similarity metric** — ✅ (`044c75e` / `hivemind.py`).
10d. **Optional `critique_brief`** — ✅ (`2a33786`).
10e. **Outcome labels in prefs summarize** — ✅ (`044c75e`).
10f. **Gap fixture underpowered / invalid_form** — Template v0.2 ready (`examples/gap_status_fixture_template.json`); grow hand-labels.

## P2 — research-facing / moonshot-adjacent

11. **VOI worksheet export** — ✅ (`2a33786`); optional credal/compare note ([`VOI_IMPRECISE.md`](VOI_IMPRECISE.md)).
12. **Cue threshold knobs** — ✅ (`044c75e`); presets JSON ([`CUE_THRESHOLD_KNOBS.md`](CUE_THRESHOLD_KNOBS.md)).
13. **LitGapFinder cooccur correlation study** — ✅ helpers landed (`04eeebf`); run offline protocol ([`LITGAP_CORRELATION_STUDY.md`](LITGAP_CORRELATION_STUDY.md)).
14. **Optional cross-model vote** — Offline protocol ([`HYBRID_VOTE_OFFLINE.md`](HYBRID_VOTE_OFFLINE.md)); not default API.
15. **Bayesian surprise closed-loop** — Only with posteriors ([`BAYESIAN_SURPRISE.md`](BAYESIAN_SURPRISE.md)).
16. **LIMITS cite McNamara / EVSI / ERS** — [`LIMITS_PATCHES.md`](LIMITS_PATCHES.md).
17. **Optional idea-graph export** — EIG-inspired debug JSON ([`EIG_IDEATION_GRAPHS.md`](EIG_IDEATION_GRAPHS.md)).
18. **Mix intensity cap (optional)** — Cap non-epistemic mix weights ([`EMOTION_MIXING_ADDENDUM.md`](EMOTION_MIXING_ADDENDUM.md)).

## Explicit non-goals (from research)

- EES runtime API / biometric ERS  
- Fake `scores.evsi`  
- Global preference model across profiles  
- Silent multi-stakeholder “consensus” score  
- Claiming BoxingGym-level experimental design skill  
- Claiming MCP-38 / MSB “compliance”

---

## Living pointers

Index: [`INDEX.md`](INDEX.md) · Sources: [`SOURCES.md`](SOURCES.md)

Recent research commits: `78180e6` LIMITS patches · `fe3e7a4` BT/VERITAS/VOI · `27446b3` cue/hivemind specs · `464715a` LitGap/pair UX · `2906fe4` MCP threats · `6c01702` EIG + gap template
