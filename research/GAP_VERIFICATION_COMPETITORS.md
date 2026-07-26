# Gap verification & scientific question-ranking competitors

**Status:** Competitive / literature spike — durable map of what “gap” and “rank” mean elsewhere vs this repo.  
**Honesty:** Landscape moves fast; treat as 2026-07 snapshot. We do **not** claim uniqueness of idea generation; we claim a specific **gap-verify → multi-axis value-rank → provoke** stack with explicit `ValueProfile`.

*Generated: 2026-07-25 | Sources: arXiv/Academia + Exa | Confidence: High on published systems; Medium on clawRxiv/skill repos (lighter peer review).*

---

## 1. Executive summary

Most “AI for science” tools **answer questions**, **synthesize literature**, or **generate ideas**. Fewer **verify unansweredness** against literature with an explicit related≠answered gate, then **rank unknowns under declared values**. Closest neighbors: SciMuse (interest ranking of ideas), ScholarEval (idea evaluation grounded in lit), LitGapFinder-style concept co-occurrence gaps, ResearchAgent/IdeaSynth (ideation loops). Differentiation for Artificial Emotions: **VOI-style axes + ValueProfile + dual-use/risk + MCP/HTTP provoke**, not end-to-end paper writing.

---

## 2. Competitor / neighbor matrix

