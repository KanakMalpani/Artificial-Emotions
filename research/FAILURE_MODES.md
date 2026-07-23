# Failure Modes & Mitigations

| ID | Failure | Symptom | Mitigation in this system |
|----|---------|---------|---------------------------|
| F1 | False unknown | Ranks a solved problem | OpenAlex/Semantic Scholar gap verify; `gap_status` gate |
| F2 | Ill-posed question | Unfalsifiable / vague | Answerability scorer + schema requiring operationalization |
| F3 | McNamara fallacy | Optimizes citations only | Multi-axis score; impact ≠ citation forecast |
| F4 | Mode collapse | Same question 10 ways | Embedding/near-dup filter; diversity-aware selection |
| F5 | Self-preference bias | Model loves its own prose | Structured rubrics; optional separate judge model |
| F6 | Trend chasing | Only hot topics | Neglectedness axis; density penalty for crowded clusters |
| F7 | Hallucinated gap | Invents empty literature | Require retrieved paper evidence for gap claims; phrase-level abstract claim/open-gap reading; optional LLM gap reader |
| F8 | Overconfident scores | Fake precision | Confidence from evidence strength; `score_low`/`score_high` uncertainty bands; judge variance when multi-judge |
| F9 | Scope creep | Generates research programs | Schema: one primary unknown + testable operationalization |
| F10 | Dual-use omission | Ignores harm | Risk penalty axis; hard reject above threshold |
| F11 | Stakeholder laundering | Claims universal value | Explicit value profile required |
| F12 | Stale frontier | Misses last year’s answers | Recency-aware literature queries |
| F13 | Paraphrase gaming | Rewording known Qs | Normalize + semantic dedupe before ranking |
| F14 | Cost blindness | Infinite ambition | Tractability + cost proxy in score |
| F15 | Empty domain | No literature API | Graceful degrade to heuristic mode with lower confidence |

## Acceptance Gates Before “Top Question”

A candidate enters the ranked output only if:

1. Schema-valid
2. `answerability >= 0.45`
3. `gap_status` ∈ {unanswered, partially_answered, unknown_with_caveat}
4. Not near-duplicate of a higher-scoring candidate
5. `risk <= 0.85` (else hard reject)

## Monitoring Signals

- Fraction of top-10 that fail human “already answered” spot-check
- Mean pairwise similarity within top-N (should stay moderate)
- Score calibration vs later outcomes (optional longitudinal log)
- Judge disagreement entropy (high = flag for human review)
