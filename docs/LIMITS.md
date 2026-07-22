# Known Limits (verified)

Honest bounds for v0.1 — do not overclaim.

## Verified working

- Offline seed → score → rank → brief pipeline
- Literature neighborhood fetch via OpenAlex
- Gap gate: related papers ≠ answered (overlap-gated)
- Acceptance gates: answerability, risk, likely-answered
- Near-duplicate suppression (normalized Jaccard)
- CLI, Python API, FastAPI, web UI
- 14+ automated tests including failure-mode cases

## Known limits

| Limit | Why | Mitigation path |
|-------|-----|-----------------|
| Heuristic scoring is lexicon/density based | No LLM required for demos | Set `use_llm=True` + API key |
| Gap verify uses token overlap, not deep reading | OpenAlex abstracts are partial | Add LLM-as-reader or full-text APIs |
| Seed set is curated, not open-ended | Offline reliability | LLM generation expands candidates |
| Value weights are defaults | No universal value-free ranking | Pass custom `ValueProfile` |
| No longitudinal calibration yet | Need outcome data | Log rankings → later impact |
| Embedding diversity not included | Avoid heavy deps in v0.1 | Optional sentence-transformers later |
| Dual-use filter is keyword-level | Easy to evade | Stronger classifier + human review |

## Confidence interpretation

- `~0.25–0.35`: no literature / unknown caveat
- `~0.45–0.58`: heuristic + literature neighborhood
- Higher: requires LLM judges and/or stronger evidence

Scores are **decision aids**, not oracles.
