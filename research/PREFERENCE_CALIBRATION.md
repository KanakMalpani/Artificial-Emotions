# Preference feedback → profile calibration (research)

**Status:** Flywheel research for HANDOFF item *Preference learning / longitudinal calibration* (schema + thin hints already in product).  
**Honesty:** Pairwise prefs calibrate **within a named ValueProfile**, not a universal science oracle. LLM-as-judge prefs are noisy; treat as weak labels.

*Generated: 2026-07-25 | Sources: Academia + Exa | Confidence: High on LTR/BT methods; Medium on sample sizes needed for science unknowns.*

---

## 1. Executive summary

The product already logs `PreferenceEvent` JSONL and can suggest **tiny weight deltas** from prefer/reject events with score axes (`preferences.py`). Literature says: (1) expert rankings diverge from text-similarity (Lingeman & Yu); (2) Bradley–Terry / Plackett–Luce are the right *objects* for pairwise ranks, with modern fixes for multi-judge reliability (BT-σ) and nonparametric ranking (DMLRank); (3) online preference learning can **collapse feature diversity** unless preferences are preserved (PFP). For Artificial Curiosity, ship **profile-scoped** learning only; collect pairwise `preferred_over_ids`; delay full BT fitting until n is non-trivial; never overwrite ValueProfile without showing deltas.

---

## 2. What already ships (do not redo)

| Piece | Role |
|-------|------|
| `PreferenceEvent` schema | prefer / reject / already_answered / keep / outcome / note |
| JSONL append/read | No DB required |
| `score_axes` on events | Enables weight hints |
| `learn_profile_weight_hints` | Small deltas on impact/neglectedness/tractability/surprise **within** profile |
| Honesty string | Explicit non-oracle disclaimer |

Research implication: next wedges are **collection UX + pairwise structure + eval**, not a new learning framework from scratch.

**Stage-2 deep dive:** [`PREFERENCE_BT_STAGE2.md`](PREFERENCE_BT_STAGE2.md) (ties, Swiss InfoGain pairing, offline BT only).

---

## 3. Relevant literature (mapped)

### 3.1 Learning to rank scientific relatedness

**Lingeman & Yu** (arXiv [1611.01400](https://arxiv.org/abs/1611.01400)): crowd/expert rankings of related articles ≠ text similarity; SVM-Rank beats similarity baselines.  
→ Our users’ prefer/reject on *unknowns* will also diverge from embedding similarity — good reason not to collapse to “most similar gap.”

### 3.2 Pairwise models for ranking

| Approach | Use here |
|----------|----------|
| Bradley–Terry / BTL | Fit latent skills for questions *within a profile+domain* once enough pairs exist |
| Plackett–Luce | If UI collects full list rankings of top-k |
| BT-σ (LLM-as-a-jury) | When multi-judge models disagree — learn judge reliability without human labels on judges ([2602.16610](https://arxiv.org/html/2602.16610v2)) |
| DMLRank / GARS | Nonparametric ranking + CIs from prefs ([2601.21816](https://arxiv.org/html/2601.21816v2)) — overkill until data volume exists |
| SciMuse interest ELO | Pairwise LLM tournaments for interest — cousin to our multi-judge path |

### 3.3 Online preference pitfalls

**PFP — Preference Feature Preservation** (arXiv [2506.11098](https://arxiv.org/abs/2506.11098)): online preference learning biases toward majority features across iterations.  
→ Keep **profile isolation**; don’t pool all users into one global ranker; store axis snapshots so minority axes (e.g. neglectedness) don’t get erased.

**Unbiased LTR** (Ai et al. [2004.13574](https://arxiv.org/abs/2004.13574)): position bias in UI clicks.  
→ Prefer explicit prefer/reject buttons over inferring from dwell; if web UI ranks vertically, log position.

### 3.4 ScholarEval / expert rubrics

Human expert idea reviews (ScholarIdeas) show what “good labels” look like: soundness + contribution dimensions. Our events can optionally carry `labels` for those dimensions without claiming ScholarEval parity.

---

## 4. Recommended learning ladder

| Stage | Data needed | Method | Product action |
|-------|-------------|--------|----------------|
| **0 (now)** | Sparse events | Weight hints from axis means of preferred vs rejected | Keep; surface in CLI/API |
| **1** | ≥20–50 pairwise within profile | Simple win-rate / Borda on question_ids | `curiosity prefs summarize` |
| **2** | ≥100 pairs / profile | BT skills + uncertainty; optional BT-σ if multi-judge | Research → optional module |
| **3** | Longitudinal outcomes | Correlate prefer with later `outcome` / `already_answered` | Calibration report (v2 bar) |
| **Never** | — | Global model replacing ValueProfile | Violates FIRST_PRINCIPLES |

---

## 5. Collection schema nudges (research → sibling)

Encourage (without breaking v1 schema):

```json
{
  "event_type": "prefer",
  "question_id": "q_a",
  "preferred_over_ids": ["q_b"],
  "profile_name": "alignment_lab",
  "domain": "ai",
  "score_axes": {"impact": 0.7, "neglectedness": 0.6, "tractability": 0.4, "surprise": 0.8},
  "labels": {"reason": "higher_neglectedness"}
}
```

- Always set `preferred_over_ids` when possible (pairwise > unary prefer).  
- Snapshot `score_axes` at feedback time (already supported).  
- Use `already_answered` as hard negative for verify eval (F1).

---

## 6. Productize next (sibling)

1. **CLI/API: `prefs summarize`** — counts by event_type; top preferred ids; show weight hints + honesty.  
2. **Web: explicit Prefer / Reject / Already answered** on ranked cards (log position).  
3. **Eval harness hook** — replay JSONL → measure rank correlation vs held-out human order (even n=10).  
4. **Guardrails** — refuse to apply hints that drive any weight to 0 or flip profile intent; clamp deltas.  
5. **Do not** train a global LTR on pooled profiles; do not claim BT skills without CIs.

---

## 7. Open risks

- Cold start: hints unstable — require min_n events.  
- Strategic feedback / preference hacking of dual-use ranks.  
- LLM jury disagreement entropy (W15) vs human prefs — keep separate channels in metadata.  
- Privacy: preference JSONL may contain sensitive question text — local-first, no cloud upload by default.

---

## 8. Key citations

| Work | ID |
|------|-----|
| Lingeman & Yu, LTR scientific docs | arXiv 1611.01400 |
| Ai et al., unbiased LTR survey | arXiv 2004.13574 |
| PFP online preference bias | arXiv 2506.11098 |
| BT-σ LLM-as-a-jury | arXiv 2602.16610 |
| DMLRank nonparametric prefs | arXiv 2601.21816 |
| SciMuse interest ranking | arXiv 2405.17044 |
| ScholarEval | arXiv 2510.16234 |
| In-repo | `preferences.py`, HANDOFF preference flywheel |
