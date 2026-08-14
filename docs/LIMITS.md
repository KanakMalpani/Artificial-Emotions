# Known Limits (verified)

Honest bounds for **v0.4.1** — do not overclaim.

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
- Named **ValueProfile presets** (`humanity_default`, `funder_10y`, `alignment_lab`, `climate_adaptation`, `basic_science`, `near_term_ops`, `public_demo_strict_risk`) via `emotions profiles`, `GET /v1/profiles`, MCP `list_profiles`, `--profile` / `profile_name`
- Instant spark for any agent/model: `GET|POST /v1/curiosity/provoke`, CLI `emotions spark`, `emotions serve`
- Agent manifest: `GET /v1/agent`
- OpenAI-compatible tool schemas: `GET /v1/agent/tools` + `examples/openai_tools.json`
- MCP stdio server: `emotions-mcp` (tools + resources: `curiosity://domains|profiles|limits`)
- Plugin install docs: `docs/PLUGINS.md` (Cursor, Claude Desktop, Claude Code, VS Code Copilot, Continue, Windsurf, HTTP, OpenAI tools, LangGraph host-side recipe via `GET /v1/agent/tools` — `langgraph` is not a package dependency; not CI-tested against LangGraph releases)
- Demo proofs: `docs/PROOFS.md` (includes multi-provider smoke matrix notes — no secrets)
- CLI, Python API, FastAPI (`:8000`) — briefs, `[low–high]` bands, and profile name on agent surfaces
- Expert-eval / spot-check harness: `emotions eval` + `evals/fixtures/` (v1+v2 adversarial) + `evals/METHODOLOGY.md` (offline; **no vanity accuracy %**; stratified `by_gold_status`)
- Elicit A/B process eval: `emotions eval elicit` + `examples/elicit_ab_protocol.json` + AI/climate sample responses (lexical investigation-quality rubric — **not** EES, **not** an elicitation league)
- Gap-status hand-label metric: `emotions eval gap-status` + `evals/fixtures/gap_status_handlabel_v1.json` (status_accuracy + related_but_unanswered_recall + false_answered_rate)
- OpenAlex `has_funder` / lit rationale keys (`openalex_hit_n`, `mean_cited_by`, `funder_field_missing_rate`) attach to score rationale only — **no silent neglectedness weight change**
- Opt-in preference JSONL schema (`preference_log_path` / `--preference-log`) — no DB required (W13); **CLI/config only** (not HTTP body — path injection)
- Thin preference re-rank (`preference_rerank_path` / `--preference-rerank`): prefer/reject → small profile-scoped score deltas + `preference_rerank` flag — **not** calibrated weight learning; CLI/config only
- Preference weight hints (`preference_learn_path` / `--preference-learn` / `emotions preferences hints` / MCP `preference_weight_hints` / `POST /v1/preferences/hints`): tiny profile-scoped ValueProfile deltas from labeled prefer/reject **and** `event_type=outcome` rows with `score_axes` plus `labels.result` — **not** calibrated; silent without usable events; **preview by default** (`--apply` / `apply=true` returns a profile copy; named presets are never overwritten); API/MCP accept inline events only (no paths); `--preference-learn` on `run` is preview unless `--preference-learn-apply`; weights floored so hints cannot zero out a dimension
- Preference calibration telemetry (`emotions eval calibration`): offline JSONL → counts, outcome mix, hint magnitudes — **no accuracy %**; not a calibration certificate; does not apply hints
- Preference summarize (`emotions preferences summarize` / `POST /v1/preferences/summarize`): counts, pairwise wins from `preferred_over_ids`, top ids — Stage-1 flywheel, not Bradley–Terry
- Profile compare (`emotions compare-profiles` / `POST /v1/profiles/compare` / MCP `compare_profiles` / web two-column panel): side-by-side offline ranks + Kendall τ + top-k Jaccard + veto tip — **no silent consensus merge**
- Constitution compare + risk veto (`POST /v1/profiles/constitution-compare` / MCP `constitution_compare` / web Compare + veto): primary vs safety-veto + hard `max_risk` flag/drop — **not** a constitutional optimum
- MCP progressive disclosure via `CURIOSITY_MCP_TIER=core|investigate|affect|research|full` (default `full`); agent card exposes `tool_tiers`
- Dual-use red-team fixtures (`evals/fixtures/dual_use_redteam_v1.json`) — small regression corpus with `residual_may_miss` items; **not** a biosecurity oracle, **not** a red-team league, **not** dual-use solved
- Form-only brief critic (`emotions critique-brief` / `POST /v1/briefs/critique` / MCP `critique_brief`) — does **not** re-rank
- VOI worksheet fill (`emotions voi-worksheet` / `POST /v1/voi/worksheet` / MCP `voi_worksheet`) — template metadata only; payload `evsi: null` / `honesty: not_evsi`; optional `estimate_evsi` hook returns None without data; **not** EVSI/ENBS
- Composite eval report (`emotions eval report`) — diagnostics-first (soundness/critique/risk before elicit means; ErrEval cousin) + gap_f1 + gap-status + hivemind
- Failure-knowledge seed phrases in domain packs (null/replication gaps) — not a dark-reactions corpus claim
- Open-gap abstract lexicon includes null/replication phrases (dampen false “answered”) — still not full-text comprehension
- MCP description lint (`tests/test_mcp_description_lint.py`) — anti-MPMA forbidden phrases + honesty families
- Agent card honesty block on `GET /v1/agent` (`card` + `honesty` list)
- ValueProfile cue thresholds (`cue_surprise_high` / `cue_neglectedness_high` / `cue_answerability_low`) drive epistemic tags — annotation only
- Preference summarize includes sparse `outcomes` breakdown (`event_type=outcome` labels) — not auto-retrain
- Preference `tie` / `both_keep` counted honestly; `suggest_next_pair` + gated `fit_bt_offline` (no auto weight overwrite)
- Offline LitGap-style cooccur study (`emotions eval cooccur`) — Spearman smoke + display-only `cooccur_gap` keys; never silent weight change
- Top-n hivemind similarity in `emotions eval report` (Jaccard default; optional embedding)
- Gap-status fixtures may carry VERITAS-ish `gold_tags` (`underpowered`, `invalid_form`) without inventing new GapStatus enums
- Emotion mix soft guards: warn when mix is dominated by fear/anxiety/anger-type ids (annotation still returned)
- Optional `mix_intensity_cap` on ValueProfile (public_demo_strict_risk=0.35) caps non-epistemic mix mass
- EIG-inspired idea-graph export (`POST /v1/evals/idea-graph` / MCP `export_idea_graph`) — display only
- Offline HybridQuestion-style `cross_model_vote` — form/heuristic proxy; never silent re-rank
- Briefs include display-only `feasibility_note` (SFBench cousin — not a weighted axis)
- Offline soundness pass (`POST /v1/evals/soundness` / MCP `soundness_pass`) — form/gap annotations; not a global science judge
- Bayesian surprise worksheet fill (`emotions surprise-worksheet` / `POST /v1/surprise/worksheet` / MCP `surprise_worksheet`) — belief-shift logging only; **not** EVSI; does **not** rename `ScoreAxes.surprise`
- Composite eval report includes soundness + hivemind sections (`emotions eval report`)
- Agent card `/v1/agent` includes affective-safety blurb (not biometric ERS; provoke is opt-in framing)
- Dual-use: weighted heuristic classifier + combo signals + `human_review_risk` flag (W14) — **not** a biosafety oracle; residual evasion risk remains
- Explore may omit items flagged `dual_use_high` when disgust/`drop_dual_use` fires; the classifier remains heuristic with residual evasion — **not** a biosafety oracle and not dual-use solved
- Neglectedness/cost proxies: density/cites + trend/funding cues + investigation-scale lexicon — **not** funding DBs
- Optional HTTP API keys (`CURIOSITY_API_KEY` / `CURIOSITY_API_KEYS`) — unset = open local demo (WO-0.4.6)
- In-process HTTP rate limit (`CURIOSITY_API_RATE_LIMIT_PER_MINUTE`, default 60/min; `0` disables) — per-process soft guard, not a WAF
- Opt-in per-key HTTP quota (`CURIOSITY_API_QUOTA_REQUESTS` / `CURIOSITY_API_QUOTA_WINDOW_S`, default window 86400s) — unset/0 = no quota; in-process; not a billing meter
- Opt-in JSONL audit (`CURIOSITY_AUDIT_LOG`) of HTTP method+path / MCP tool name + status — default off; never bodies or keys
- CORS default deny (empty allow list); opt-in via `CURIOSITY_CORS_ORIGINS` (was `*` for the removed web demo)
- Versioned domain packs (`artificial_emotions/packs/*.json`, `load_bundled_packs` / `domain_pack_paths`) including alignment, climate, affective science, aging biology, and materials catalysis packs
- Domain pack lint (`emotions pack check`): CONTRIBUTING operationalization + why_it_matters bar on bundled (or `--path`) packs. Exit 1 on errors. Not a scientific review; not dual-use solved
- Structured HTTP errors (`{"error":{"code","message","details?"}}`) + `/ready` readiness (**503** when not ready)
- Central env config module (`artificial_emotions.config`) — LLM_*, CURIOSITY_API_KEY, timeouts, CORS, rate limit, quota, audit
- HTTP does **not** accept `literature_cache_dir` or `llm_base_url` (CLI/env only — path injection / SSRF)
- Ranked-unknowns export (`emotions export unknowns` / `POST /v1/export/unknowns` / MCP `export_unknowns`): JSON document of an already-ranked set (or CLI runs the pipeline). File / HTTP body is the v1 path. Arbitrary webhook URLs are **not** accepted (SSRF). Does not re-rank. HTTP does **not** write files (`out_path` rejected).
- Outcome-loop dry-run (`emotions loop --outcomes PATH`): preference JSONL `event_type=outcome` → suggested re-rank + next explore step. Does **not** run experiments, does **not** call `explore`. Not a lab closed-loop. CLI only (path; no HTTP path injection)
- CI: `.github/workflows/ci.yml` runs ruff + pytest on push/PR (independent of publish billing)
- Automated tests: core, failure-mode, provoke/API, MCP, emotions, mid-horizon, Alive, e2e — run `pytest -q` (1112 passed, 1 skipped)
- Smoke: `emotions spark`, `emotions profiles`, `emotions eval`, `emotions pack check`, `emotions export unknowns --no-literature --json`, `emotions loop --outcomes evals/fixtures/outcome_loop_smoke_v1.jsonl --json`, `emotions-mcp --list-tools`, `--list-resources`
- Offline vs literature artifacts under `examples/run_ai_*_final.json`
- Multi-domain seeds: biology, physics, ai, climate, medicine, materials, social, energy
- Failure-mode suite: `tests/test_failure_modes.py` encodes F1–F15 from `docs/LIMITS.md` / failure-mode tests
- Explicit ValueProfile on provoke/inject (F11); recency-aware likely-answered gate (F12)
- Download-and-run: `pip install -e .` then `emotions serve` **or** `emotions-mcp` — no vendor lock-in for LLM hosts
- Packaging: on PyPI as `artificial-emotions` (`pip install artificial-emotions`); editable install still fine for contributors (see `docs/PUBLISHING.md`)
- Alive continuity + imagination: CLI memory defaults, scars/costs/temperament/avoidance as biases, quarantined imagination, corpus-gated transfer (~5× lift), explicit dream reanalysis — see sections below and `CHANGELOG` `[0.4.0]` (serve/memory integrity hardening in `[0.4.1]`)

