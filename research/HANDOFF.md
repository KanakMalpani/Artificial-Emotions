# Agent Handoff — Artificial Curiosity

**Workspace (only):** `<local-clone>`  
**Remote:** https://github.com/KanakMalpani/Artificial-Curiosity.git (private for now)  
**Goal:** Curiosity layer — generate & rank valuable *unanswered* questions (not Q&A).  
**Entry docs:** Product → root `README.md` + `docs/`. Research archive → `research/` (`FIRST_PRINCIPLES`, `RESEARCH`, `FAILURE_MODES`, …).  
**Version:** `0.2.0`

## Done (do not redo)

- Full pipeline: generate → OpenAlex gap verify → multi-axis score → diversify → brief
- Gap fix: **related ≠ answered** (`verify.py` overlap-gated + phrase-level abstract claim/open-gap reading)
- Expanded seeds; hyphen-safe diversity; score uncertainty bands
- **Provider-agnostic LLM** (`LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL`) — OpenAI, OpenRouter, Groq, Ollama, etc.
- **Separate `judge_model` / `LLM_JUDGE_MODEL`** from generator (F5)
- **ValueProfile presets** + `list_profiles` / `curiosity profiles` / `GET /v1/profiles`
- **Optional embedding diversity** extras; Jaccard remains default
- Instant spark: `curiosity spark` + `GET|POST /v1/curiosity/provoke` (`inject` pack for any model)
- Agent guide: `GET /v1/agent`; one-command API: `curiosity serve`
- **MCP stdio plugin:** `curiosity-mcp` / `python -m artificial_curiosity.mcp_server`
  - Tools: `provoke_curiosity`, `spark`, `rank_unknowns`, `run_curiosity`, `list_domains`, `list_profiles`
  - Shared schemas: `agent_tools.py`; OpenAI JSON: `examples/openai_tools.json` + `GET /v1/agent/tools`
- Platform install docs: `docs/PLUGINS.md` (Cursor, Claude Desktop, Claude Code, VS Code Copilot, Continue, Windsurf, HTTP, OpenAI tools)
- Web UI: briefs primary + bands + profile name
- CONTRIBUTING seed/domain pack quality bar
- Packaging prep (hatchling); **not on PyPI yet** (LIMITS honesty)
- Automated tests (core + failure-mode + provoke/API + MCP) — run `pytest -q`
- Fresh compare artifacts under `examples/run_ai_*_final.json`
- v0.2 work orders WO-0.2.1 … WO-0.2.10 checked in `docs/ROADMAP.md`

## Not finished / continue here

1. Live multi-provider LLM smoke with real keys (document results privately; never commit secrets)
2. Expert-eval / longitudinal calibration harness (W10 / v0.3)
3. Second literature backend (W11)
4. LLM gap reader: mandatory retrieved evidence in rationale (W12)
5. Owner: `python -m build` + PyPI publish when ready
6. Dual-use beyond keywords (W14) / multi-judge entropy (W15)

## Commands

```bash
cd Artificial-Curiosity   # or your local clone path
pip install -e ".[dev]"
pytest -q
curiosity spark --domain ai --n 5 --profile alignment_lab
curiosity profiles
curiosity serve
curiosity-mcp --list-tools
# Instant API: GET http://127.0.0.1:8000/v1/curiosity/provoke?domain=ai&n=5&profile_name=funder_10y
# Tools JSON:  GET http://127.0.0.1:8000/v1/agent/tools
# Profiles:    GET http://127.0.0.1:8000/v1/profiles
```

## Invariants

- Stay in this folder only
- Explicit `ValueProfile` — no value-free ranking
- Don't claim scores are oracles; update `docs/LIMITS.md` when claims change
- Don't commit secrets / `.env` / API keys
