# VERITAS-style epistemic verdicts for gap status (research)

**Status:** Competitor / method note for gap verification honesty.  
**Honesty:** VERITAS targets **image-derived clinical hypotheses** with executable stats. Our gap status is literature/metadata-facing. Steal the **label taxonomy**, not the MRI pipeline.

*Generated: 2026-07-25 | Primary: Stoffl et al., VERITAS arXiv [2604.12144](https://arxiv.org/abs/2604.12144)*

---

## 1. What VERITAS adds

VERITAS (Verifiable Epistemic Reasoning for Image-Derived Hypothesis Testing) is a multi-agent clinical co-scientist that:

- Decomposes hypothesis testing into role-specialized phases.
- Emits an **auditable evidence trail** (plan → artifacts → stats → verdict).
- Classifies outcomes as **Supported / Refuted / Underpowered / Invalid** by jointly checking significance, effect direction, and study power.

Reported: ~81% verdict accuracy with frontier models on a 64-hypothesis MRI bank; high rate of independently verifiable statistical outputs. Failures remain diagnosable via artifacts.

**Transfer:** The Underpowered vs Refuted distinction is exactly the honesty gap our product already warns about (“related ≠ answered”; “no hit ≠ settled”).

---

## 2. Mapping to Artificial Curiosity gap status

| VERITAS label | Our gap-status cousin | Product use |
|---------------|----------------------|-------------|
| **Supported** | `answered` / `settled_claim` (rare; needs claim-level verify) | Only after claim verification + human confirm |
| **Refuted** | `falsified` / `contradicted` | Claim-level SciFact-style path |
| **Underpowered** | `open` + `low_evidence` / `thin_lit` | Prefer over silent “answered” when n/power weak |
| **Invalid** | `ill_formed` / F9 sprawl / non-operational | Aligns with `critique_brief` form issues |

Also relevant: **HLER** ([2603.07444](https://arxiv.org/abs/2603.07444)) — dataset-aware hypothesis generation → 87% feasible vs 41% unconstrained. Maps to answerability/feasibility axes + pack quality.

---

## 3. Productize next (sibling)

1. Extend gap-status fixture vocabulary with optional `underpowered` / `invalid_form` (hand labels).  
2. Eval metric: confusion matrix including underpowered (don’t punish “open” when lit is thin).  
3. Keep `critique_brief` as Invalid/form gate — already shipping in sibling `critique.py`.  
4. Do **not** claim VERITAS-level executable verification for arbitrary text unknowns.

---

## 4. Related ecosystem (positioning)

| System | Relation |
|--------|----------|
| Google Co-Scientist | Objective-conditioned tournament — we rank upstream unknowns |
| OmniScientist / ScienceArena | Elo + pairwise voting — cousin to prefs/BT |
| Agentic AutoSurvey | Quality evaluator agent — cousin to form critic |
| Denario sketch ([2606.22859](https://arxiv.org/abs/2606.22859)) | Institutional verification/accountability framing |

Curiosity layer stays **upstream**: rank what to investigate; VERITAS-like stacks run **after** a hypothesis is chosen.

---

## 5. Key citations

| Work | ID |
|------|-----|
| VERITAS | arXiv 2604.12144 |
| HLER | arXiv 2603.07444 |
| OmniScientist | arXiv 2511.16931 |
| In-repo | [`GAP_VERIFY_METHODS.md`](GAP_VERIFY_METHODS.md), [`CRITIC_DEBATE_JUDGES.md`](CRITIC_DEBATE_JUDGES.md) |
