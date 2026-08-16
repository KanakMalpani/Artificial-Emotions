# Changelog

## [Unreleased]

### Added
- Calibration coverage counts on `emotions eval calibration`: unique
  questions, repeat-outcome ids, distinct result labels, score-then-outcome
  pairing. Counts and magnitudes only — **not** accuracy, ECE, Brier, or a
  `proof_ready` latch. Bundled smoke JSONL still has zero repeat-outcome ids.
  §10 proof remains unmet (no real longitudinal impact dataset).
- **Non-loopback bind opt-in.** `emotions serve` still defaults to
  `127.0.0.1`. `--host 0.0.0.0` / `CURIOSITY_HOST=0.0.0.0` / LAN binds
  require `CURIOSITY_ALLOW_NONLOCAL_BIND=1` or the CLI exits `2` without
  starting uvicorn. Direct `uvicorn --host 0.0.0.0` bypasses the guard.
  Still not TLS, not a WAF, not multi-tenant, not production HTTP.

### Changed
- Honesty lockstep: advertised pytest counts, coverage snapshot, and hard
  non-claims stay aligned across LIMITS, PROOFS, ROADMAP §2, and README.
  Calibration **proof** (§10) and production HTTP remain **v1.1**. Scores
  still **not calibrated**. HTTP still local-v1 (not TLS/WAF/SLOs). Dual-use
  still residual.
- Internal architecture (no `/v1` change): catalog `when` evaluation lives in
  `appraisal_interpreter.py`; `appraisal.py` remains the stable import and
  run-dispatch path. Preference JSONL / in-memory event parsing is one seam
  (`normalize_preference_events`); corrupt rows still skip, now logged at
  WARNING via `soft_fail`. `coerce_preference_event` skips only
  `ValidationError` and `JSONDecodeError` — other exceptions propagate.
  Shared helpers: `RankedQuestion.flag_set` / `score_band_width`,
  `validate.concept_pool`, `timeutil.parse_iso` / `utc_now` /
  `utc_now_iso` (PreferenceEvent stamps; surprise-worksheet `logged_at`).
  Catalog `APPRAISAL_USE_FOR` is the `use_for` text map (not RULES
  lambdas); empty-run confusion still reads that map. Optional swallows
  in domain-pack load, transfer/discovery evidence titles, and mix-cap
  profile lookup log via `soft_fail` — corrupt JSON / unknown preset /
  missing optional files still skip; unexpected exceptions still raise.
  Catalog effect applicators live in `modulate_effects.py`; `modulate.py`
  remains the stable import and plan assembly path. Frozen effect ids
  unchanged. MCP tool implementations live in `handler_families/` with
  `handlers.py` as the stable re-export — no schema, mcp_lint, or `/v1`
  change. Preference JSONL I/O lives in `preference_events.py`; weight-hint
  math lives in `preference_hints.py`; `preferences.py` remains the stable
  import (preview default, `--apply` / `apply=true` copy, named presets
  never overwritten).   Ranked imagination generators live in
  `imagine_twins.py` and `imagine_counterfactual.py`; `imagine_lenses.py`
  re-exports them; `imagine.py` remains the public registry /
  `apply_imagination` import. Six ranked-applicable kinds are wired
  (`premortem`, `harm_scenario`, `rehearsal`, `eulogy`, `reformulation`,
  `counterfactual`); transfer stays corpus-gated. `apply_imagination`
  MCP/OpenAI kind enum is additive (the six wired ranked kinds; transfer
  stays on `imagine_transfer`). `/v1` imagination notes no longer call
  ranked kinds stubs. Quarantine and driving-emotion wiring unchanged.
  No new lenses. CLI `discover` / `stance` / `imagine` live in
  `cli_pkg/commands/lenses.py`; CLI `explore` lives in
  `cli_pkg/commands/explore.py`; `ranking.py` keeps `run` / `spark` /
  `serve` and re-exports the lens handlers and `_explore`. Domain jump
  helpers live in `explore_domains.py`; dual-use omission in
  `explore_drop.py`; `explore.py` remains the stable loop import.
  CLI argparse lives in `cli_pkg/parser/` groups (`core` /
  `evaluation` / `alive` / `worksheets`); `build_parser` /
  `cli_pkg.parser` remain the facade. Flag names, defaults, and help
  semantics unchanged, including serve help for
  `CURIOSITY_ALLOW_NONLOCAL_BIND` (bind refuse still in the serve
  handler). Scars jump-order dict is the `explore_domains` source (no
  `explore.py` import — that would cycle). MCP/OpenAI JSON Schema fragments
  live in `schema_families/` with `schemas.py` as the stable re-export —
  same family cut as handlers, no schema or mcp_lint change. Catalog load
  lives in `emotions_catalog.py`; mix math in `emotions_mix.py`;
  `emotions.py` remains the public import (cues, pack, catalog, mix).
  Catalog `when` / `use_for` / honesty payload unchanged. `memory.py` and
  `dream.py` stay one module each (persistence unit; reanalysis + honesty
  guards have no second caller). Not calibrated. Not EVSI.
  Loop remains dry-run. Audit `ts` remains Z-strftime. HTTP is not
  production. Dual-use residual. Not phenomenal.

