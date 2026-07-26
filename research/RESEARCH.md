# Research Report: Artificial Emotions Layer
*Generated: 2026-07-23 | Sources: 20+ | Confidence: High on gap diagnosis; Medium on long-term eval*

## Executive Summary

AI systems today excel at **answering** and increasingly at **executing** research workflows (AI Scientist, Robin, FutureHouse agents). They remain weak at the upstream act that directs all of that work: **selecting which unanswered questions are most worth asking**. Academic systems (HybridQuestion, SciMuse, AutoDiscovery, Idea-Catalyst, MIRAI) attack pieces of this problem — idea generation, surprise-driven search, interest prediction, impact forecasting — but no widely deployed product is a dedicated **curiosity layer** that generates unknowns, verifies gaps, and ranks by expected investigation value. That is the product thesis of this repository.

## 1. The Capability Gap

| System class | Examples | Strength | Missing |
|--------------|----------|----------|---------|
| Literature QA | Elicit, Consensus | Evidence for a given question | Does not choose the question |
| Gap sniffers | FutureHouse Owl (“Has anyone done X?”) | Existence check | Not ranked by value |
| Idea generators | SciMuse, AI Scientist ideation | Novelty / interest | Weak VOI + gap gates |
| End-to-end scientists | Sakana AI Scientist, Robin | Experiment loops | Problem selection still thin |
| Surprise search | AutoDiscovery | Bayesian surprise | Domain-limited; not general ranking UX |

HybridQuestion (2025) shows AI aligns with humans on **past** breakthroughs but **diverges** on prospective questions — exactly where curiosity judgment is hardest and most valuable.

## 2. Theoretical Anchors

1. **Value of Information (ISPOR VOI)** — Research worth ≈ reduction in expected cost of decision uncertainty minus investigation cost (EVPI / EVPPI / EVSI / ENBS).
2. **ITN-style prioritization** — Importance × Tractability × Neglectedness as practical proxies when full VOI is intractable.
3. **Bayesian surprise (Itti & Baldi; AutoDiscovery)** — Prefer hypotheses that shift beliefs; diversity alone fails in huge spaces.
4. **Intrinsic curiosity (Pathak, Oudeyer)** — RL curiosity is prediction-error driven; scientific curiosity needs *value-laden* prediction error, not pixel novelty.
5. **McNamara fallacy warning** — Optimizing only what is measurable (citations) warps science; multi-axis scores + human value profiles are mandatory.

## 3. Empirical Signals Worth Building On

- **SciMuse**: 100+ group leaders ranked 4,400+ ideas; interest is partially predictable; zero-shot LLM ranking helps when labels are scarce.
- **AutoDiscovery**: Surprisal + MCTS beats diversity heuristics; ~2/3 of LLM-surprising finds surprised humans too.
- **MIRAI**: Title/abstract → impact prediction usable for ideation bias toward impact — necessary but insufficient alone.
- **Idea-Catalyst**: Decompose domain → unresolved challenges → cross-domain insights → rank by impact potential.
- **Position paper (2026)**: Agentic AI scientists are not yet built for autonomous discovery; problem selection remains the bottleneck.

## 4. Product Implications Encoded Here

1. Pipeline, not chatbot: generate → verify → score → diversify → brief.
2. Explicit `ValueProfile` (no pretending neutrality).
3. Literature gap gate (OpenAlex) so “unanswered” is evidence-bearing.
4. Multi-axis score with weak-link geometry (low tractability collapses score).
5. Failure catalog with acceptance gates (`research/FAILURE_MODES.md`).
6. Offline path so demos work without API keys; LLM path for quality uplift.

## 5. Open Research Questions (Meta-curiosity)

1. How to calibrate curiosity scores against later scientific outcomes (citations, patents, policy change) without McNamara collapse?
2. Can ensemble generators + separate judges beat single-model self-preference?
3. What human-in-the-loop protocol minimizes expert time while fixing prospective-question divergence (HybridQuestion)?
4. How to represent interdisciplinary neglectedness beyond co-occurrence graphs?

## Sources (selected)

- HybridQuestion — https://arxiv.org/html/2602.03849
- SciMuse — https://arxiv.org/html/2405.17044v3
- AutoDiscovery (NeurIPS 2025) — Bayesian surprise for open-ended ASD
- MIRAI — https://arxiv.org/html/2606.05443
- Idea-Catalyst — https://www.arxiv.org/pdf/2603.12226
- Sakana AI Scientist — https://sakana.ai/ai-scientist-nature/
- FutureHouse platform / Owl / Robin — https://www.futurehouse.org/
- ISPOR VOI Task Force reports — value of information for research prioritization
- Elicit / Consensus / ResearchRabbit — answer/search products (contrast class)

## Methodology

Multi-source web + arXiv search (Exa, Academia MCP). Sub-questions: (1) existing curiosity/prioritization systems, (2) VOI theory, (3) commercial contrast, (4) failure modes of AI scientists, (5) scoring proxies that survive contact with experts.
