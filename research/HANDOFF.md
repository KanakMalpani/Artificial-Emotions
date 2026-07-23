# Agent Handoff — Artificial Curiosity

**Workspace (only):** `C:\Users\mrkan\CRAZZY\Artificial Curiosity`  
**Remote:** https://github.com/KanakMalpani/Artificial-Curiosity.git (private for now)  
**Goal:** Curiosity layer — generate & rank valuable *unanswered* questions (not Q&A).  
**Entry docs:** Product → root `README.md` + `docs/`. Research archive → `research/` (`FIRST_PRINCIPLES`, `RESEARCH`, `FAILURE_MODES`, …).  
**Version:** `0.3.0`

## Done (do not redo)

- Full pipeline: generate → lit gap verify → multi-axis score → diversify → brief
- Gap fix: **related ≠ answered** (`verify.py` overlap-gated + phrase-level abstract claim/open-gap reading)
- Expanded seeds; hyphen-safe diversity; score uncertainty bands
- **Provider-agnostic LLM** (`LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL`) — OpenAI, OpenRouter, Groq, Ollama, etc.
- **Separate `judge_model` / `LLM_JUDGE_MODEL`** from generator (F5)
- **ValueProfile presets** + `list_profiles` / `curiosity profiles` / `GET /v1/profiles`
- **Optional embedding diversity** extras; Jaccard remains default
- Instant spark: `curiosity spark` + `GET|POST /v1/curiosity/provoke` (`inject` pack for any model)
- Agent guide: `GET /v1/agent`; one-command API: `curiosity serve`
- **MCP stdio plugin:** tools + resources (`curiosity://domains|profiles|limits`)
- Platform install docs: `docs/PLUGINS.md`
- Web UI: briefs primary + bands + profile name
- CONTRIBUTING seed/domain pack quality bar
- Packaging prep (hatchling); **not on PyPI yet** (LIMITS honesty)
- v0.2 work orders WO-0.2.1 … WO-0.2.10 checked in `docs/ROADMAP.md`
- **P2 / v0.3 mid-horizon (W10–W15 + extras):**
  - W10 expert-eval harness (`curiosity eval`, `evals/`)
  - W11 Semantic Scholar + `both` merge (`literature.py`)
  - W12 grounded LLM gap reader (reject invented titles)
  - W13 preference JSONL (`preferences.py`)
  - W14 dual-use weighted classifier + `human_review_risk`
  - W15 multi-judge disagreement entropy + wider bands
  - Domain packs, lit cache, MCP resources
- Automated tests — **71 passed** (`pytest -q`)

## Not finished / continue here

1. Live multi-provider LLM smoke with real keys (document results privately; never commit secrets)
2. Owner: `python -m build` + **PyPI publish** when ready (blocks calling “v1.0”)
3. WO-0.4.4 neglectedness / cost proxy research spike (optional)
4. WO-0.4.6 optional HTTP API keys (enterprise nicety)
5. Preference *learning* / longitudinal calibration (v1.x flywheel — schema only today)
6. Moonshots (approx VOI, lab closed-loop, constitutional curiosity) — stubs only; do not claim done

## Commands

```bash
cd Artificial-Curiosity   # or your local clone path
pip install -e ".[dev]"
pytest -q
curiosity spark --domain ai --n 5 --profile alignment_lab
curiosity eval
curiosity profiles
curiosity serve
curiosity-mcp --list-tools
curiosity-mcp --list-resources
# Instant API: GET http://127.0.0.1:8000/v1/curiosity/provoke?domain=ai&n=5&profile_name=funder_10y
```

## Invariants

- Stay in this folder only
- Explicit `ValueProfile` — no value-free ranking
- Don't claim scores are oracles; update `docs/LIMITS.md` when claims change
- Don't commit secrets / `.env` / API keys