## Known limits

| Limit | Why | Mitigation path |
|-------|-----|-----------------|
| Heuristic scoring is lexicon/density based | No LLM required for demos | Set `use_llm=True` + API key |
| Appraisal rules that need literature, risk flags, previous-step context, or logged outcomes | Offline `spark` / `explore --no-literature` never sees related_works, dual-use flags, prior-step features, or preference outcomes | Named in `tests/test_appraisal_coverage.py`: 7 literature-gated (`perplexity`, `respect`, `envy`, `skepticism`, `satisfaction`, `triumph`, `disappointment`) plus catalog leftovers `admiration` / `gratitude`; 2 risk-flag (`anxiety`, `reluctance`) plus catalog `fear` / `disgust`; previous-step `embarrassment` / `relief` / `anger`; `pride` / `shame` need a logged outcome (`outcome_result` + question id) and stay silent without one; `hubris` needs confidence above the heuristic cap; `disorientation` needs an empty/collapsed rank; `suspicion` keeps a high surprise bar so it does not auto-enable OpenAlex. They are **not** claimed to fire on `spark`. PAD mood remains computational — not a VAD experience claim. |
| Topic contraction under AI tooling | Hao et al. *Nature* 2026: tools expand individual impact but can shrink collective topic volume | Neglectedness + diversity + explicit ValueProfile — not a claim we reverse the effect |
| Gap reading is phrase/overlap, not full-text comprehension | Abstracts are partial | Grounded LLM reader (optional) or full-text APIs later |
| OpenAlex / S2 neighborhoods can be topically noisy | Relevance search ≠ semantic match | Low overlap keeps `unanswered`; `both` merges sources |
| OpenAlex funder/affiliation metadata incomplete | Coverage ≠ accuracy (esp. outside WoS/Scopus overlap) | Treat funder signals as optional rationale keys only — not silent score weight |
| Seed set is curated (+ optional packs) | Offline reliability | LLM generation + CONTRIBUTING pack bar |
| Value weights are named presets or custom | No universal value-free ranking | Pass `profile_name` or custom `ValueProfile`; AI can shrink collective focus (McNamara / Hao *Nature* 2026; Bisht et al.) |
| Ranked unknowns ≠ post-execution quality | Ideation–execution gap (arXiv 2506.20803) | Treat ranks as decision aids; outcome flywheel is sparse / deferred |
| Axis scores are not EVSI/ENBS | No shared utility / PSA model | VOI worksheet is template fill only (`evsi: null`, `honesty: not_evsi`) |
| Multi-model / ensemble generation | Artificial Hivemind homogenization risk | Jaccard/embedding diversity + hivemind eval metric; disagreement ≠ value |
| Affective surfaces (cues / mix / provoke) | Framing can manipulate priorities without biometric ERS | Annotation-only honesty; mix coercion warnings; optional `mix_intensity_cap`; agent safety blurb; no silent user-affect inference |
| PAD mood carryover (4h half-life) | Continuity of stored P/A/D across sessions | Computational carryover, not a VAD experience claim |
| No longitudinal outcome calibration yet | Need impact follow-up data | **W-cal** scaffolding shipped (outcome-event hints + eval calibration telemetry); still **not calibrated**; no accuracy %; bands provisional |
| Embedding diversity is optional extras | Avoid heavy deps by default | `pip install '.[embeddings]'` + `diversity_backend=embedding` |
| Dual-use is weighted heuristic, not a trained classifier | Evadable phrasing remains; agentic scaffolding can uplift dual-use proxies (BioVeil MATRIX) | Human review hook + LIMITS residual; do not strip risk from inject/MCP; not BioVeil-certified |
| Neglectedness/cost are lexicon/density proxies | No grant/spend APIs wired | Documented spike; optional funding adapters later |
| LLM paths untested live in CI | `LLM_API_KEY` often unset | Local multi-provider smoke per PROOFS; no secrets in repo |
| Multi-judge ensemble needs live LLM | Offline uses single heuristic | Documented; disagreement flag only when ≥2 judges return |
| PyPI publish depends on Actions billing | Failed payment / spending limit aborts runners in ~2s | Fix Billing & plans; re-run `publish.yml` (see PUBLISHING) |
| Absolute local paths may remain in older git commits | Working-tree scrub does not rewrite history | Accept residual username-in-history risk, or squash/filter before first public clone wave |
| Moonshots (approx VOI, lab closed-loop) | Research tracks | Stubs only — v1 does **not** claim VOI, EVSI, or a lab loop. VOI worksheet is not EVSI; `emotions loop --outcomes` is a dry-run (JSONL → suggested re-rank / next explore), **not** experiment execution. Dual-use fixture expansion is not a league; residual stays residual. |
| Unauthenticated local HTTP when API key unset | Demo DX by design | Documented; set key + avoid `0.0.0.0` for non-local |
| HTTP rate limit is per-process only | In-memory sliding window by client host | Soft guard for local serve; use a reverse proxy/WAF for multi-instance |
| HTTP quota is per-process and per matched key | In-memory sliding window; no key → no quota bucket | Opt-in `CURIOSITY_API_QUOTA_*`; unset keeps local DX; not multi-tenant |
| Audit JSONL is local names+status only | Opt-in file; not a SIEM | Set `CURIOSITY_AUDIT_LOG`; never logs bodies or keys; default off |
| CORS default deny; auth still opt-in | Local CLI ergonomics vs browser demos | Set `CURIOSITY_CORS_ORIGINS` and/or API keys explicitly; not production hardening |
| MCP / `use_llm` can incur provider cost | Tools may call paid LLM hosts | Operator controls keys + MCP tier; no silent billing claims |

