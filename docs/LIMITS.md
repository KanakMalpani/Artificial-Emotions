# Known Limits (verified)

Honest bounds for **v0.4.0** — do not overclaim.

## Verified working (2026-07-24)

- Offline seed → score → rank → brief pipeline
- Literature neighborhood fetch via **OpenAlex** (default) and optional **Semantic Scholar** (`literature_backend=semantic_scholar|both`)
- Optional literature disk cache (`literature_cache_dir`) for rate-limit softening
- Parallel literature fetches (`literature_workers`, default 4; CLI `--lit-workers`; API field) — serial when `1`
- Gap gate: related papers ≠ answered (overlap-gated + phrase-level abstract reading)
- LLM gap reader (optional): **rejects ungrounded / invented paper titles**; keeps heuristic gap when evidence missing (W12)
- Acceptance gates: answerability, risk, likely-answered
- Near-duplicate suppression: **normalized Jaccard is the default** (hyphen-safe)
- Optional embedding diversity behind `pip install '.[embeddings]'` (`diversity_backend=embedding`); falls back to Jaccard if extras missing — **not** default intelligence
- Score uncertainty bands (`score_low` / `score_high`) — evidence envelopes, not true CIs; widen on multi-judge disagreement
- Optional LLM judge + LLM gap reader when `use_llm=True` and any OpenAI-compatible provider is configured (`LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL`)
- Separate `judge_model` / `LLM_JUDGE_MODEL` from generator model (F5) — config + CLI/API/MCP flags
- Multi-judge ensemble (`judge_ensemble_n` / `LLM_JUDGE_MODELS`): disagreement entropy flag + wider bands (W15) — requires live LLM; offline path uses heuristic
- Named **ValueProfile presets** (`humanity_default`, `funder_10y`, `alignment_lab`, `climate_adaptation`, `basic_science`, `near_term_ops`, `public_demo_strict_risk`) via `curiosity profiles`, `GET /v1/profiles`, MCP `list_profiles`, `--profile` / `profile_name`
- Instant spark for any agent/model: `GET|POST /v1/curiosity/provoke`, CLI `curiosity spark`, `curiosity serve`
- Agent manifest: `GET /v1/agent`
- OpenAI-compatible tool schemas: `GET /v1/agent/tools` + `examples/openai_tools.json`
- MCP stdio server: `curiosity-mcp` (tools + resources: `curiosity://domains|profiles|limits`)
- Plugin install docs: `docs/PLUGINS.md` (Cursor, Claude Desktop, Claude Code, VS Code Copilot, Continue, Windsurf, HTTP, OpenAI tools)
- Demo proofs: `docs/PROOFS.md` (includes multi-provider smoke matrix notes — no secrets)
- CLI, Python API, FastAPI (`:8000`), Vite UI (`:5173`) — UI shows briefs, `[low–high]` bands, and profile name
- Expert-eval / spot-check harness: `curiosity eval` + `evals/fixtures/` (v1+v2 adversarial) + `evals/METHODOLOGY.md` (offline; **no vanity accuracy %**; stratified `by_gold_status`)
- Elicit A/B process eval: `curiosity eval elicit` + `examples/elicit_ab_protocol.json` (lexical investigation-quality rubric — **not** EES)
- Gap-status hand-label metric: `curiosity eval gap-status` + `evals/fixtures/gap_status_handlabel_v1.json` (status_accuracy + related_but_unanswered_recall + false_answered_rate)
- OpenAlex `has_funder` / lit rationale keys (`openalex_hit_n`, `mean_cited_by`, `funder_field_missing_rate`) attach to score rationale only — **no silent neglectedness weight change**
- Opt-in preference JSONL schema (`preference_log_path` / `--preference-log`) — no DB required (W13); **CLI/config only** (not HTTP body — path injection)
- Thin preference re-rank (`preference_rerank_path` / `--preference-rerank`): prefer/reject → small profile-scoped score deltas + `preference_rerank` flag — **not** calibrated weight learning; CLI/config only
- Preference weight hints (`preference_learn_path` / `--preference-learn` / `curiosity preferences hints` / `POST /v1/preferences/hints`): tiny profile-scoped ValueProfile deltas from labeled events with `score_axes` — **not** calibrated; API accepts inline events only (no paths); weights floored so hints cannot zero out a dimension
- Preference summarize (`curiosity preferences summarize` / `POST /v1/preferences/summarize`): counts, pairwise wins from `preferred_over_ids`, top ids — Stage-1 flywheel, not Bradley–Terry
- Profile compare (`curiosity compare-profiles` / `POST /v1/profiles/compare` / MCP `compare_profiles` / web two-column panel): side-by-side offline ranks + Kendall τ + top-k Jaccard + veto tip — **no silent consensus merge**
- Form-only brief critic (`curiosity critique-brief` / `POST /v1/briefs/critique` / MCP `critique_brief`) — does **not** re-rank
- VOI worksheet fill (`curiosity voi-worksheet` / `POST /v1/voi/worksheet` / MCP `voi_worksheet`) — template metadata only; **not** EVSI/ENBS
- Composite eval report (`curiosity eval report`) — gap_f1 + gap-status + elicit means + risk probes
- MCP description lint (`tests/test_mcp_description_lint.py`) — anti-MPMA forbidden phrases + honesty families
- Agent card honesty block on `GET /v1/agent` (`card` + `honesty` list)
- ValueProfile cue thresholds (`cue_surprise_high` / `cue_neglectedness_high` / `cue_answerability_low`) drive epistemic tags — annotation only
- Preference summarize includes sparse `outcomes` breakdown (`event_type=outcome` labels) — not auto-retrain
- Preference `tie` / `both_keep` counted honestly; `suggest_next_pair` + gated `fit_bt_offline` (no auto weight overwrite)
- Offline LitGap-style cooccur study (`curiosity eval cooccur`) — Spearman smoke + display-only `cooccur_gap` keys; never silent weight change
- Top-n hivemind similarity in `curiosity eval report` (Jaccard default; optional embedding)
- Gap-status fixtures may carry VERITAS-ish `gold_tags` (`underpowered`, `invalid_form`) without inventing new GapStatus enums
- Emotion mix soft guards: warn when mix is dominated by fear/anxiety/anger-type ids (annotation still returned)
- Optional `mix_intensity_cap` on ValueProfile (public_demo_strict_risk=0.35) caps non-epistemic mix mass
- EIG-inspired idea-graph export (`POST /v1/evals/idea-graph` / MCP `export_idea_graph`) — display only
- Offline HybridQuestion-style `cross_model_vote` — form/heuristic proxy; never silent re-rank
- Agent card `/v1/agent` includes affective-safety blurb (not biometric ERS; provoke is opt-in framing)
- Dual-use: weighted heuristic classifier + combo signals + `human_review_risk` flag (W14) — **not** a biosafety oracle; residual evasion risk remains
- Neglectedness/cost proxies: density/cites + trend/funding cues + investigation-scale lexicon (`research/NEGLECTEDNESS_COST.md`) — **not** funding DBs
- Optional HTTP API keys (`CURIOSITY_API_KEY` / `CURIOSITY_API_KEYS`) — unset = open local demo (WO-0.4.6)
- Versioned domain packs (`artificial_curiosity/packs/*.json`, `load_bundled_packs` / `domain_pack_paths`) including alignment, climate, affective science, aging biology, and materials catalysis packs
- Vite UI (`:5173`): briefs + bands + profile primary; optional investigation framing mix (annotation only — does not feel); Fast spark via provoke
- Structured HTTP errors (`{"error":{"code","message","details?"}}`) + `/ready` readiness (**503** when not ready)
- Central env config module (`artificial_curiosity.config`) — LLM_*, CURIOSITY_API_KEY, timeouts, CORS
- HTTP does **not** accept `literature_cache_dir` or `llm_base_url` (CLI/env only — path injection / SSRF)
- CI: `.github/workflows/ci.yml` runs ruff + pytest on push/PR (independent of publish billing)
- Automated tests: core, failure-mode, provoke/API, MCP, emotions, mid-horizon, e2e — run `pytest -q`
- Optional Playwright web smoke: `CURIOSITY_PLAYWRIGHT=1` + `web/dist` + chromium (`tests/e2e/test_web_playwright.py`) — skipped by default
- Smoke: `curiosity spark`, `curiosity profiles`, `curiosity eval`, `curiosity-mcp --list-tools`, `--list-resources`
- Offline vs literature artifacts under `examples/run_ai_*_final.json`
- Multi-domain seeds: biology, physics, ai, climate, medicine, materials, social, energy
- Failure-mode suite: `tests/test_failure_modes.py` encodes F1–F15 from `research/FAILURE_MODES.md`
- Explicit ValueProfile on provoke/inject (F11); recency-aware likely-answered gate (F12)
- Download-and-run: `pip install -e .` then `curiosity serve` **or** `curiosity-mcp` — no vendor lock-in for LLM hosts
- Packaging: hatchling sdist/wheel buildable locally; **not published to PyPI yet** (GitHub Actions blocked by account billing/spending — see `docs/PUBLISHING.md`)

