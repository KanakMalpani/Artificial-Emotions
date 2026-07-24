# Research Index (archived)

> **Not required to use the product.** Start at [`../README.md`](../README.md).

Everything under `research/` is design/background material that informed the implementation.

| File | Contents |
|------|----------|
| [FIRST_PRINCIPLES.md](FIRST_PRINCIPLES.md) | Decision-theoretic definition of curiosity; scoring axes; invariants |
| [RESEARCH.md](RESEARCH.md) | Full research report + competitive landscape |
| [SOURCES.md](SOURCES.md) | Annotated bibliography with code mapping |
| [FAILURE_MODES.md](FAILURE_MODES.md) | F1–F15 failures and mitigations |
| [CAPABILITY.md](CAPABILITY.md) | Implementation-ready capability contract |
| [HANDOFF.md](HANDOFF.md) | Historical agent notes (may be stale) |
| [AI_EMOTIONS.md](AI_EMOTIONS.md) | Emotions in AI — taxonomies, production mechanisms, epistemic emotions ↔ provoke (not anthropomorphic) |
| [EMOTION_ACCESS.md](EMOTION_ACCESS.md) | Consumer access patterns — APIs/SDKs/datasets; minimal public emotions contract |
| [EMOTION_MIXING.md](EMOTION_MIXING.md) | Blends / PAD interpolation / Plutchik dyads; % mix API justification + honesty limits |
| [EPISTEMIC_ELICITATION.md](EPISTEMIC_ELICITATION.md) | EES / incongruity measurement → provoke A/B eval protocol |
| [GAP_VERIFICATION_COMPETITORS.md](GAP_VERIFICATION_COMPETITORS.md) | Lit gap / idea-rank competitor map (SciMuse, ScholarEval, LitGapFinder, …) |
| [AFFECTIVE_SAFETY.md](AFFECTIVE_SAFETY.md) | Anyone-can-use safety: AI Act ERS vs annotation; MCP manipulation |
| [AGENT_PLUGIN_UX.md](AGENT_PLUGIN_UX.md) | MCP / tool-calling UX for curiosity layers |
| [NEGLECTEDNESS_COST.md](NEGLECTEDNESS_COST.md) | Neglectedness / cost proxy spike notes |
| [VOI_APPROXIMATIONS.md](VOI_APPROXIMATIONS.md) | ISPOR/ConVOI EVSI methods → honest proxy vs adapter paths |
| [PREFERENCE_CALIBRATION.md](PREFERENCE_CALIBRATION.md) | Preference JSONL → profile-scoped LTR/BT ladder |
| [NEGLECTEDNESS_ITN.md](NEGLECTEDNESS_ITN.md) | ITN / EA neglectedness addendum for proxies |
| [BAYESIAN_SURPRISE.md](BAYESIAN_SURPRISE.md) | AutoDiscovery surprisal vs score-axis surprise |
| [README.md](README.md) | Archive orientation |

## Product code

| Path | Role |
|------|------|
| `src/artificial_curiosity/` | Curiosity engine (generate → verify → score → rank → brief) |
| `tests/` | Unit + failure-mode adversarial tests |
| `examples/` | Offline/literature experiment JSON + eval harness |
| `docs/` | Product docs (PLUGINS, LIMITS, ARCHITECTURE, PROOFS) |
| `web/` | UI for ranked unknowns |
