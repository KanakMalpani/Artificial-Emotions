# Research Index

Everything for this project is under:

`<local-clone>`

## Docs (research + design)

| File | Contents |
|------|----------|
| [FIRST_PRINCIPLES.md](FIRST_PRINCIPLES.md) | Decision-theoretic definition of curiosity; scoring axes; invariants |
| [RESEARCH.md](RESEARCH.md) | Full research report + competitive landscape |
| [SOURCES.md](SOURCES.md) | Annotated bibliography with code mapping |
| [FAILURE_MODES.md](FAILURE_MODES.md) | F1–F15 failures and mitigations |
| [LIMITS.md](LIMITS.md) | Verified working vs known gaps |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Pipeline modules and trust boundaries |
| [CAPABILITY.md](CAPABILITY.md) | Implementation-ready capability contract |
| [INDEX.md](INDEX.md) | This file |

## Code (implements the research)

| Path | Role |
|------|------|
| `src/artificial_curiosity/` | Curiosity engine (generate → verify → score → rank → brief) |
| `tests/` | Unit + failure-mode adversarial tests |
| `examples/` | Offline/literature experiment JSON + eval harness |
| `web/` | UI for ranked unknowns |

## Experiment artifacts already in-repo

- `examples/run_ai_offline.json`
- `examples/run_ai_literature.json`
- `examples/_run_compare.py`
- `examples/eval_harness.py`
