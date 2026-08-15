# Proofs — verified product behaviors

Short demo commands tied to research-backed claims. Scores are **decision aids**, not oracles.

Prereq:

```bash
pip install -e ".[dev]"
```

## Related literature ≠ answered (F1 / F7)

```bash
emotions run --domain ai --n 5 --json
# Inspect: gap.status, gap.related_works, gap.notes (“Related ≠ answered”)
```

Offline degrade (F15):

```bash
emotions run --domain ai --no-literature --n 5 --json
# gap.status == unknown_with_caveat; flags include no_literature; confidence lowered
```

## Acceptance gates (F2 / F10 / F1)

```bash
pytest tests/test_failure_modes.py -q
# Covers F1–F15 adversarial checks (see tests/test_failure_modes.py)
# Includes expanded F7 phrase-gaming + F13 paraphrase cluster tests
```

## Mode collapse / paraphrase (F4 / F13)

Near-duplicates (including hyphen variants) are suppressed before top-N via **Jaccard** (default).

Optional semantic path (not default):

```bash
pip install -e ".[embeddings]"
emotions run --domain ai --n 5 --no-literature --diversity embedding
# Falls back to Jaccard if sentence-transformers is missing
```

## ValueProfile presets (F11)

```bash
emotions profiles
emotions spark --domain ai --n 3 --profile alignment_lab
# inject and value_profile.name both show the preset
curl "http://127.0.0.1:8000/v1/profiles"   # after emotions serve
```

## Instant spark + explicit ValueProfile (F11)

```bash
emotions spark --domain biology --n 5
emotions spark --domain physics --json
# inject states ValueProfile; pack includes value_profile + capability disclaimer
```

## Separate judge model (F5)

```bash
# Generator vs judge can differ (no live call required for offline path)
emotions run --domain ai --n 3 --no-literature --model gen-model --judge-model judge-model
# Or set LLM_JUDGE_MODEL in .env (never commit .env)
```

## Multi-domain seeds

```bash
emotions spark --domain climate --n 3
emotions spark --domain energy --n 3
emotions spark --domain materials --n 3
emotions spark --domain social --n 3
```

## MCP / agent UX (curiosity ≠ Q&A)

```bash
emotions-mcp --list-tools
emotions-mcp --list-resources
python -c "from artificial_emotions.agent_tools import dispatch_tool; print(dispatch_tool('list_profiles'))"
```

## Expert-eval / spot-check harness (W10)

```bash
emotions eval
emotions eval --json
emotions eval elicit --responses examples/elicit_ab_sample_responses.json --json
emotions eval elicit --responses examples/elicit_ab_sample_responses_climate.json --domain climate --json
# Lexical A/B smoke — not EES, not an elicitation league
emotions eval gap-status --json
emotions eval report --json
emotions eval calibration --json
# Preference/outcome telemetry: counts, outcome mix, hint magnitudes.
# Not calibrated. Not a calibration certificate. No accuracy %.
# Hand-label metrics: status_accuracy, related_but_unanswered_recall, false_answered_rate
# Composite report: gap_f1 + elicit means + risk probes (not a vanity %)
pytest tests/test_mid_horizon.py -q
pytest tests/test_eval_calibration.py -q
# Methodology: evals/METHODOLOGY.md — report case-level match + F1 miss rate; no vanity accuracy %
```

## Profile compare (decision aid)

```bash
emotions compare-profiles --domain ai --a humanity_default --b alignment_lab --n 6 --json
# HTTP: POST /v1/profiles/compare — Kendall τ + top-k Jaccard; no silent weight merge
# Web: Side-by-side ranks panel (two columns)
```

## Critique brief + VOI worksheet

```bash
emotions critique-brief --question "What is A? What is B?" --ops "do everything" --json
emotions voi-worksheet --question "Which biomarkers…?" --profile humanity_default --json
# HTTP: POST /v1/briefs/critique  POST /v1/voi/worksheet — form-only / template fill
# JSON includes honesty=not_evsi and evsi=null (not computed EVSI)
```

## Second literature backend (W11)

```bash
# Default remains OpenAlex. Semantic Scholar / merge are config switches.
emotions run --domain ai --n 3 --literature-backend openalex --json
# Optional (network): --literature-backend semantic_scholar | both
# Offline path unchanged:
emotions run --domain ai --n 3 --no-literature --json
```

## Grounded LLM gap reader (W12)