| System | What it optimizes | Gap / verify? | Ranking object | vs Artificial Emotions |
|--------|-------------------|---------------|----------------|-------------------------|
| **Elicit / Consensus** | Answers & evidence for a *given* Q | Evidence retrieval | Answer quality | Opposite job: they close gaps; we surface them |
| **ResearchRabbit / Connected Papers** | Citation graph exploration | No | Relatedness | Discovery UX, not value-rank of unknowns |
| **FutureHouse Owl** | Existence / literature check | Strong existence | Binary-ish | Subset of our verify; we add value ranking |
| **Ai2 Scholar QA** ([2504.10861](https://arxiv.org/abs/2504.10861)) | Literature QA with attribution | N/A (answering) | Answer organization | Contrast class |
| **SciMuse** ([2405.17044](https://arxiv.org/abs/2405.17044)) | Personalized *interesting* ideas from KG+LLM | Weak (generation from concepts) | Expert interest (4k+ ratings; NN/LLM rank) | Interest ≠ VOI/ITN; no ValueProfile; huge human eval we lack |
| **ResearchAgent** ([2404.07738](https://arxiv.org/abs/2404.07738); NAACL 2025) | Novel problems + methods + experiments | Lit graph + review agents | Novelty/clarity/validity via LLM reviewers | Downstream ideation; weak explicit unanswered gate |
| **IdeaSynth** ([2410.04025](https://arxiv.org/abs/2410.04025)) | Iterative facet refinement | Literature-grounded feedback | Human canvas exploration | HCI ideation aid; not batch VOI rank |
| **ScholarEval** ([2510.16234](https://arxiv.org/abs/2510.16234)) | Soundness + contribution of *ideas* | Retrieval-augmented eval | Rubric coverage vs experts | Eval layer we can **learn from**; not our generate→verify pipeline |
| **IdeaBench / AI Idea Bench 2025** | Benchmark idea generation | Grounding varies | Novelty/feasibility metrics | Use for eval inspiration; not products |
| **LDC** ([2412.14626](https://arxiv.org/abs/2412.14626)) | Controllable novelty/feasibility/effectiveness | Paper→follow-up pairs | Multi-dim RL | Ranking dimensions overlap ours loosely |
| **LitGapFinder** (clawRxiv 2603.00233+) | Concept pairs high sim × low co-occurrence | Graph gap score | Hypotheses from gaps | Closest *gap math*; often no human ValueProfile; related≠answered weaker |
| **Research Gap Finder skills** (e.g. GitHub agent skills) | Method/theory/application gaps | LLM taxonomy | Innovation/feasibility/impact 1–5 | Heuristic; quality bar varies |
| **HybridQuestion** (in SOURCES) | Future questions AI vs human | Divergence | Future-oriented Qs | Complementary research signal |
| **Sakana AI Scientist** | End-to-end papers | Weak upstream priority | Pipeline success | Moonshot contrast; prioritization thin |
| **MIRAI / Idea-Catalyst / ResearchBench** | Impact / unresolved / rank decompositions | Partial | Various | Cite in RESEARCH.md; watch for merge ideas |

---

## 3. How “gap” is operationalized elsewhere

### 3.1 Concept co-occurrence gaps (LitGapFinder family)

\[
\mathrm{GapScore}(c_j,c_k) = \mathrm{sim}(c_j,c_k)\cdot\frac{1}{1+w(c_j,c_k)}
\]

High semantic similarity + low empirical co-occurrence ⇒ “underexplored link.” Validation claim (LitGapFinder): ~60% top-10 hypotheses hit papers published after cutoff (treat as **optimistic / lightly reviewed** until reproduced).

**Risks:** Synonym inflation; trendy embeddings; “gap” that is actually answered under different vocabulary; no dual-use filter; no stakes/ITN.

**Borrow carefully:** Density / co-occurrence as a **neglectedness neighbor signal** (see [`NEGLECTEDNESS_COST.md`](NEGLECTEDNESS_COST.md)) — not as sole truth of unansweredness.

### 3.2 Existence check (Owl-class)

“Does literature already answer Q?” — necessary, not sufficient for ranking. Our `verify.py` stance: **related neighborhood ≠ answered**; overlap-gated claims; grounded LLM reader that must not invent titles.

### 3.3 Idea evaluation (ScholarEval)

Two axes: **soundness** (methods vs prior lit) and **contribution** (advancement dimensions). Expert-annotated ScholarIdeas (117 ideas, 4 disciplines). Useful as **downstream judge** pattern for our eval harness (W10), not as replacement for gap status.

### 3.4 Interest prediction (SciMuse)

Supervised nets on KG features + zero-shot LLM ELO tournaments predict expert interest (AUC ~0.64–0.67 range in paper; public benchmark leaderboard on GitHub). **Interest ≠ decision-theoretic VOI.** We should not chase SciMuse AUC as the north star unless a profile literally says “maximize PIs’ interest.”

---

## 4. Differentiation checklist (keep honest)

| Capability | Ship status (this repo) | Competitor pressure |
|------------|-------------------------|---------------------|
| Generate candidate unknowns | Yes | Commodity (every LLM) |
| Literature gap verify + related≠answered | Yes (core) | Owl / Scholar QA adjacent; still a wedge |
| Multi-axis score + uncertainty bands | Yes | Idea benches score novelty/feasibility; we add neglectedness/surprise/risk |
| Explicit ValueProfile | Yes | Rare in open tools |
| Diversify / anti-mode-collapse | Yes | Often weak |
| Dual-use / human_review_risk | Yes (heuristic) | Rare in ideation toys |
| Provoke / MCP inject | Yes | Agent skills rising (LitGapFinder-as-skill) — **distribution** competition |
| Preference learning flywheel | Schema only | Future |
| Calibrated VOI / EVSI | Moonshot | Nobody credible at consumer scale |

**Positioning sentence (safe):**  
*Artificial Emotions ranks valuable unanswered questions under an explicit value profile, with literature gap checks that refuse to equate related work with answered questions — unlike answer engines, idea chatbots, or interest-only generators.*

---

## 5. Productize next (sibling)

1. **Competitor fixture in evals** — 10 seed questions with hand labels: answered / partial / unanswered; compare our verify vs “naive related-hit ⇒ answered.”
2. **Document Owl-class handoff** — `docs/` one-pager: when to use existence-only tools vs our rank pipeline (light touch if sibling prefers).
3. **Optional neglectedness experiment** — log neighborhood hit density alongside score (already partly in lit cache); compare to LitGapFinder-style sim×(1/(1+w)) as *research* metric only.
4. **ScholarEval-inspired rubric fields** — optional judge dimensions `soundness_vs_lit` / `contribution_claim` in multi-judge (W15) — labels only, not new product name.
5. **MCP skill packaging** — ensure `docs/PLUGINS.md` contrast vs one-shot “gap finder” skills: we expose profiles + limits resources.

---

## 6. Watch list (do not overclaim)

- SciMuse benchmark private rankings — can’t train on them; can only compare methodology.
- clawRxiv LitGapFinder — agent-native distribution may outpace academic packaging; quality bar unclear.
- Preference-manipulation attacks on MCP tool descriptions (see [`AGENT_PLUGIN_UX.md`](AGENT_PLUGIN_UX.md)) — curiosity servers must not SEO their own tool text.

---

## 7. Key citations

| Work | ID |
|------|-----|
| SciMuse | arXiv 2405.17044 |
| ResearchAgent | arXiv 2404.07738 |
| IdeaSynth | arXiv 2410.04025 |
| ScholarEval | arXiv 2510.16234 |
| IdeaBench | arXiv 2411.02429 |
| AI Idea Bench 2025 | arXiv 2504.14191 |
| LDC | arXiv 2412.14626 |
| Ai2 Scholar QA | arXiv 2504.10861 |
| LitGapFinder | clawRxiv 2603.00233 (and v1.1/v1.2) |
| FutureHouse | https://www.futurehouse.org/ |
