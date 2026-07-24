# Failure knowledge & publication bias → curiosity signals

**Status:** Short spike complementing [`PROBLEM_SELECTION_MCNAMARA.md`](PROBLEM_SELECTION_MCNAMARA.md).  
**Honesty:** We cannot recover unpublished failed experiments from OpenAlex. We can prefer questions that **name** unresolved/negative-evidence gaps and avoid treating “many positive papers nearby” as answered.

*Generated: 2026-07-25*

---

## 1. Why it matters

Publication filters favor conclusions over process and positives over negatives (Fanelli; Bisht et al.). Models trained on that corpus miss **when to abandon** a hypothesis. Raccuglia et al. (*Nature* 2016, “dark reactions”) famously showed ML on failed hydrothermal reactions beat literature-only models for predicting synthesis success — failure data is scientifically valuable and systematically missing.

Hao, Xu, Li & Evans (*Nature* 2026): AI tools expand individual scientists’ impact but **contract science’s collective focus** — accelerates measurable topics; shrinks topic volume. Directly motivates neglectedness + diversity in ranking.

---

## 2. Product signals (honest)

| Signal | Do | Don’t |
|--------|----|-------|
| Open-gap lexicon in abstracts | Already in `verify.py` `_OPEN_GAP` | Treat absence of open-gap words as answered |
| Pref event `already_answered` | Train verify eval | Assume user is always right |
| Prefer questions citing contradictions / null results | Seed templates | Fake “failed experiment” databases |
| Diversity / anti-hivemind | Embedding similarity of top-n | Multi-LLM vote alone |

Optional future: ingest **negative-result registries** / preregistration dumps as adapters — not core.

---

## 3. Productize next (sibling)

1. Expand `_OPEN_GAP` carefully with measured FP/FN on fixtures.  
2. Seed pack phrases: “despite null findings…”, “failed to replicate…” as curiosity targets.  
3. Cite Hao *Nature* 2026 in LIMITS for topic-contraction risk.  
4. Do not claim access to dark-reaction-scale failure corpora.

---

## 4. Key citations

| Work | ID |
|------|-----|
| Bisht et al. (failure/tacit sections) | arXiv 2605.08956 |
| Hao et al., AI expands impact / contracts focus | *Nature* 2026 DOI 10.1038/s41586-025-09922-y |
| Artificial Hivemind | arXiv 2510.22954 |
| Shi et al., pos/neg clinical extraction | arXiv 2212.03464 |
| Raccuglia et al., dark reactions | *Nature* 2016 (cited in Bisht) |
