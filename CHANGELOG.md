# Changelog

## Unreleased — the affect loop

Affect stops being a label and starts being a cause.

### Added
- **`appraisal.py` — emotion as the output of evaluation.** Given what a run
  actually encountered (open gaps, judge disagreement, thin evidence under high
  confidence, ground already covered), it derives what the system should be
  feeling and why. Every signal carries `because` and `evidence`: affect you
  cannot audit is affect you cannot trust. Notably the system appraises *itself*
  for `hubris` — high confidence on heuristic, literature-free evidence — and for
  `humility` when thin evidence is met with correspondingly low confidence.
- **`trajectory.py` — session memory.** Questions seen, vocabulary mined, dead
  ends, surprises. Boredom is impossible without a past; this is the past.
- **`modulate.py` — affect with consequences.** Curiosity widens the candidate
  pool, confusion narrows and forces decomposition, boredom suppresses
  duplicates and changes ground, hubris makes the system go and fetch
  literature, frustration stops the loop and records the dead end.
- **`explore.py` — the loop.** `rank → appraise → feel → modulate → remember`,
  returning a research trajectory: every step, what it felt, the evidence, what
  that changed, and a decomposed plan for the best unknown found. Offline and
  deterministic. Surfaced as `emotions explore`, `POST /v1/curiosity/explore`,
  and MCP tool `explore_curiosity`.

### Honesty
- **Affect modulates search behaviour, never the stated scoring weights.**
  Ranking remains a pure function of the supplied `ValueProfile`. Weight
  modulation is opt-in (`allow_weight_deltas`), capped at `MAX_WEIGHT_DELTA`
  (±0.08, the same ceiling the preference-hint path uses), and every delta is
  reported. Both directions are pinned by tests — the default leaves the profile
  untouched, and the opt-in path stays bounded and logged.
- `explore` disclaims what it is not: no answers, no optimal search, no
  closed-loop scientist, no biological emotion.

### Fixed
- Term saturation was measured *after* folding the current run into memory, so
  every step scored as already-seen against its own vocabulary and boredom
  pinned high from step one. Memory is now snapshotted before the fold.
- Step notes named the loudest feeling rather than the one that actually moved
  the knob (`determination` forced decomposition while the note credited
  `curiosity`). Notes now report the real driver.

### Internal
- 458 tests, 89% coverage. `modulate.py` at 100%.

## Unreleased — Artificial Emotions

### Renamed
- Project, distribution, and import path are now **Artificial Emotions** /
  `artificial-emotions` / `artificial_emotions`. MCP server id, agent manifest,
  docs, CI, and the FastAPI title follow. Console scripts are `emotions` and
  `emotions-mcp`; the pre-rename `curiosity` / `curiosity-mcp` names remain as
  aliases so existing MCP host configs keep working.
- Deliberately **not** renamed: HTTP route namespaces (`/v1/curiosity/*`),
  `CuriosityEngine`, `CuriosityConfig`, and `curiosity_score`. Those name the
  mechanism, not the product, and renaming them would break the pinned API
  contract for no gain.

### Added — computational affect, expanded
- Emotion catalog **25 → 54** entries across **six** families: `epistemic` (22),
  `basic` (7), `social` (8), `achievement` (8), and two new ones — `aesthetic`
  (elegance, sublimity, dissonance, parsimony) and `volitional` (determination,
  impatience, reluctance, urgency, persistence).
- `humility` and `hubris` are both catalogued on purpose: the discipline this
  project is built around and the failure mode it exists to flag each need
  vocabulary.
- **Mixing past 2-component dyads.** `blend_triad_hint` names 3-component
  blends (`disciplined_inquiry`, `premature_eureka`, `overclaim_risk_state`, …),
  matching exactly at three components and on the top three by weight above
  that. The existing `plutchik_dyad_hint` contract is unchanged.
- **`ambivalence`** detects opposing entries held at once, scored as mass ×
  balance across 13 opposition axes. A mix carrying `conviction` beside live
  `doubt` now reads as a different stance, and `felt_simulation` says so —
  "I am pulled two ways … name the observation that would settle it" — instead
  of averaging the tension away. Sustained ambivalence is reported as an honest
  state, not an error.
- Four new cue tags registered in the stable vocabulary: `overclaim_risk`,
  `insight_candidate`, `scope_creep_risk`, `dead_end_risk`.

### Added — curiosity depth
- **`artificial_emotions.decompose`** takes one ranked unknown a step further
  toward a solution without becoming an answer engine. It expands a question
  into measurement / baseline / mechanism / confound / boundary sub-questions
  (recursively, to depth 3), names the single observation worth making first,
  derives falsifiers from the stated operationalization (`AUROC >= 0.7` →
  *refuted if AUROC < 0.7*), and emits stop rules — including a review gate when
  the risk axis is elevated.
- The invariant is enforced rather than intended: `assert_free` scans the whole
  payload for assertion language and the result ships as `assertion_free`. Every
  decomposition ends by stating that the original gap is **not** thereby closed.
- Exposed on all four surfaces: `emotions decompose`, `POST
  /v1/curiosity/decompose`, MCP/OpenAI tool `decompose_question` (tier
  `investigate`), and the Python API. Fully offline and deterministic.
- 60 new tests; coverage 87% → 88% across 415 tests.

## Unreleased

### Fixed
- **Worksheet templates and eval fixtures now work when installed.** `bayesian`,
  `voi`, `compare`, `elicit_eval`, `evals`, and the `curiosity eval` /
  `voi-worksheet` / `surprise-worksheet` commands resolved data via
  `Path(__file__).parents[2]`, a path that only exists in a source checkout —
  every `pip install` hit `FileNotFoundError`. Data files are now force-included
  into the wheel and resolved by `artificial_emotions.resources`, which prefers
  the packaged copy and falls back to the checkout.