## [1.0.0] — 2026-08-15

1.0.0 is a curiosity layer that ranks unknowns as **decision aids** under an
explicit `ValueProfile`. Scores are **not calibrated**. Dual-use classification
is heuristic and **residual**. HTTP (`emotions serve`) is a **local** soft
guard, not a production SLO. This release does not claim EVSI, a lab
closed-loop, phenomenal feeling, production HTTP, or dual-use solved.

### Added
- **Ranked-unknowns export.** `emotions export unknowns --json` (optional `--out FILE`,
  `--from` a previous `run --json`) plus `POST /v1/export/unknowns` wrap pipeline
  output as a JSON document. File / HTTP body is the v1 path. Arbitrary webhook
  URLs are **not** accepted (SSRF). Does not re-rank. MCP `export_unknowns`
  takes inline questions only.
- **Local HTTP threat model.** `docs/THREAT_MODEL.md` names the local
  `emotions serve` posture (in-process rate limit, CORS deny-by-default,
  auth opt-in, opt-in per-key quota, opt-in audit JSONL). Not a production
  SLO. ROADMAP §7.5 enterprise = this local-v1, not multi-tenant.
  `GET /v1/agent` honesty points at it.
- **Outcome-event weight hints.** `learn_profile_weight_hints` consumes
  `event_type=outcome` rows with `score_axes` plus `labels.result` (tiny
  prefer/reject-like deltas; floors so no axis zeros). Silent without usable
  events. Apply still requires `apply_weight_hints_to_profile` / `--apply`.
  Not calibrated.
- **Preference weight-hint preview vs apply.** `emotions preferences hints`,
  MCP `preference_weight_hints`, and `POST /v1/preferences/hints` default to
  preview (`mode=preview`, `applied=false`). `--apply` / `apply=true` returns
  an `applied_profile` copy via `apply_weight_hints_to_profile` — never
  overwrites a named preset. HTTP/MCP take inline events only (no filesystem
  paths). `emotions run --preference-learn` is preview unless
  `--preference-learn-apply`. Not calibrated.
- **Preference calibration telemetry.** `emotions eval calibration` reads
  offline JSONL and reports counts, outcome mix, and hint magnitudes — **no
  accuracy %**. Shared `--path` on `eval` (optional; default smoke fixture).
  Not a calibration certificate.
- **Per-key HTTP quota.** Opt-in `CURIOSITY_API_QUOTA_REQUESTS` plus
  `CURIOSITY_API_QUOTA_WINDOW_S` (default 86400s). Unset/0 = no quota (local
  DX unchanged). 429 `quota_exceeded` with `Retry-After`. In-process per
  matched API key — not multi-tenant, not a billing meter.
