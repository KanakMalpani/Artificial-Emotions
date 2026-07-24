# Problem selection & the McNamara fallacy (position paper)

**Status:** Core-thesis reinforcement from Bisht et al., *Agentic AI Scientists Are Not Built For Autonomous Scientific Discovery* (arXiv [2605.08956](https://arxiv.org/abs/2605.08956), May 2026).  
**Honesty:** Position paper + one “hypothesis hivemind” embedding experiment — treat as argument + suggestive evidence, not a large RCT.

*Generated: 2026-07-25 | Source: Academia arxiv_download | Confidence: High on alignment with our FIRST_PRINCIPLES.*

---

## 1. Executive summary

This paper’s central claim matches Artificial Curiosity’s reason to exist: **problem selection ≠ problem solving**, and AI-augmented science drifts toward **measurable, data-rich, consensus** questions (McNamara / quantitative fallacy). Preference optimisation + literature priors create a **hypothesis hivemind** (multi-provider outputs still semantically similar). Recommendations: co-scientist not full autonomy; diversity-preserving post-training; failure/tacit data; preregistration of AI hypotheses; persistent world models / EIG. Our stack (explicit ValueProfile, neglectedness, diversity, dual-use, related≠answered, prefs) is a **practical wedge** against technology-push problem selection — not a solved autonomous scientist.

---

## 2. Four challenges → our mitigations

| Challenge (paper) | Desired | Our product move |
|-------------------|---------|------------------|
| **McNamara problem selection** | Field bottlenecks + significance×tractability×resources | Explicit multi-axis score + ValueProfile; anti-hot-topic neglectedness |
| **Tacit / failure data missing** | Procedures + abandoned paths | Can’t invent lab tacit knowledge; do surface open-gap language; prefs `already_answered` / outcomes |
| **Diversity compression (RLHF/DPO)** | Depart from consensus when warranted | `diversity.py`; boredom_guard; interdisciplinary boost; refuse global pref collapse |
| **Bad benchmarks / no physical loop** | Multi-step investigation + experiment feedback | Elicit rubrics; BoxingGym humility; no claim of closed-loop science |

Empirical cite they use: Hao et al. 2026 — AI-augmented scientists publish/cite more but **shrink topic volume** and scientist engagement — quantitative acceleration ≠ broader questions.

---

## 3. Hypothesis hivemind → ensemble caution

Inter-provider cosine similarity stays high on **open-ended** hypothesis generation (NeurIPS AI4Mat papers).  
**Implication:** HybridQuestion-style multi-LLM voting may amplify consensus, not diversity. Prefer **disagreement entropy** and human/ValueProfile overrides over “majority of six models.”

---

## 4. Their forward path vs ours

| Their recommendation | Our honest scope |
|----------------------|------------------|
| Public reviews/proposals as training for scientific judgment | Future data; not ours to scrape without consent |
| Centralized preregistration of AI hypotheses | Optional export schema later; don’t claim registry |
| Simulators as verifiers | Domain adapters only |
| Persistent world models + EIG experiment selection | Moonshot ([`VOI_APPROXIMATIONS.md`](VOI_APPROXIMATIONS.md), [`BAYESIAN_SURPRISE.md`](BAYESIAN_SURPRISE.md)) |
| Demand-pull over technology-push | **Profiles + user domains** are demand-pull entry points |

---

## 5. Productize next (sibling)

1. **LIMITS / README one-liner:** We rank unknowns under declared values because AI Scientist stacks inherit McNamara bias — cite 2605.08956.  
2. **Diversity report** in eval: pairwise embedding similarity of top-n (hivemind detector).  
3. **Do not** market multi-model generate as “more creative” without diversity metrics.  
4. Prefs: reward prefer events that increase neglectedness/surprise vs modal LLM picks.  
5. Keep co-scientist framing in `/v1/agent` copy.

---

## 6. Key citation

Bisht, Kumar, Jablonka, et al. (2026). *Agentic AI Scientists Are Not Built For Autonomous Scientific Discovery.* arXiv:2605.08956.
