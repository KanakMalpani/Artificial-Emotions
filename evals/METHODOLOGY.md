# Expert-eval / spot-check methodology (W10)

**Purpose:** Measure gap-gate quality offline with labeled fixtures — not to
publish a vanity “accuracy %” for marketing.

## What we measure

| Signal | Meaning |
|--------|---------|
| Case-level status match | Predicted `GapStatus` vs gold label |
| Missed answered (F1) | Gold `likely_answered` but predicted otherwise |
| False unknown rate | Same as above among answered gold cases |

We **do not** collapse these into a single product accuracy claim.

## How to run

```bash
curiosity eval
# or
python -c "from artificial_curiosity.evals import run_spotcheck; print(run_spotcheck().to_dict())"
pytest tests/test_evals.py -q
```

Fixtures live under `evals/fixtures/` (JSON). Each case includes a question,
optional pre-baked literature hits, and a `gold_status`.

## Protocol for human spot-checks (optional)

1. Sample top-10 ranked questions from a real run (offline or lit).
2. Blind: label each as unanswered / partial / likely_answered / unknown.
3. Append labels via preference JSONL (`event_type=already_answered|keep`).
4. Compare to system `gap.status`; track fail rate over time in LIMITS notes —
   never as a headline accuracy figure.

## Honesty

Scores remain decision aids. Literature is abstract/neighborhood-level unless
full-text adapters are added. LLM gap reader (when used) must cite retrieved
evidence titles only.