- **Opt-in audit JSONL.** Set `CURIOSITY_AUDIT_LOG` to a file path. Records
  HTTP method+path and MCP tool name + status only. Default off. Never
  bodies, headers, query strings, or API keys. Local operator log, not a SIEM.
- **Domain pack lint.** `emotions pack check` lints bundled (or `--path`)
  domain packs against the CONTRIBUTING seed/pack bar: operationalization
  (≥20 chars) and stakeholder `why_it_matters` (no placeholders). Exit 1 on
  errors. Not a scientific review; not dual-use solved. `emotions pack`
  still loads affective_science seeds.
- **LangGraph host recipe.** Copy-paste snippet in `docs/PLUGINS.md` loads
  `GET /v1/agent/tools` and executes via `http_fallbacks`. `langgraph` is not
  a package extra. Smoke is the tools payload, not a LangGraph CI job.
- **VOI worksheet honesty fields.** `fill_voi_worksheet` (CLI `voi-worksheet`,
  `POST /v1/voi/worksheet`, MCP `voi_worksheet`) always emits `evsi: null` and
  `honesty: not_evsi`. Optional `estimate_evsi` hook returns None without
  PSA/utility data and never invents a number. Additive `/v1` fields only.
  Not EVSI/ENBS.
- **Outcome-loop dry-run.** `emotions loop --outcomes PATH` reads preference
  JSONL `event_type=outcome` rows and suggests a re-rank plus a next explore
  step. Does **not** run experiments and does **not** call `explore`. Not a
  lab closed-loop. CLI only (no HTTP path injection). Fixture:
  `evals/fixtures/outcome_loop_smoke_v1.jsonl`.
- **Elicit A/B + dual-use fixture expansion.** Extra climate elicit sample
  responses (`examples/elicit_ab_sample_responses_climate.json`) and a larger
  dual-use red-team regression corpus (`residual_may_miss` documents LIMITS
  evasion). Not a league; not dual-use solved; not EES.

### Changed
- **Explore honors `drop_dual_use` / `forbid_similar_jump`.** Disgust may omit
  `dual_use_high` items; anger `--somatic-modulate` skips similar-domain jumps.
  Classifier remains heuristic — not dual-use solved (LIMITS).
- **Catalog-only appraisal dispatch.** `appraise_run` evaluates catalog `when`
  / `use_for` only. The former `RULES` golden is **deleted**. All **54** emotion
  rows carry a non-empty `when` (or `requires: outcome_event` plus a firing
  fixture) and a use. Coverage floor is `MIN_CATALOG_SHARE = 1.0`.
- **Somatic search knobs stay opt-in** via `--somatic-modulate`
  (`CuriosityConfig.somatic_modulate`). High-coercion ids still appraise and
  surface when the flag is off. They never raise the risk ceiling.
- **Pride and shame need logged outcomes.** They fire on `outcome_result` plus a
  question id (`--preference-log`); they stay silent without one. They are not
  triumph-from-rank.

### Honesty
- §7.6 stubs shipped; moonshots remain moonshots. v1 does not claim VOI, EVSI,
  or a lab closed-loop. Dual-use residual stays residual.

### Fixed
- Pytest `pythonpath` includes the repo root so Ubuntu collection can import
  `tests.*`. Tag `v1.0.0` CI died in collection (`No module named 'tests'`);
  local Windows still collected. Runtime package unchanged.

## [0.4.1] — memory integrity + API serve hardening

Patch release for silent memory wipe risk and open HTTP serve defaults that
landed after `0.4.0` but were not yet tagged.

### Fixed
- **Atomic memory save:** write `memory.json` via `.tmp` + replace so a truncated
  write cannot leave an empty file that wipes history on next load.
- **Corrupt reads:** preserve unreadable `memory.json` as `*.corrupt*` instead of
  silently starting empty.
- **Rate-limit probe exemptions:** `/health` and `/ready` skip the same open-path
  exemptions as auth so probes stay reachable under load.

