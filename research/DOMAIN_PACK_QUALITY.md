# Domain pack / seed quality (research addendum)

**Status:** Complements CONTRIBUTING seed bar with failure-mode and hivemind lessons.  
**Honesty:** Curated seeds are **starting distributions**, not exhaustive frontiers.

*Generated: 2026-07-25*

---

## 1. Existing bar (keep)

From CONTRIBUTING: operationalization + why_it_matters; not textbook-solved; dual-use awareness; checklist before PR.

Packs now live under `src/artificial_emotions/packs/` (aging_biology, materials_catalysis, affective_science, …).

---

## 2. Research-driven additions

| Risk | Pack rule |
|------|-----------|
| McNamara / hot-topic only | Mix neglected + high-stakes; avoid LLM-hype-only AI packs |
| Hivemind (similar questions) | ≥1 embedding-dissimilar cluster per pack; no near-paraphrase triples |
| Related≠answered | Prefer questions where related lit exists but settlement is unclear |
| Failure knowledge | Include ≥1 seed about contradictions / null / replication gaps when honest |
| Dual-use | Materials/bio packs: escalate `max_risk` awareness; prefer public_demo for demos |
| Answerability sprawl | One `?` primary; enabling_questions ≤4 |
| Feasibility theater | Don’t claim synthesizability; use operationalization for *measurement plan* |
| Confirmation-only ops | Prefer ops that name a **falsifying / discriminating** observation ([`FALSIFYBENCH.md`](FALSIFYBENCH.md)) |
| Invalid form | Reject multi-`?` sprawl seeds; critique would flag ([`VERITAS_EPISTEMIC_LABELS.md`](VERITAS_EPISTEMIC_LABELS.md)) |

---

## 3. Suggested pack metadata (optional JSON fields)

```json
{
  "pack_id": "materials_catalysis",
  "honesty": "Curated seeds — not exhaustive; not lab-validated",
  "diversity_notes": "Include interfacial / manufacturability unknowns, not only conductivity",
  "dual_use_review": "YYYY-MM-DD"
}
```

---

## 4. Productize next (sibling)

1. Pack linter: duplicate Jaccard; multi-`?` count; missing operationalization.  
2. CONTRIBUTING link to this note + [`HIVEMIND.md`](HIVEMIND.md) / [`PROBLEM_SELECTION_MCNAMARA.md`](PROBLEM_SELECTION_MCNAMARA.md).  
3. Eval: pack-level hivemind similarity of seed questions.  

---

## 5. See also

- CONTRIBUTING.md seed section  
- [`FAILURE_MODES.md`](FAILURE_MODES.md) F4/F6/F9/F10  
- Packs: `src/artificial_emotions/packs/`  
