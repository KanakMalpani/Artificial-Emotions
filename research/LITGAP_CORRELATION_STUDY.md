# LitGapFinder-style co-occurrence vs neglectedness — offline study design

**Status:** Offline research protocol only (P2). Do **not** replace gap verify or ValueProfile ranking with co-occurrence GapScore.  
**Honesty:** LitGapFinder-family claims (~60% top-10 hypotheses later published) are lightly reviewed until reproduced. Synonym/vocab mismatch can fake “gaps.”

*Generated: 2026-07-25 | Background: [`GAP_VERIFICATION_COMPETITORS.md`](GAP_VERIFICATION_COMPETITORS.md) §3.1*

---

## 1. Goal

Measure **correlation** (Spearman/Pearson) between:

| Signal A | Signal B |
|----------|----------|
| Concept-pair GapScore \(=\mathrm{sim}\cdot 1/(1+w)\) | Our `scores.neglectedness` on ranked unknowns |
| GapScore | OpenAlex hit sparsity / funder thinness ([`FUNDING_NEGLECT_SIGNALS.md`](FUNDING_NEGLECT_SIGNALS.md)) |
| GapScore | Human gap-status labels (`unanswered` vs `answered`) |

Hypothesis (weak): GapScore correlates **modestly** with neglectedness proxies and **poorly** with “truly unanswered” after related≠answered verify — useful as an **optional rationale key**, not a scorer replacement.

---

## 2. Dataset construction (offline)

1. Pick 1–2 domains with packs (e.g. climate + AI safety).  
2. Extract concept vocabulary from pack seeds + OpenAlex topics (cap N concepts).  
3. Build co-occurrence counts \(w(c_j,c_k)\) from abstracts in a **time-sliced** corpus (train ≤ T_cut).  
4. Embedding sim from a fixed model (record id + date).  
5. Sample top-M GapScore pairs → render as candidate “unknowns” (template: “How does \(c_j\) relate to \(c_k\) when …?”).  
6. Run **our** pipeline: verify + score under fixed `ValueProfile`.  
7. Hand-label subset (n≥50) for gap status using VERITAS-aware labels ([`VERITAS_EPISTEMIC_LABELS.md`](VERITAS_EPISTEMIC_LABELS.md)).

Holdout: papers after T_cut for optional “later published?” check (LitGapFinder-style) — report carefully; publication ≠ high VOI.

---

## 3. Analyses

| Analysis | Method | Success criterion |
|----------|--------|-------------------|
| Rank correlation | Spearman(GapScore, neglectedness) | Report ρ + CI; expect |\ρ| < 0.5 if signals differ |
| Classification | AUROC GapScore → unanswered label | Compare to OpenAlex hit-count baseline |
| Ablation | sim-only vs 1/(1+w) only vs product | Which term drives agreement |
| Failure cases | Manual: synonym gaps, answered-under-other-vocab | Qualitative appendix |
| Hivemind | Mean pairwise cosine of GapScore-derived questions | [`HIVEMIND_METRIC_SPEC.md`](HIVEMIND_METRIC_SPEC.md) |

---

## 4. What sibling may productize *after* study

| If finding… | Product move |
|-------------|--------------|
| Weak correlation | Keep GapScore out of core scorer; optional debug export |
| Moderate + interpretable | Add `rationale.cooccur_gap` key (display only; no silent weight) |
| High false “unanswered” | Reinforce related≠answered gate; never auto-promote GapScore |

Same pattern as OpenAlex funder keys: **rationale only**.

---

## 5. Non-goals

- Shipping LitGapFinder as default generate path.  
- Claiming co-occurrence = ITN neglectedness.  
- Running this in CI (too heavy / network).

---

## 6. Key citations

| Work | Role |
|------|------|
| LitGapFinder family (clawRxiv 2603.00233+) | GapScore formula inspiration |
| In-repo competitors note | Positioning |
| OpenAlex neglect signals | Comparison baseline |