### Changed
- **HTTP rate limiting** on API routes (configurable; defaults disclosed in
  `docs/LIMITS.md`).
- **CORS default empty** (no `*` wildcard) — callers must opt in explicitly.

### Removed
- **`web/`** demo surface: Vite SPA, mood-shell GIF / capture pipeline,
  Playwright web smoke (`tests/e2e/test_web_playwright.py`), and CI `web` job.
  Continuity visual proof remains `docs/media/avoidance.svg`.

## [0.4.0] — Alive (continuity + imagination)

Functional continuity and quarantined imagination. Affect can outlive a process,
cost something, and generate what is not yet there — without phenomenal claims.

Package version `0.4.0`. Superseded for serve/memory hardening by `[0.4.1]`.

**Correction (2026-08-02):** early `0.4.0` notes said PyPI upload was deferred.
That stopped being true when `0.4.0` published — install path is
`pip install artificial-emotions` (see `docs/PUBLISHING.md`). Hardening that
justifies upgrading from that release is recorded under `[0.4.1]`.

### Added — continuity
- **`memory.py` — persistent CLI memory.** Local JSON at
  `~/.artificial_emotions/memory.json` (sessions, encounters, mood carryover).
  **Defaults:** CLI `explore` may persist; library / MCP / HTTP stay off
  (`persist_memory=False`). Opt out entirely with `CURIOSITY_NO_MEMORY=1`.
  Inspect / forget / reset via `emotions memory show|forget|reset`.
- **`scars.py` / affinities** — history biases the bar for returning to dead
  ground and the pull toward what paid off. Disclosed magnitudes, capped;
  **behavioral bias, not motive.**
- **`costs.py` — affect that can make a run worse.** Downside twins of helpful
  modulation; never raises risk ceilings; always disclosed.
- **`temperament.py` — instance `.toml` personality.** Biases appraisal swing
  and search knobs so *this* install diverges from a fresh one.
- **`avoidance.py` — persistent non-selection patterns.**
  `emotions memory avoiding` reports questions seen often and never picked.
  Honesty: `pattern_not_motive` — cannot distinguish avoidance from judgment.
- **`dream.py` — explicit offline reanalysis** of stored history
  (`emotions dream`). Never automatic / background. Payload honesty:
  `offline_reanalysis_of_stored_history` (not labeled as evidence of dreaming).

### Added — imagination
- **`imagine.py` — quarantine + stance-twin generators.** Imagined material
  travels only under the `imagined` payload key with
  `honesty: "imagined_not_retrieved"` and `confidence: null`. Never merged into
  ranked lists. Wired offline generators today: **premortem**, **reformulation**,
  **counterfactual**. Stubs (generators landing next): `harm_scenario`,
  `rehearsal`, `eulogy`.
- **`transfer.py` — corpus-gated structural analogy.** Separate from
  `apply_imagination` (no ranked-item path). Cleared the `validate.py` lift
  ship gate on the bundled timesplit corpus (**≈5×** over random pairing;
  dense-corpus control collapses to chance). CLI:
  `emotions imagine transfer --seed … --corpus …`,
  `emotions validate --method transfer …`.
- Surfaces: `emotions imagine`, `list_imagination_kinds` / `apply_imagination`
  (MCP). Memory / dream / transfer agent tools and HTTP routes are landing in
  parallel — see `agent_tools_pkg/registry.py` and `/v1` discovery; do not treat
  route tables in older docs as exhaustive.

### Added — mood-reactive local demo
- **`web/`** — Vite SPA with affect-derived tokens, stance lenses, imagination /
  memory stubs, and Playwright mood-shell snapshots. **Local demo evidence
  only** — no deploy, auth, multi-user, or server-side persistence. Product
  scope for `web/` is frozen at demo quality.

### Honesty
- Continuity modules bias behaviour; they do not invent motives or feelings.
- Imagination stays quarantined; transfer never injects into ranking.
- Affect may still tighten safety gates, never loosen them.

