# Design rationale — optional

Long-form research that **informed** the product. You do not need these files to install or run Artificial Emotions.

**Product entry:** [`../README.md`](../README.md)  
**Product docs:** [`../docs/`](../docs/) (plugins, limits, architecture, proofs)

| File | What it contributed to the product |
|------|-------------------------------------|
| [FIRST_PRINCIPLES.md](FIRST_PRINCIPLES.md) | Curiosity = EVSI-style investigation selection; six scoring axes; hard invariants |
| [RESEARCH.md](RESEARCH.md) | Product thesis vs Q&A / AI Scientists; VOI, ITN, Bayesian surprise anchors |
| [FAILURE_MODES.md](FAILURE_MODES.md) | F1–F15 mitigations encoded in gates, gap verify, diversity, scoring, tests |
| [SOURCES.md](SOURCES.md) | Annotated bibliography (HybridQuestion, SciMuse, AutoDiscovery, MIRAI, …) |
| [CAPABILITY.md](CAPABILITY.md) | Capability contract: ranked unknowns + ValueProfile — not Q&A / lab automation |
| [HANDOFF.md](HANDOFF.md) | Historical implementation notes (may be stale) |
| [AI_EMOTIONS.md](AI_EMOTIONS.md) | Emotion mechanisms; epistemic elicitation ↔ provoke (not anthropomorphic) |
| [EMOTION_ACCESS.md](EMOTION_ACCESS.md) | Consumer APIs/SDKs/datasets; minimal `/v1/emotions/*` public contract |
| [EMOTION_MIXING.md](EMOTION_MIXING.md) | Mixable catalog / PAD / Plutchik honesty limits |
| [INDEX.md](INDEX.md) | Full research file index (including 2026-07 deep spikes) |
| [PRODUCTIZE_NEXT.md](PRODUCTIZE_NEXT.md) | Aggregated sibling backlog from research cycles |
| [SOURCES.md](SOURCES.md) | Living annotated bibliography |

Deep spikes (elicitation, competitors, safety, VOI, prefs, McNamara, co-scientist, …) are listed in [INDEX.md](INDEX.md).

Where research shows up in code:

- `scoring.py` — geometric weak-link aggregate; anti-McNamara; cost / risk / answerability
- `verify.py` — related ≠ answered; abstract claim/open-gap reading; recency-aware likely-answered
- `diversity.py` — F4/F13 near-duplicate suppression
- `judge.py` — structured rubrics (F5); curiosity ≠ citation forecast
- `provoke.py` / MCP / HTTP — explicit ValueProfile (F11); “not Q&A” agent UX
- `emotions.py` / `/v1/emotions/*` — epistemic cue annotate/elicit/pack (annotation_only)
- `preferences.py` / `compare.py` — pref JSONL + side-by-side profiles
- `tests/test_failure_modes.py` — adversarial coverage for F1–F15
