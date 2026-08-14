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
preference JSONL and reports **counts**, **outcome mix**, and **hint magnitudes**
only. It does **not** publish an accuracy %, Brier score, or ECE, and it does
not apply weight hints.

| Signal | Meaning |
|--------|---------|
| `counts_by_type` | `event_type` histogram (`prefer`, `reject`, `keep`, `outcome`, …) |
| `outcomes.by_result` | Mix of `labels.result` on `event_type=outcome` (silent if none) |
| `hint_magnitudes` | `l1` / `max_abs` of tiny `learn_profile_weight_hints` deltas |

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
the numbers as anything other than a wiring check.

Honesty field: **not calibrated**. v1 ships the flywheel scaffolding, not
proof that scores track later impact.

## Honesty

Scores remain decision aids. Literature is abstract/neighborhood-level unless
full-text adapters are added. LLM gap reader (when used) must cite retrieved
evidence titles only. Neglectedness/cost remain heuristic proxies
(`research/NEGLECTEDNESS_COST.md`).
