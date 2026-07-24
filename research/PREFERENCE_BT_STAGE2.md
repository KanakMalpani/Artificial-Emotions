# Preference stage-2 — Bradley–Terry within profile (research)

**Status:** Deepening [`PREFERENCE_CALIBRATION.md`](PREFERENCE_CALIBRATION.md) for when pairwise volume justifies latent scores.  
**Honesty:** BT/BTL fits **within a named ValueProfile (+ optional domain)**. Global BT across users recreates McNamara/hivemind pressure. Do not ship RLHF-scale reward models for curiosity ranks in v0.x.

*Generated: 2026-07-25*

---

## 1. When stage-2 is justified

| Signal | Threshold (heuristic) |
|--------|------------------------|
| Prefer/reject only | Stay on weight-hint ladder (stage-1) |
| `preferred_over_ids` pairs | ≥ ~30–50 pairs **per profile** before MLE BT is stable |
| Ties / “both useful” | Collect explicitly — see BTT below |
| Multi-annotator | Prefer BT-σ / reliability weighting over pooling |

Until then: keep `learn_profile_weight_hints` + show deltas; do not fit latent question skills.

---

## 2. Literature worth stealing (2024–2026)

| Work | Claim | Transfer |
|------|-------|----------|
| **Swiss InfoGain** ([2511.12796](https://arxiv.org/abs/2511.12796)) | Adaptive Swiss + mutual-info pairing beats random BT pairs under annotation budget | UI: next pairwise duel = max info gain vs random top-n |
| **BTT — BT with ties** ([2410.05328](https://arxiv.org/abs/2410.05328)) | Ignoring ties biases preference *strength* | Schema: `prefer` / `reject` / `tie` / `both_keep` |
| **GenRM** ([2410.12832](https://arxiv.org/abs/2410.12832)) | Zero-shot LLM judges underperform BT RMs in-distribution; GenRM closes gap OOD | If using LLM-as-judge for synthetic prefs, don’t claim human equivalence |
| **Pairwise-RL** ([2504.04950](https://arxiv.org/abs/2504.04950)) | Scalar BT RM calibration is hard across contexts | Prefer keeping **axis weight deltas** over one scalar “science reward” |
| **DFA / fused prefs** ([2508.11363](https://arxiv.org/abs/2508.11363)) | Prefs + rewards under BT recover entropy-regularized policy | Academic only — we are not training a policy |
| **PageRank ↔ BT** ([2402.07811](https://arxiv.org/abs/2402.07811)) | BT scores ≈ scaled PageRanks under quasi-symmetry | Optional citation-network neglectedness cousin — not for user prefs |
| **RLHF statistical survey** ([2604.02507](https://arxiv.org/abs/2604.02507)) | BTL, active design, UQ framing | Use for eval language; not product scope |

---

## 3. Recommended product ladder (sibling)

1. **Collect ties** in PreferenceEvent (`outcome` or new `relation: tie`).  
2. **Active pair picker** (Swiss InfoGain–inspired): propose next duel among top-k ranked unknowns for this profile.  
3. **Offline BT fit script** (research/eval only): emit latent skills + CIs; compare to heuristic ranks (Spearman).  
4. **Never** auto-rewrite `ValueProfile.weights` from BT without user confirm + audit log.  
5. **Never** pool prefs across `public_demo_*` and personal profiles.

---

## 4. Eval hooks

| Metric | Role |
|--------|------|
| Pair coverage / graph connectedness | Is BT identifiable? |
| Spearman(heuristic rank, BT skill) | Divergence is expected and informative |
| Preference strength calibration | With ties vs without (BTT ablation) |
| Hivemind check | BT top-n embedding similarity must not worsen |

---

## 5. Productize next

- Add `tie` / `both_keep` to preference UX + summarize.  
- Optional `suggest_next_pair(profile, top_k)` tool (info-gain heuristic, not full Swiss tournament).  
- Eval notebook: BT MLE only when pair graph is connected enough; else report “insufficient.”

---

## 6. Key citations

| Work | ID |
|------|-----|
| Swiss InfoGain | arXiv 2511.12796 |
| BTT | arXiv 2410.05328 |
| GenRM | arXiv 2410.12832 |
| Pairwise-RL | arXiv 2504.04950 |
| PageRank–BT | arXiv 2402.07811 |
| RLHF stats survey | arXiv 2604.02507 |
| In-repo | `preferences.py`, [`OUTCOME_FLYWHEEL.md`](OUTCOME_FLYWHEEL.md) |
