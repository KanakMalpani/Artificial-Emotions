# Known Limits (verified)

Honest bounds for **v0.2.0** — do not overclaim.

## Verified working (2026-07-23)

- Offline seed → score → rank → brief pipeline
- Literature neighborhood fetch via OpenAlex
- Gap gate: related papers ≠ answered (overlap-gated + phrase-level abstract reading)
- Acceptance gates: answerability, risk, likely-answered
- Near-duplicate suppression: **normalized Jaccard is the default** (hyphen-safe)
- Optional embedding diversity behind `pip install '.[embeddings]'` (`diversity_backend=embedding`); falls back to Jaccard if extras missing — **not** default intelligence
- Score uncertainty bands (`score_low` / `score_high`) — evidence envelopes, not true CIs
- Optional LLM judge + LLM gap reader when `use_llm=True` and any OpenAI-compatible provider is configured (`LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL`)
- Separate `judge_model` / `LLM_JUDGE_MODEL` from generator model (F5) — config + CLI/API/MCP flags
- Named **ValueProfile presets** (`humanity_default`, `funder_10y`, `alignment_lab`, `climate_adaptation`, `basic_science`, `near_term_ops`) via `curiosity profiles`, `GET /v1/profiles`, MCP `list_profiles`, `--profile` / `profile_name`
- Instant spark for any agent/model: `GET|POST /v1/curiosity/provoke`, CLI `curiosity spark`, `curiosity serve`
- Agent manifest: `GET /v1/agent`
- OpenAI-compatible tool schemas: `GET /v1/agent/tools` + `examples/openai_tools.json`
- MCP stdio server: `curiosity-mcp` / `python -m artificial_curiosity.mcp_server` (tools list + call handlers; no MCP SDK)
- Plugin install docs: `docs/PLUGINS.md` (Cursor, Claude Desktop, Claude Code, VS Code Copilot, Continue, Windsurf, HTTP, OpenAI tools)
- Demo proofs: `docs/PROOFS.md` (includes multi-provider smoke matrix notes — no secrets)
- CLI, Python API, FastAPI (`:8000`), Vite UI (`:5173`) — UI shows briefs, `[low–high]` bands, and profile name
- Automated tests: core, failure-mode (incl. expanded F7/F13), provoke/API, MCP — **61 passed** (`pytest -q`, 2026-07-23)
- Smoke: `curiosity spark`, `curiosity profiles`, `curiosity-mcp --list-tools`, `import artificial_curiosity.mcp_server`
- Offline vs literature artifacts under `examples/run_ai_*_final.json`
- Multi-domain seeds: biology, physics, ai, climate, medicine, materials, social, energy
- Failure-mode suite: `tests/test_failure_modes.py` encodes F1–F15 from `research/FAILURE_MODES.md`
- Explicit ValueProfile on provoke/inject (F11); recency-aware likely-answered gate (F12)
- Download-and-run: `pip install -e .` then `curiosity serve` **or** `curiosity-mcp` — no vendor lock-in for LLM hosts
- Packaging: hatchling sdist/wheel buildable locally; **not published to PyPI yet** (owner-gated)

## Known limits

| Limit | Why | Mitigation path |
|-------|-----|-----------------|
| Heuristic scoring is lexicon/density based | No LLM required for demos | Set `use_llm=True` + API key |
| Gap reading is phrase/overlap, not full-text comprehension | OpenAlex abstracts are partial | LLM gap reader (shipped optional) or full-text APIs |
| OpenAlex neighborhoods can be topically noisy | Relevance search ≠ semantic match | Low overlap keeps `unanswered`; query uses tags + compounds |
| Seed set is curated, not open-ended | Offline reliability | LLM generation expands candidates; see CONTRIBUTING |
| Value weights are named presets or custom | No universal value-free ranking | Pass `profile_name` or custom `ValueProfile` |
| No longitudinal outcome calibration yet | Need impact follow-up data | Log rankings → later impact; bands are provisional |
| Embedding diversity is optional extras | Avoid heavy deps by default | `pip install '.[embeddings]'` + `diversity_backend=embedding` |
| Dual-use filter is keyword-level | Easy to evade | Stronger classifier + human review |
| LLM paths untested live in CI | `LLM_API_KEY` often unset | Local multi-provider smoke per PROOFS; no secrets in repo |
| MCP is tools-only (no resources/prompts) | Keep stdlib surface small | Add later if hosts need them |
| Not on PyPI yet | Owner publish gate | `python -m build` locally; publish when tagged |

## Confidence interpretation

- `~0.25–0.35`: no literature / unknown caveat
- `~0.45–0.58`: heuristic + literature neighborhood (cap while heuristic)
- Higher: requires LLM judges and/or stronger evidence

Scores are **decision aids**, not oracles. Displayed `[low–high]` bands widen when confidence is low.