- `classify_value_error` returned `unknown_emotion` for "unknown emotion pack"
  messages, because the general check ran before the specific one. Pack errors
  now classify as `unknown_pack`. Error codes are public contract.
- CI had been failing on every push since the workflow was added (14 ruff
  errors, 20 files off `ruff format`). Lint and formatting are clean.
- **Ranked output was not reproducible.** Flag lists were rebuilt with
  `list(set(...))`, so their order followed PYTHONHASHSEED and an identical run
  emitted different JSON on every invocation — breaking run-to-run diffs,
  caching, and golden-output tests. Replaced with an order-preserving
  `scoring.dedupe_flags`; `tests/test_output_determinism.py` runs the CLI under
  three different hash seeds to keep it fixed.
- `test_soundness_pass_offline` was defined twice in `tests/test_mid_horizon.py`;
  the second silently replaced the first, so the surprise-worksheet assertions
  never ran and `bayesian.py` sat at 0% coverage. Renamed to
  `test_surprise_worksheet_offline`.

### Changed
- `ruff` pinned to `>=0.15,<0.16` — `ruff format --check` is version-sensitive,
  so the previous `>=0.6,<1` range let CI reformat the tree and go red on its own.
- CI matrix adds Python 3.13 (already advertised in the classifiers), enforces a
  coverage floor, and gained a `packaging` job that installs the built wheel into
  a clean environment and exercises the data files and console scripts from
  outside the checkout.

- The PyPI publish workflow built and uploaded without running the test suite or
  checking that the artifact worked. It now runs lint + pytest first, runs
  `twine check`, and installs the built wheel into a clean environment to
  exercise its data files and console scripts before upload.

### Added
- `artificial_emotions.resources` — package-first data file resolution.
- Test coverage for surfaces that had none: the MCP stdio read loop and
  `curiosity-mcp` argv handling, the full CLI subcommand surface, the
  OpenAI-compatible client (credential precedence, tolerant JSON extraction,
  the `response_format` retry that keeps local providers working), the
  Semantic Scholar backend, and the judge's soft-fail and
  anti-hallucination-grounding contracts. All offline — no network, no keys.
- Coverage 78% → 87%; 146 → 327 tests. Floor enforced at 85%.

### Internal
- `api.py` (1141 lines) split into `api_pkg/`: app assembly, `security.py`,
  `error_handlers.py`, `schemas.py`, and six routers grouped by URL prefix.
  `artificial_emotions.api:app` and every previously importable name still
  resolve from `artificial_emotions.api` — the generated OpenAPI (32 paths,
  18 component schemas) and the middleware order are byte-identical to before.
  Added `tests/test_api_wiring.py` to pin the served path set, the
  auth-wraps-CORS ordering, and that no router module can be left un-included.
- `cli.py` (929 lines) split into `cli_pkg/`: parser definitions plus one module
  per subcommand group. Verified against a captured baseline — the full argparse
  contract (every subcommand, option, default, and help string) and all 20
  sampled command outputs are unchanged. The bare-flag fallback now derives
  subcommand names from the parser instead of a second hardcoded list.
- `agent_tools.py` (1147 lines) split into `agent_tools_pkg/` as
  schemas → handlers → registry → mcp_resources, a one-way dependency chain.
  The captured tool contract — every schema, tier listing, `curiosity://`
  resource, and dispatch result — is byte-identical.
- No source or test file now exceeds 800 lines.
- `test_mid_horizon.py` (1375 lines) split by theme into
  `test_wedges_literature_gap.py`, `test_wedges_preferences.py`,
  `test_wedges_safety_packs.py`, and `test_wedges_worksheets.py`. No test
  bodies changed.
- `config.py` env reference now lists `CURIOSITY_MCP_TIER`.

## 0.4.0 — 2026-07-24

Production-ready hardening of the public surface (emotions + API + plugins).

### Docs / packaging surface (same release line)
- World-class README + docs INDEX / CONTRIBUTING / examples index aligned to v0.4.0
- ROADMAP_SUMMARY + PUBLISHING version pins corrected (were stale at 0.3.1)
- Honesty: not on PyPI; emotions annotation_only; scores ≠ oracles

### Added
- Central `artificial_emotions.config` (env knobs: LLM_*, CURIOSITY_API_KEY, timeouts, CORS)
- Structured errors (`CuriosityError` + stable codes) and HTTP exception handlers
- `GET /ready` readiness checks; richer `/health` (version, timeouts, auth/cors summary)
- CI workflow (`.github/workflows/ci.yml`): ruff + pytest on PR/push (separate from publish)
- Stdlib logging on optional lit/LLM/embedding soft-fails

### Changed
- Package version **0.4.0**; Development Status classifier → Beta
- Dependency ranges clarified (`pydantic`/`fastapi`/`uvicorn` upper bounds; extras `dev`, `embeddings`)
- Emotion mix/catalog/annotate raise typed `CuriosityError` (still subclasses `ValueError`)
- Auth reject responses use `{ "error": { "code": "auth_required", … } }`
- Regenerated `examples/openai_tools.json` to include emotion catalog/mix tools
- HTTP no longer accepts `literature_cache_dir` or `llm_base_url` (CLI/env only — path injection / SSRF)
- `/ready` returns **503** when checks fail

### Honesty
- Emotions remain **annotation_only** framing — not felt affect; scores ≠ oracles