## Security posture (HTTP serve)

Default `emotions serve` is a **local soft guard**, not a hardened public API.
This is the **v1 baseline (local-v1)**. ROADMAP §7.5 “enterprise” means this
posture — opt-in keys, in-process rate limit, CORS deny, opt-in per-key quota,
opt-in audit JSONL — **not** multi-tenant SSO, TLS, a WAF, or SLOs.
Detail: [`THREAT_MODEL.md`](THREAT_MODEL.md) (not a production SLO).

- **Rate limiting:** in-process sliding window (default 60 req / 60s per client host). Not multi-instance safe; not a WAF.
- **Quota:** opt-in per matched API key (`CURIOSITY_API_QUOTA_REQUESTS` / `CURIOSITY_API_QUOTA_WINDOW_S`). Unset or `0` = no quota. Open local serve (no keys) does not apply a quota. Not a billing meter.
- **Auth:** required only when `CURIOSITY_API_KEY` / `CURIOSITY_API_KEYS` (or alias) is set. Unset keys → open routes (local CLI DX). Binding `0.0.0.0` without keys is operator risk.
- **CORS:** default empty allow list (deny). Opt-in via `CURIOSITY_CORS_ORIGINS`. Previously defaulted to `*` for the removed web demo.
- **Audit:** opt-in JSONL via `CURIOSITY_AUDIT_LOG` (HTTP method+path and MCP tool name + status). Default off. Never request/response bodies, headers, query strings, or API keys. Local operator log, not a SIEM.
- **No production hardening claim** — put a reverse proxy, TLS, and shared rate limits in front if you expose the API.

