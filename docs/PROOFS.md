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
curiosity-mcp --list-resources
python -c "from artificial_curiosity.agent_tools import dispatch_tool; print(dispatch_tool('list_profiles'))"
```

## Expert-eval / spot-check harness (W10)

```bash
curiosity eval
curiosity eval --json
pytest tests/test_mid_horizon.py -q
# Methodology: evals/METHODOLOGY.md — report case-level match + F1 miss rate; no vanity accuracy %
```

## Second literature backend (W11)

```bash
# Default remains OpenAlex. Semantic Scholar / merge are config switches.
curiosity run --domain ai --n 3 --literature-backend openalex --json
# Optional (network): --literature-backend semantic_scholar | both
# Offline path unchanged:
curiosity run --domain ai --n 3 --no-literature --json
```

## Grounded LLM gap reader (W12)

When `use_llm=True`, the gap reader must cite titles from retrieved papers only.
Ungrounded / invented titles are rejected (heuristic gap kept; `llm_gap_ungrounded` flag).
Verified offline via `tests/test_mid_horizon.py::test_w12_gap_reader_rejects_ungrounded_titles`.
Live LLM smoke is optional (keys often absent).

## Preference JSONL (W13)

```bash
curiosity run --domain ai --n 3 --no-literature --preference-log prefs.jsonl
# Appends PreferenceEvent rows (schema preference_event.v1); no DB required
```

## Dual-use uplift (W14)

```bash
pytest tests/test_mid_horizon.py::test_w14_dual_use_beyond_keywords -q
# Weighted patterns + combos + human_review_risk; LIMITS still lists residual evasion risk
```

## Multi-judge disagreement (W15)

```bash
# Offline unit: disagreement entropy widens bands
pytest tests/test_mid_horizon.py::test_w15_multi_judge_disagreement_widens_bands -q
# Live (optional keys): --judge-ensemble 2 or LLM_JUDGE_MODELS=a,b
curiosity run --domain ai --n 3 --no-literature --llm --judge-ensemble 2
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

## End-to-end surfaces (API + CLI)

Offline by default — does not depend on OpenAlex:

```bash
pytest tests/e2e -q
# or: pytest -m e2e -q
```

Covers: `GET /health` → domains/profiles/agent/tools → fast provoke → `POST /v1/curiosity/run` with `use_literature=false`; emotions (`/v1/emotions/*` mix/catalog); `POST /v1/preferences/hints`; CLI `spark` / `run --no-literature` / `profiles` / `eval` / `emotions` / `preferences hints`.

Optional Vite UI Playwright (skipped by default):

```bash
cd web && npm run build
# pip install playwright && playwright install chromium
set CURIOSITY_PLAYWRIGHT=1
pytest tests/e2e/test_web_playwright.py -q
```

## Epistemic cues / emotions (annotation only)

```bash
curiosity emotions cues --json
curiosity emotions annotate "What remains unknown about epistemic emotion elicitation?" --surprise 0.7 --json
curiosity emotions pack --json
# HTTP: GET /v1/emotions/cues  POST /v1/emotions/annotate  GET /v1/emotions/pack
# Docs: docs/EMOTIONS.md — does not claim the system feels
```

Optional literature smoke (may skip when OpenAlex is unreachable):

```bash
pytest -m slow -q
```

## Full suite

```bash
pytest -q
# CI-safe (exclude optional lit): pytest -m "not slow" -q
```

Design rationale: [`research/`](../research/). Short invariants: [`DESIGN.md`](DESIGN.md).
