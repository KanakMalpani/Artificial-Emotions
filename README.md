# Artificial Curiosity

**Current AI answers questions. This system generates the most valuable unanswered ones.**

It asks: *What should humanity investigate next?* — then ranks scientific unknowns by expected impact.

## Why this exists

Most AI products optimize answering (search, synthesis, agents that write papers). The scarce capability is **curiosity**: proposing and prioritizing investigations under uncertainty.

This repo implements a **Curiosity Layer**:

1. Propose candidate unknowns  
2. Verify they look unanswered in the literature (OpenAlex)  
3. Score them on impact / neglectedness / tractability / surprise / answerability / risk  
4. Diversify and return investigation briefs  

All research lives in this folder — start at [`docs/INDEX.md`](docs/INDEX.md).

Also: `docs/FIRST_PRINCIPLES.md`, `docs/RESEARCH.md`, `docs/SOURCES.md`, `docs/FAILURE_MODES.md`.

## Quick start

```bash
# API + engine
cd "<local-clone>"
pip install -e ".[dev]"
curiosity --domain ai --n 8 --no-literature
curiosity --domain biology --json

# API server
uvicorn artificial_curiosity.api:app --reload --port 8000

# Web UI (separate terminal)
cd web
npm install
npm run dev
```

Open http://localhost:5173

### Optional LLM mode

```bash
set OPENAI_API_KEY=sk-...
curiosity --domain ai --llm
```

Uses an OpenAI-compatible Chat Completions API for generation + judging. Without a key, the engine falls back to curated seeds + heuristic scoring.

## Python API

```python
from artificial_curiosity import CuriosityEngine, CuriosityConfig

engine = CuriosityEngine(CuriosityConfig(domain="climate", use_literature=True))
for q in engine.run():
    print(q.rank, q.curiosity_score, q.question.question)
```

## HTTP API

`POST /v1/curiosity/run`

```json
{
  "domain": "ai",
  "topic": "alignment evals",
  "n_return": 8,
  "use_llm": false,
  "use_literature": true
}
```

## Design invariants

- No value-free ranking — `ValueProfile` is explicit  
- Likely-answered questions cannot top the list  
- Near-duplicates are suppressed  
- Scores carry confidence; heuristics are flagged  

## Status

v0.1.0 — working end-to-end curiosity pipeline with offline demo path, literature grounding, CLI, API, and web UI.

See [`docs/LIMITS.md`](docs/LIMITS.md) for verified capabilities vs known gaps. Do not treat curiosity scores as ground truth.
