# Soundness pass — offline / display UX (research)

**Status:** Companion to sibling `soundness.py` and [`INNOEVAL_JUDGES.md`](INNOEVAL_JUDGES.md).  
**Honesty:** Heuristic form+gap check ≠ ScholarEval retrieval-augmented expert rubrics. Labels `pass`/`revise`/`fail` are **triage**, not peer review.

*Generated: 2026-07-25*

---

## 1. What the heuristic covers

| Signal | Role |
|--------|------|
| `critique_brief` issues | Form sprawl, falsifier missing, anthropomorphism |
| Gap status honesty | Avoid treating related lit as settled |
| `feasibility_note` | Display context only |
| Optional hivemind on batch | Homogeneity flag |

**Missing vs ScholarEval/InnoEval:** deep lit retrieval for soundness/contribution dimensions; multi-background review board.

---

## 2. UX

- Badge: **Soundness triage** (not “Peer reviewed”).  
- Footer: “Heuristic — does not change ranks.”  
- `fail` → encourage edit ops; never auto-drop from top-n without user action.  
- Batch report: % pass/revise/fail + hivemind metadata.

---

## 3. Productize next

1. Wire MCP/API/eval report if not already.  
2. Grow toward retrieval-grounded soundness **offline** only.  
3. Keep profile-scoped; no global science judge.  
4. Dual-use: soundness pass must not clear `human_review_risk`.

---

## 4. See also

[`CRITIC_DEBATE_JUDGES.md`](CRITIC_DEBATE_JUDGES.md) · [`FEASIBILITY_NOTE_UX.md`](FEASIBILITY_NOTE_UX.md) · [`CURIOSITY_EVAL_METRICS.md`](CURIOSITY_EVAL_METRICS.md)
