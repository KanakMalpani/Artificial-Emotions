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

Bundled set: `evals/fixtures/spotcheck_v1.json` (≥6 cases).

## How to run

```bash
curiosity eval
# or
python -c "from artificial_curiosity.evals import run_spotcheck; print(run_spotcheck().to_dict())"
pytest tests/test_mid_horizon.py::test_w10_spotcheck_harness_offline -q
```

## Protocol for human spot-checks (optional)

1. Sample top-10 ranked questions from a real run (offline or lit).
2. Blind: label each as unanswered / partial / likely_answered / unknown.
3. Append labels via preference JSONL (`event_type=already_answered|keep`).
4. Optionally set `preference_rerank_path` for thin profile-scoped re-rank
   (small deltas only — not calibrated learning).
5. Compare to system `gap.status`; track fail rate over time in LIMITS notes —
   never as a headline accuracy figure.

## Honesty

Scores remain decision aids. Literature is abstract/neighborhood-level unless
full-text adapters are added. LLM gap reader (when used) must cite retrieved
evidence titles only. Neglectedness/cost remain heuristic proxies
(`research/NEGLECTEDNESS_COST.md`).
