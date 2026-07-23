# Proofs — verified product behaviors

Short demo commands tied to research-backed claims. Scores are **decision aids**, not oracles.

Prereq:

```bash
pip install -e ".[dev]"
```

## Related literature ≠ answered (F1 / F7)

```bash
curiosity run --domain ai --n 5 --json
# Inspect: gap.status, gap.related_works, gap.notes (“Related ≠ answered”)
```

Offline degrade (F15):

```bash
curiosity run --domain ai --no-literature --n 5 --json
# gap.status == unknown_with_caveat; flags include no_literature; confidence lowered
```

## Acceptance gates (F2 / F10 / F1)

```bash
pytest tests/test_failure_modes.py -q
# Covers F1–F15 adversarial checks from research/FAILURE_MODES.md
# Includes expanded F7 phrase-gaming + F13 paraphrase cluster tests
```

## Mode collapse / paraphrase (F4 / F13)

Near-duplicates (including hyphen variants) are suppressed before top-N via **Jaccard** (default).

Optional semantic path (not default):

```bash
pip install -e ".[embeddings]"
curiosity run --domain ai --n 5 --no-literature --diversity embedding
# Falls back to Jaccard if sentence-transformers is missing
```

## ValueProfile presets (F11)

```bash
curiosity profiles
curiosity spark --domain ai --n 3 --profile alignment_lab
# inject and value_profile.name both show the preset
curl "http://127.0.0.1:8000/v1/profiles"   # after curiosity serve
```

## Instant spark + explicit ValueProfile (F11)

```bash
curiosity spark --domain biology --n 5
curiosity spark --domain physics --json
# inject states ValueProfile; pack includes value_profile + capability disclaimer
```

## Separate judge model (F5)

```bash
# Generator vs judge can differ (no live call required for offline path)
curiosity run --domain ai --n 3 --no-literature --model gen-model --judge-model judge-model
# Or set LLM_JUDGE_MODEL in .env (never commit .env)
```

## Multi-domain seeds

```bash
curiosity spark --domain climate --n 3
curiosity spark --domain energy --n 3
curiosity spark --domain materials --n 3
curiosity spark --domain social --n 3
```

## MCP / agent UX (curiosity ≠ Q&A)

```bash
curiosity-mcp --list-tools
python -c "from artificial_curiosity.agent_tools import dispatch_tool; print(dispatch_tool('list_profiles'))"
```

## Multi-provider LLM smoke matrix (ops)

Provider-agnostic client: any OpenAI-compatible `/chat/completions` host.
Copy `.env.example` → `.env` locally; **never commit keys**.

| Provider | `LLM_BASE_URL` | Example `LLM_MODEL` | Notes |
|----------|----------------|---------------------|-------|
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` | Default in `.env.example` |
| OpenRouter | `https://openrouter.ai/api/v1` | `anthropic/claude-sonnet-4` | Set `LLM_API_KEY` to OpenRouter key |
| Groq | `https://api.groq.com/openai/v1` | `llama-3.3-70b-versatile` | Fast hosted Llama |
| Ollama (local) | `http://localhost:11434/v1` | `llama3.2` | Key may be `local` / empty |

Smoke (run **once** locally with your own keys; do not paste secrets into docs/git):

```bash
# 1) Confirm resolution without calling the network:
python -c "from artificial_curiosity.llm import resolve_llm_settings; print(resolve_llm_settings())"

# 2) Offline path must still work with no keys:
curiosity spark --domain ai --n 3

# 3) Optional live (only if you set LLM_* in local .env):
curiosity run --domain ai --n 3 --no-literature --llm
# Optional distinct judge:
curiosity run --domain ai --n 3 --no-literature --llm --judge-model "$LLM_JUDGE_MODEL"
```

This repo’s CI/agent sessions do **not** claim live multi-provider passes — only that the client + env matrix are documented and offline demos work without keys.

## Offline vs literature compare

```bash
python examples/_run_compare.py
```

## Packaging smoke (not PyPI publish)

```bash
pip install build
python -m build
# Artifacts under dist/; owner publishes to PyPI when ready
```

## Full suite

```bash
pytest -q
```

Design rationale: [`research/`](../research/). Short invariants: [`DESIGN.md`](DESIGN.md).