## Persistent memory (privacy)

CLI `explore` may write a local JSON file at `~/.artificial_emotions/memory.json`
(session summaries + question encounter counts). This is **usage history on your
machine**, not a cloud sync and not a model of the field.

- **Inspect / edit / delete** the file by hand, or use `emotions memory show`,
  `emotions memory forget <what>`, `emotions memory reset`.
- **Opt out:** `CURIOSITY_NO_MEMORY=1` (or `explore --no-memory`) — no read, no
  write; offline explore stays byte-identical to a fresh install.
- **Never on by default for MCP/HTTP** — only the CLI, where there is a single
  obvious user. Library `explore(..., persist_memory=False)` is the default.

**Scars, costs, temperament, avoidance** read that history as disclosed
**behavioral biases** (capped magnitudes, pattern-not-motive for avoidance).
They do not invent motives. `emotions dream` is explicit offline reanalysis of
the same file — never automatic, never “dream evidence.”

## Imagination quarantine

- Outputs travel only under the `imagined` payload key with
  `honesty: "imagined_not_retrieved"` and `confidence: null`.
- Never merged into ranked unknowns; never claimed as retrieved literature.
- Wired generators: `premortem`, `reformulation`, `counterfactual`.
  Stubs until generators land: `harm_scenario`, `rehearsal`, `eulogy`.
- **Transfer** is corpus-gated (`emotions imagine transfer --seed … --corpus …`),
  not applied over a ranking. Ship gate: ≈5× lift vs random pairing on the
  bundled timesplit corpus; dense-corpus control collapses to chance.


## Confidence interpretation

- `~0.25–0.35`: no literature / unknown caveat
- `~0.45–0.58`: heuristic + literature neighborhood (cap while heuristic)
- Higher: requires LLM judges and/or stronger evidence
- Bands widen further when `judge_disagreement` fires

Scores are **decision aids**, not oracles. Displayed `[low–high]` bands widen when confidence is low.
