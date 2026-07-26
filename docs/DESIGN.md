# Design (short)

Artificial Emotions is a **curiosity layer**: generate → verify → score → diversify → brief.

It is **not** literature Q&A, citation forecasting, or an end-to-end AI Scientist.

## Invariants

1. Explicit `ValueProfile` — no value-free ranking  
2. Related literature ≠ answered  
3. Answerability / risk / likely-answered gates before top-N  
4. Near-duplicate suppression  
5. Scores are estimates with confidence bands — never oracles  

## Where to read more

| Need | Doc |
|------|-----|
| Docs index | [INDEX.md](INDEX.md) |
| Install / plugins | [PLUGINS.md](PLUGINS.md) |
| Emotions | [EMOTIONS.md](EMOTIONS.md) — epistemic cues are `annotation_only`; percentage mixes emit `computational_affect` / `felt_simulation`, not biological consciousness or user-affect measurement |
| Honest bounds | [LIMITS.md](LIMITS.md) |
| Demo commands | [PROOFS.md](PROOFS.md) |
| Modules | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Roadmap skim | [ROADMAP_SUMMARY.md](ROADMAP_SUMMARY.md) |
