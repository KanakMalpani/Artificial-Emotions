# Expert-eval / spot-check methodology (W10)

**Purpose:** Measure gap-gate quality offline with labeled fixtures — not to
publish a vanity “accuracy %” for marketing.

## What we measure

| Signal | Meaning |
|--------|---------|
| Case-level status match | Predicted `GapStatus` vs gold label |
| Missed answered (F1) | Gold `likely_answered` but predicted otherwise |
| False unknown rate | Same as above among answered gold cases |
| Phrase-gaming holdouts | Topic-adjacent open-gap abstracts stay `unanswered` (F7) |
| Recency holdouts | Stale strong overlaps should not auto-promote to `likely_answered` (F12) |

We **do not** collapse these into a single product accuracy claim. Report
case-level tables + F1-style miss rates only.

## Fixture quality bar

Each case should include:

1. One primary unknown + operationalization (≥ measurement bar).
2. Pre-baked literature hits **or** empty hits (unknown caveat).
3. Gold `GapStatus` justified in `notes` (which failure mode).
4. Adversarial cases: open-gap language, weak ops overlap, stale years.

Bundled set: `evals/fixtures/spotcheck_v1.json` + `spotcheck_v2.json`
(adversarial F7 / weak-ops / empty-hits). Default `curiosity eval` loads the
whole fixtures directory.

Report also includes `by_gold_status` (stratified gold→predicted counts) —
still **not** a single product accuracy claim.

## How to run

```bash
curiosity eval
# or
python -c "from artificial_emotions.evals import run_spotcheck; print(run_spotcheck().to_dict())"
pytest tests/test_mid_horizon.py::test_w10_spotcheck_harness_offline -q
```

## Protocol for human spot-checks (optional)

1. Sample top-10 ranked questions from a real run (offline or lit).
2. Blind: label each as unanswered / partial / likely_answered / unknown.
3. Append labels via preference JSONL (`event_type=already_answered|keep`) with
   optional `score_axes` for weight hints.
4. Optionally set `preference_rerank_path` for thin profile-scoped re-rank
   and/or `preference_learn_path` / `POST /v1/preferences/hints` for tiny
   ValueProfile weight hints (not calibrated learning).
5. Compare to system `gap.status`; track fail rate over time in LIMITS notes —
   never as a headline accuracy figure.

## Preference / outcome calibration telemetry (W-cal)

**Not a calibration certificate.** `emotions eval calibration` reads an offline
preference JSONL and reports **counts**, **outcome mix**, **hint magnitudes**,
and **coverage** (unique questions, repeat-outcome ids) only. It does **not**
publish an accuracy %, Brier score, or ECE, and it does not apply weight hints.
It does not set a `proof_ready` flag.

| Signal | Meaning |
|--------|---------|
| `counts_by_type` | `event_type` histogram (`prefer`, `reject`, `keep`, `outcome`, …) |
| `outcomes.by_result` | Mix of `labels.result` on `event_type=outcome` (silent if none) |
| `hint_magnitudes` | `l1` / `max_abs` of tiny `learn_profile_weight_hints` deltas |
| `coverage` | Shape counts: unique `question_id`s, how many have an outcome, how many have **repeat** outcomes, distinct result labels, outcomes that carry `score_axes`, ids with a prior score snapshot **and** an outcome |

Weight hints come from labeled prefer/reject **and** from `event_type=outcome`
rows that carry `score_axes` plus a known `labels.result`. Outcome rows are
always counted in `outcomes.by_result` when present. This report does not
call `apply_weight_hints_to_profile` and is **not** a calibration certificate.

### How to run

```bash
emotions eval calibration --json
emotions eval calibration --path prefs.jsonl --profile humanity_default --json
# Optional: fold the same telemetry into the composite report
emotions eval report --path prefs.jsonl --json
pytest tests/test_eval_calibration.py -q
```

Default `--path` is the bundled smoke fixture
`evals/fixtures/preference_calibration_smoke_v1.jsonl` (prefer/reject/keep plus
two outcome breadcrumbs). Replace it with a real labeled log before treating
the numbers as anything other than a wiring check. On that smoke file,
`coverage.n_question_ids_with_repeat_outcome` is **0**.

Honesty field: **not calibrated**. v1 ships the flywheel scaffolding, not
proof that scores track later impact.

### What v1.1-cal / §10 still needs

Coverage counts are **not** the calibration proof. ROADMAP §10 still requires:

1. **Longitudinal dataset** — time-separated score snapshots vs later *real*
   impact follow-up. The bundled smoke JSONL is five synthetic rows, not that
   dataset. Do not invent dated “thin longitudinal” fixtures to look like proof.
2. **Methodology for score-vs-outcome** — a protocol that compares prior scores
   to later outcomes. This command reports counts and magnitudes only and must
   **not** publish accuracy / Brier / ECE until such a dataset exists.
3. **Multi-outcome analysis** — enough labeled results across outcome types to
   inspect mix over time. `outcomes.by_result` is a histogram, not that analysis.

`proof_ready` is intentionally absent: a boolean latch that never flips (or that
flips on synthetic JSONL) is not a proof gate.

## Elicit A/B process eval (not EES)

Lexical investigation-quality rubric on synthetic agent write-ups
(`examples/elicit_ab_protocol.json`, AI + climate sample responses).
`emotions eval elicit` reports condition means and B−A / C−A deltas only.

This is **not** an elicitation league, **not** EES, and **not** proof that
incongruity raises breakthrough rates. Protocol `non_claims` stay in force.

```bash
emotions eval elicit --responses examples/elicit_ab_sample_responses.json --json
emotions eval elicit --responses examples/elicit_ab_sample_responses_climate.json --domain climate --json
pytest tests/test_elicit_redteam_fixtures.py -q
```

## Dual-use red-team regression (not a league)

`evals/fixtures/dual_use_redteam_v1.json` is a small offline corpus for the
weighted heuristic. `expect_risk=low` must stay below review; `review_or_high`
must flag; `residual_may_miss` documents LIMITS evasion (a catch is allowed;
a miss is not a product failure).

**Not** a biosecurity oracle, **not** a continuous F1–F15 league, **not**
dual-use solved.

```bash
pytest tests/test_elicit_redteam_fixtures.py tests/test_wedges_safety_packs.py::test_dual_use_redteam_fixtures -q
```

## Honesty

Scores remain decision aids. Literature is abstract/neighborhood-level unless
full-text adapters are added. LLM gap reader (when used) must cite retrieved
evidence titles only. Neglectedness/cost remain heuristic proxies
(`research/NEGLECTEDNESS_COST.md`).