### Internal
- ~680 tests after Alive. Coverage floor unchanged.

## Unreleased — stances: curiosity is not the only useful feeling

Widening appraisal made 37 emotions *derivable* and 22 of them able to change
search behaviour. It did not change the fact that every entry point in the repo
asked one question: **"what is most worth investigating?"** Emotions other than
curiosity could only ever be modifiers on that — and the 15 declared
`OBSERVATION_ONLY` could not even do that. They were named, disclaimed, and
otherwise idle.

### Added
- **`stances.py` — seven non-curiosity questions over one ranked set.** A stance
  does not rank; it reads an existing ranking looking for something else.
  `doubt` (which of these am I most likely to be wrong about?), `safety` (which
  could hurt someone, and who reviews it?), `focus` (if only one, what exactly
  do I do first?), `close` (what do we stop doing, and what do we write down?),
  `taste` (which are badly posed, regardless of whether they matter?), `wonder`
  (what is most surprising, regardless of whether it is valuable?), `survey`
  (who already owns this ground?).
- **`wonder` deliberately ignores your ValueProfile.** It ranks on surprise and
  neglectedness alone, then reports where that *disagrees* with your values — a
  profile that never surprises you is filtering something out, and this is how
  you find out. It is the only surface here that is allowed to not care what you
  said you wanted.
- **Every appraisable emotion now has a use.** 22 modulate search, 26 drive a
  stance, and the union is 37 of 37. The six that had neither — `enjoyment`,
  `insight`, `interest`, `surprise`, `uncertainty`, `wonder` — drive the `wonder`
  stance.
- Surfaces: `emotions stance <name>` and `emotions stance list` (CLI),
  `list_stances` / `apply_stance` (MCP + OpenAI tools), `GET /v1/stances` and
  `GET /v1/stances/{stance}` (HTTP).
- **`tests/test_stances.py`** — guards the two ways this could rot: a stance that
  agrees with the curiosity ranking on everything is decoration, and a stance
  that quietly reorders the set would make the ValueProfile a lie. Also asserts
  `taste` actually fails a malformed question rather than rubber-stamping.

### Honesty
- **A stance is a view, never a verdict.** It cannot rescore or reorder anything.
  Every payload carries `honesty: "stance_view_only"` and explicitly disclaims
  re-ranking; a test asserts the input ordering is unchanged afterwards.
- No stance is driven by `curiosity` — that is the ranking's job, and a test
  enforces it. Stances exist for the questions ranking cannot answer.

### Changed
- The anti-decoration guard now makes the **stronger** claim. It previously
  accepted `OBSERVATION_ONLY` as sufficient justification for an emotion
  existing; that is an honest label but still describes something the system
  names and never uses. It now requires every appraisable emotion to modulate
  search *or* drive a stance, and separately checks that no observation-only
  emotion is left stranded without one. Floors: 7 stances, 24 stance drivers.
- Fixed the CLI stance printer repeating a whole list per row instead of the row.

### Internal
- 616 tests.

## Unreleased — the whole catalog earns its keep

54 emotions existed; **four** ever fired. The rest were furniture.

### Fixed
- **Appraisal could derive only 13 of 54 catalogued emotions, and just four
  (`curiosity`, `humility`, `insight`, `determination`) fired across all nine
  domains.** Rules are now explicit condition/weight functions over one context
  object: **37 emotions derivable (68% of the catalog)**, 9-10 firing per step.
  New rules read signals the engine already computed but ignored — dual-use
  flags, score-band width, near-duplicate rate, answered-gap ratio, ungrounded
  LLM citations, literature density and citation counts, operationalization
  shape, score spread, cost.
- **Normalisation was crushing every secondary emotion below the action floor.**
  Modulation keyed off mix *percentages*, which shrink as more emotions fire — a
  strong signal at 0.25 became ~8% of the blend and never acted. It now keys off
  appraised strength, which measures how strongly the situation presented rather
  than how crowded the blend was. Distinct emotions changing behaviour per run
  went from 2 to 4+.