## Known limits

| Limit | Why | Mitigation path |
|-------|-----|-----------------|
| Heuristic scoring is lexicon/density based | No LLM required for demos | Set `use_llm=True` + API key |
| Gap reading is phrase/overlap, not full-text comprehension | Abstracts are partial | Grounded LLM reader (optional) or full-text APIs later |
| OpenAlex / S2 neighborhoods can be topically noisy | Relevance search ≠ semantic match | Low overlap keeps `unanswered`; `both` merges sources |
| OpenAlex funder/affiliation metadata incomplete | Coverage ≠ accuracy (esp. outside WoS/Scopus overlap) | Treat funder signals as optional rationale keys only — not silent score weight |
| Seed set is curated (+ optional packs) | Offline reliability | LLM generation + CONTRIBUTING pack bar |
| Value weights are named presets or custom | No universal value-free ranking | Pass `profile_name` or custom `ValueProfile`; AI can shrink collective focus (McNamara / Hao *Nature* 2026; Bisht et al.) — see `research/PROBLEM_SELECTION_MCNAMARA.md` |
| Ranked unknowns ≠ post-execution quality | Ideation–execution gap (arXiv 2506.20803) | Treat ranks as decision aids; outcome flywheel is sparse / deferred |
| Axis scores are not EVSI/ENBS | No shared utility / PSA model | VOI worksheet is template fill only (`research/VOI_APPROXIMATIONS.md`) |
| Multi-model / ensemble generation | Artificial Hivemind homogenization risk | Jaccard/embedding diversity + hivemind eval metric; disagreement ≠ value |
| Affective surfaces (cues / mix / provoke) | Framing can manipulate priorities without biometric ERS | Annotation-only honesty; mix coercion warnings; optional `mix_intensity_cap`; agent safety blurb; no silent user-affect inference |
| No longitudinal outcome calibration yet | Need impact follow-up data | Preference JSONL + thin re-rank + tiny weight hints; bands provisional |
| Embedding diversity is optional extras | Avoid heavy deps by default | `pip install '.[embeddings]'` + `diversity_backend=embedding` |
| Dual-use is weighted heuristic, not a trained classifier | Evadable phrasing remains | Human review hook + LIMITS residual risk; stronger models later |
| Neglectedness/cost are lexicon/density proxies | No grant/spend APIs wired | Documented spike; optional funding adapters later |
| LLM paths untested live in CI | `LLM_API_KEY` often unset | Local multi-provider smoke per PROOFS; no secrets in repo |
| Multi-judge ensemble needs live LLM | Offline uses single heuristic | Documented; disagreement flag only when ≥2 judges return |
| Not on PyPI yet | Owner publish + Actions billing gate | Fix Billing & plans; then re-run `publish.yml` (see PUBLISHING) |
| Moonshots (approx VOI, lab closed-loop) | Research tracks | Stubs only — not claimed done |

## Confidence interpretation

- `~0.25–0.35`: no literature / unknown caveat
- `~0.45–0.58`: heuristic + literature neighborhood (cap while heuristic)
- Higher: requires LLM judges and/or stronger evidence
- Bands widen further when `judge_disagreement` fires

Scores are **decision aids**, not oracles. Displayed `[low–high]` bands widen when confidence is low.
