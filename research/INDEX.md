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
| [NEGLECTEDNESS_COST.md](NEGLECTEDNESS_COST.md) | Neglectedness / cost proxy spike notes |
| [README.md](README.md) | Archive orientation |

## Product code

| Path | Role |
|------|------|
| `src/artificial_curiosity/` | Curiosity engine (generate → verify → score → rank → brief) |
| `tests/` | Unit + failure-mode adversarial tests |
| `examples/` | Offline/literature experiment JSON + eval harness |
| `docs/` | Product docs (PLUGINS, LIMITS, ARCHITECTURE, PROOFS) |
| `web/` | UI for ranked unknowns |
