# Design (short)

Artificial Curiosity is a **curiosity layer**: generate → verify → score → diversify → brief.

It is **not** literature Q&A, citation forecasting, or an end-to-end AI Scientist.

## Invariants (from research)

1. Explicit `ValueProfile` — no value-free ranking  
2. Related literature ≠ answered  
3. Answerability / risk / likely-answered gates before top-N  
4. Near-duplicate suppression  
5. Scores are estimates with confidence bands — never oracles  

## Where to read more

| Need | Doc |
|------|-----|
| Install / plugins | [PLUGINS.md](PLUGINS.md) |
| Honest bounds | [LIMITS.md](LIMITS.md) |
| Demo commands | [PROOFS.md](PROOFS.md) |
| Modules | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Full design rationale (optional) | [`research/`](../research/) |
