# AI co-scientist landscape (2025–26 snapshot)

**Status:** Competitor adjacency for [`GAP_VERIFICATION_COMPETITORS.md`](GAP_VERIFICATION_COMPETITORS.md).  
**Honesty:** These systems are **hypothesis / workflow co-pilots** with human-set objectives — not replacements for ValueProfile-ranked unknowns. Snapshot mid-2026.

*Generated: 2026-07-25*

---

## 1. Positioning sentence

| System | Job | Gap vs Artificial Emotions |
|--------|-----|------------------------------|
| **Google Co-Scientist** ([2502.18864](https://arxiv.org/abs/2502.18864); *Nature*) | Multi-agent Gemini; tournament evolution of hypotheses conditioned on **user research objectives** + evidence; biomedical validations | Objectives given; strong on generate/critique; not general VOI-rank of open unknowns |
| **HeurekaBench / sc-HeurekaBench** ([2601.01678](https://arxiv.org/abs/2601.01678); ICLR 2026) | Benchmarks open-ended research Qs grounded in papers+code; critic module helps | Eval framework we can learn from; domain-specific instantiation |
| **MIND** ([2604.13699](https://arxiv.org/abs/2604.13699)) | Materials co-scientist; MLIP in-silico experiments + debate | Closed-loop materials; different wedge |
| **HACO / MaskGXT** ([2606.22866](https://arxiv.org/abs/2606.22866)) | Human–AI co-discovery of algorithms (CSP) | Algorithm search with human steering |
| **Kosmos / Robin** (refs in Bisht) | Autonomous discovery agents | Downstream of problem selection |
| **This repo** | Rank **unanswered** Qs under explicit values + gap verify + provoke | Upstream of co-scientist hypothesis tournaments |

---

## 2. Shared pattern (and our wedge)

Almost every co-scientist paper **conditions on human research objectives**. Bisht et al. argue that’s why they’re co-scientists, not autonomous. Artificial Emotions’s wedge is making **objective/value choice explicit and multi-axis** before (or beside) hypothesis tournaments.

**Integration sketch (sibling, optional):**  
`provoke` / ranked unknowns → paste as Co-Scientist / agent “research objective” pack — we don’t reimplement their tournament.

---

## 3. Productize next (sibling)

1. Docs one-pager: “Curiosity layer vs co-scientist” handoff.  
2. Example inject fragment: “Research objectives (ranked unknowns): …” for external agents.  
3. Watch HeurekaBench methodology for open-ended eval design ([`CURIOSITY_EVAL_METRICS.md`](CURIOSITY_EVAL_METRICS.md)).  
4. Do not claim Nature-validated biomedical discovery.

---

## 4. Key citations

| Work | ID |
|------|-----|
| Co-Scientist | arXiv 2502.18864 |
| HeurekaBench | arXiv 2601.01678 |
| MIND materials | arXiv 2604.13699 |
| HACO | arXiv 2606.22866 |
| Bisht et al. | arXiv 2605.08956 |