- `perplexity` was declared observation-only while actually modulating (it is
  summed into confusion). Caught by the new guard.
- `absorption` could not veto the stop because momentum was resolved *after* the
  stop rule ran. Momentum is now resolved first, so a live thread survives a bad
  step.

### Added
- **Consequences for 14 more emotions.** `anxiety`/`reluctance` tighten
  `max_risk` and demand review; `skepticism`/`suspicion` force the soundness
  pass and fetch literature; `disorientation` shrinks and reframes;
  `absorption`/`hope`/`anticipation` hold the ground; `urgency`/`impatience`
  narrow to the cheap step; `triumph`/`satisfaction` turn a result into a plan;
  `disappointment` records nulls and moves.
- **`OBSERVATION_ONLY`** — 15 emotions appraised and surfaced but deliberately
  never acted on. Aesthetic pull (`elegance`, `parsimony`) and social comparison
  (`envy`, `respect`) are real drivers of research choices *and* known biases, so
  they are shown to the reader rather than obeyed.
- **`tests/test_appraisal_coverage.py`** — the anti-decoration guard. Every rule
  must be firable from a constructible context, must not fire on a neutral one,
  and must either modulate behaviour or be declared observation-only. It found
  all three bugs above.
- Runs print `acted:` and `observed:` separately.

### Honesty
- Affect may make a safety gate **stricter, never looser**: `anxiety` lowers
  `max_risk` and nothing raises it. Scoring weights remain untouched by default.

- **Ratcheted the guard to lock in the gains.** Its floors previously allowed a
  slide back to 30 rules while still passing. They now sit just under the
  achieved numbers (35 rules, 62% of catalog, 20 acting, 8 firing offline, 3
  distinct drivers per loop) so ordinary churn passes but a real regression
  fails. Added two reachability checks against *real* runs rather than
  constructed contexts, and a direct regression guard for the normalisation bug:
  a secondary signal must still act when a louder emotion fires beside it.
  Verified by reverting the fix — the guard fails.

### Internal
- 603 tests, 88.7% coverage.

## Unreleased — discovery, and evidence that it works

### Added
- **`validate.py` — retrospective validation.** The repo's one falsifiable claim
  about its own usefulness. Hide everything from a cutoff year onward, run ABC
  discovery on the past alone, then check which proposed A–C links actually
  appear in the held-out future. On the bundled time-split corpus, discovery from
  pre-1986 literature proposes fish oil → Raynaud's and finds it confirmed
  post-1986 — the case Swanson actually got right, reproduced as a test.
- **A random-pairing baseline, and lift.** A bare hit rate is precisely the
  vanity metric `evals/METHODOLOGY.md` forbids: on a dense corpus you could
  "confirm" most random pairs and look brilliant. Every run therefore pairs A
  against randomly drawn concepts from the same pool and measures how often those
  land. `test_lift_falls_to_chance_when_the_future_confirms_everything` asserts
  lift collapses to 1.0 when a dense future confirms everything, so the metric
  cannot quietly become flattery.
- The control pool is *not* filtered to exclude concepts the method also
  proposed, so it can score its own hits. That makes lift a floor rather than a
  ceiling — the conservative direction to err in, and it is stated in the report.
- `emotions validate --corpus … --cutoff … --seeds …`, plus a bundled time-split
  demo corpus shipped in the wheel.

### Honesty
- The report disclaims being a benchmark, claiming significance at this sample
  size, attributing confirmed links to anything the method knew, or generalising
  beyond the supplied corpus.
- The bundled corpora are small illustrative fixtures that demonstrate the
  mechanism. They are not scraped datasets and are not evidence about any field.

### Internal
- 510 tests, 88% coverage.

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
- Honesty: emotions annotation_only; scores ≠ oracles. *(Original line also said
  “not on PyPI”; that claim was corrected when the package published — see
  correction under `[0.4.0] — Alive` above.)*

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
