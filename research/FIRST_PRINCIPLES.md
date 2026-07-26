# First Principles: Artificial Emotions

## The Claim

Current AI is optimized for **answering**. The missing layer is **asking** — generating unanswered questions ranked by expected value to humanity (or a stakeholder).

That layer is not “more chat.” It is a decision system over epistemic actions.

## What “Curiosity” Must Compute

Curiosity is not novelty for its own sake. It is the selection of **investigations** that maximally improve future decisions and knowledge under constraints.

Formal skeleton (decision-theoretic):

```
score(q) ≈ E[value of knowing answer(q)] − E[cost of investigating(q)]
         = approximate EVSI / ENBS for q
```

We cannot run full Bayesian VOI for open science. So we estimate proxies that are:

1. **Actionable** — change which investigation someone funds or starts
2. **Falsifiable** — a question can fail gap-check or answerability
3. **Anti-McNamara** — not only what is easy to measure (citations)

## Decomposition Into Necessary Stages

| Stage | Job | Failure if skipped |
|-------|-----|--------------------|
| Frontier map | Locate density of existing work | Reinvent crowded areas |
| Question forge | Propose candidate unknowns | Empty / mode-collapsed set |
| Gap verify | Confirm “unanswered” against literature | Fake unknowns |
| Answerability | Reject ill-posed / metaphysical mush | Un-investigable noise |
| Multi-axis score | Impact × neglectedness × tractability × surprise | Single-metric bias |
| Diversity select | Avoid near-duplicates | Ten paraphrases of one idea |
| Brief | Make the top-N investigable | Pretty lists nobody uses |

## Scoring Axes (Why Each Exists)

1. **Impact** — If answered well, how much does the world (or domain) change?
2. **Neglectedness** — Relative underinvestment vs importance (literature + funding density proxies).
3. **Tractability** — Progress possible with near-term methods / data / instruments.
4. **Surprise (epistemic value)** — Expected belief shift; inspired by Bayesian surprise / AutoDiscovery.
5. **Answerability** — Well-posed enough that an investigation could resolve it.
6. **Risk** — Dual-use / harm potential as a *penalty*, not a virtue signal.

Aggregate (default):

```
curiosity = (I^α · N^β · T^γ · S^δ) · A · (1 − R)
```

with uncertainty from judge disagreement and literature-evidence strength.

## Hard Constraints (Invariants)

- A question that fails gap verification cannot rank in the top tier as “unanswered.”
- A question with answerability below threshold is demoted, never dressed as high curiosity.
- Generator and scorer must use **structured rubrics**; free-form “interestingness” is insufficient.
- Scores are **estimates with confidence**, never oracles.
- Human values / stakeholder weights are explicit inputs — there is no value-free ranking.

## What This System Is Not

- Not an end-to-end AI Scientist (experiments, papers).
- Not a literature Q&A tool (Elicit / Consensus / Crow).
- Not “has anyone done X?” alone (FutureHouse Owl) — gap check is necessary but not sufficient.
- Not citation forecasting alone (MIRAI) — impact ≠ curiosity.

## Evidence From Research (Compressed)

- **HybridQuestion (2025)**: AI aligns with humans on past breakthroughs, diverges on future questions → need hybrid judgment + transparent axes.
- **AutoDiscovery / Bayesian surprise**: Surprisal guides open-ended discovery better than diversity alone.
- **SciMuse**: Idea quality is predictable; zero-shot LLM ranking helps when human labels are scarce.
- **VOI / ISPOR**: Research priority = value of reducing decision uncertainty vs cost.
- **Position papers on AI Scientists**: Problem selection is the unsolved bottleneck (McNamara fallacy, consensus bias).

## Design Implication

Ship a **Curiosity Layer**: generate → verify → score → rank → brief.

Everything else (lab automation, paper writing) can consume its outputs later.