When `use_llm=True`, the gap reader must cite titles from retrieved papers only.
Ungrounded / invented titles are rejected (heuristic gap kept; `llm_gap_ungrounded` flag).
Verified offline via `tests/test_mid_horizon.py::test_w12_gap_reader_rejects_ungrounded_titles`.
Live LLM smoke is optional (keys often absent).

## Preference JSONL (W13)

```bash
emotions run --domain ai --n 3 --no-literature --preference-log prefs.jsonl
# Appends PreferenceEvent rows (schema preference_event.v1); no DB required
emotions preferences summarize --path prefs.jsonl --json
emotions preferences suggest-pair --candidates a,b,c --path prefs.jsonl --json
# HTTP: POST /v1/preferences/suggest-pair — next duel heuristic; not BT weight overwrite
# Web: Prefer / Tie / Reject on result cards
```

## Dual-use uplift (W14)

```bash
pytest tests/test_mid_horizon.py::test_w14_dual_use_beyond_keywords -q
# Weighted patterns + combos + human_review_risk; LIMITS still lists residual evasion risk
pytest tests/test_elicit_redteam_fixtures.py tests/test_wedges_safety_packs.py::test_dual_use_redteam_fixtures -q
# Small dual-use + elicit fixture regression — not a league; not dual-use solved
pytest tests/test_explore_enacted_flags.py -q
# W-explore: explore may omit dual_use_high when drop_dual_use fires; still not a biosafety oracle
```

## Multi-judge disagreement (W15)

```bash
# Offline unit: disagreement entropy widens bands
pytest tests/test_mid_horizon.py::test_w15_multi_judge_disagreement_widens_bands -q
# Live (optional keys): --judge-ensemble 2 or LLM_JUDGE_MODELS=a,b
emotions run --domain ai --n 3 --no-literature --llm --judge-ensemble 2
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
python -c "from artificial_emotions.llm import resolve_llm_settings; print(resolve_llm_settings())"

# 2) Offline path must still work with no keys:
emotions spark --domain ai --n 3

# 3) Optional live (only if you set LLM_* in local .env):
emotions run --domain ai --n 3 --no-literature --llm
# Optional distinct judge:
emotions run --domain ai --n 3 --no-literature --llm --judge-model "$LLM_JUDGE_MODEL"
```

This repo’s CI/agent sessions do **not** claim live multi-provider passes — only that the client + env matrix are documented and offline demos work without keys.

## VOI + Bayesian surprise worksheets (not EVSI)

```bash
emotions voi-worksheet --question-id q1 --question "Which biomarkers?" --json
# honesty=not_evsi, evsi=null — not computed EVSI
emotions surprise-worksheet --question-id q1 --predicted-surprise 0.7 --belief-shift 2 --json
# HTTP: POST /v1/voi/worksheet  POST /v1/surprise/worksheet
# Belief-shift logging only — does not rename ScoreAxes.surprise
```

## Outcome loop dry-run (not experiment execution)

```bash
emotions loop --outcomes evals/fixtures/outcome_loop_smoke_v1.jsonl --json
# Suggested re-rank + next explore step from logged outcomes.
# Does not run experiments. Not a lab closed-loop. CLI only.
```

## Offline vs literature compare

```bash
python examples/_run_compare.py
```

## Packaging smoke (local build; last PyPI upload is 1.0.0)

```bash
pip install build
python -m build
# Artifacts under dist/. Last upload: artificial-emotions 1.0.0 (tag v1.0.0).
# This command does not publish. Next upload: see docs/PUBLISHING.md.
```

## End-to-end surfaces (API + CLI)

Offline by default — does not depend on OpenAlex:

```bash
pytest tests/e2e -q
# or: pytest -m e2e -q
```

Covers: `GET /health` → domains/profiles/agent/tools → fast provoke → `POST /v1/curiosity/run` with `use_literature=false`; emotions (`/v1/emotions/*` mix/catalog); `POST /v1/preferences/hints`; CLI `spark` / `run --no-literature` / `profiles` / `eval` / `emotions` / `preferences hints`. LangGraph snippet in `docs/PLUGINS.md` is host-side docs; its smoke is `GET /v1/agent/tools`, not a LangGraph CI job.


## Epistemic cues / emotions (annotation only)

```bash
emotions cues --json
emotions annotate "What remains unknown about epistemic emotion elicitation?" --surprise 0.7 --json
emotions pack --json
emotions pack check --json
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

Product bounds: [`LIMITS.md`](LIMITS.md). Short invariants: [`DESIGN.md`](DESIGN.md). Examples index: [`../examples/README.md`](../examples/README.md).
