# Imprecise / multicenter VOI — addendum (research)

**Status:** Addendum to [`VOI_APPROXIMATIONS.md`](VOI_APPROXIMATIONS.md).  
**Honesty:** Still **no** product EVSI. These papers sharpen when ValueProfile disagreement and cluster heterogeneity matter.

*Generated: 2026-07-25*

---

## 1. Credal / imprecise VOI (Iskandar 2026)

**Value of Information under Imprecise Probabilities** (arXiv [2607.06570](https://arxiv.org/abs/2607.06570)):

- Classical VOI assumes **one** probability measure.
- When evidence only pins a **credal set**, two objects diverge:
  1. **Rule-specific VOI** — value of info for a fixed imprecise decision rule (e.g. Gamma-maximin).
  2. **Fixed-measure envelope** — classical VOI evaluated over all admissible precise measures.
- EVPI is concave over the credal set; endpoints behave differently for lower vs upper envelopes.
- Gamma-maximin value can **exceed** the entire envelope — rule choice is not recoverable from envelope ends alone.

**Transfer to Artificial Curiosity:**

| Concept | Product analogue |
|---------|------------------|
| Credal set of beliefs | Stakeholder / profile disagreement over importance |
| Rule-specific VOI | “What would a veto-stack / maximin profile do?” |
| Envelope | `compare_profiles` showing range of ranks across profiles |
| Fake consensus average | Explicitly discouraged (see [`CONSTITUTIONAL_CURIOSITY.md`](CONSTITUTIONAL_CURIOSITY.md)) |

Worksheet honesty line: if utilities/probabilities are contested, report **envelope across profiles**, not one EVSI number.

---

## 2. Multicenter EVPI for validation (Wynants et al. 2026)

**VOI for external validation in multicenter studies** (arXiv [2607.02321](https://arxiv.org/abs/2607.02321)):

- Extends EVPI/EVPPI when Net Benefit has **between-center heterogeneity**.
- Distinguishes global vs local optimal strategy; observed vs unobserved clusters.
- ADNEX ovarian-cancer example: global EVPI can be ~0 while local/cluster EVPI remains informative.

**Transfer:** Domain packs / labs are “clusters.” A question high-value for one lab profile may be low for another — same as profile compare, not a bug.

---

## 3. Productize next

1. Sibling `fill_voi_worksheet` (in flight) — keep honesty string; optionally attach `profile_name` + `compare_profiles` snapshot IDs.  
2. Worksheet field: `credal_note` = “utilities contested across profiles; see compare.”  
3. Still never emit `scores.evsi`.

---

## 4. Key citations

| Work | ID |
|------|-----|
| Imprecise VOI / credal | arXiv 2607.06570 |
| Multicenter validation EVPI | arXiv 2607.02321 |
| VOIMCP (POMDP planning) | arXiv 2604.01434 — planning VOI, not science EVSI |
| In-repo | `voi.py`, `examples/voi_worksheet_template.json` |
