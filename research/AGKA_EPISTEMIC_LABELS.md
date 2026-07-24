# AGKA — annotation-guideline knowledge for epistemic labels (research)

**Status:** Thin note for catalog / cue vocabulary authoring.  
**Honesty:** AGKA improves LLM **classification of educational text** including epistemic emotion labels — not user ERS and not our mix API.

*Generated: 2026-07-25 | Paper: Liu et al. arXiv [2406.00954](https://arxiv.org/abs/2406.00954) (IEEE TLT 2025)*

---

## 1. Finding

Annotation Guidelines-based Knowledge Augmentation (AGKA): retrieve label definitions from guidelines → few-shot LLM classify. Helps GPT-4 / Llama 3 70B on learning-engagement tasks including **epistemic emotion** classification. Struggle: similar label names in multi-class.

---

## 2. Transfer

| AGKA lesson | Our product |
|-------------|-------------|
| Clear label definitions matter | Keep cue catalog disclaimers precise |
| Similar names confuse classifiers | Don’t blur curiosity vs interest in scoring axes |
| Guidelines as knowledge | `list_epistemic_cues` + docs are the guideline surface |
| Not for inference of user affect | Still `annotation_only` |

Persuasion link remains: epistemic emotion predicts belief change ([2511.22109](https://arxiv.org/abs/2511.22109)) — [`AFFECTIVE_SAFETY.md`](AFFECTIVE_SAFETY.md).

---

## 3. Productize next

1. Ensure each cue tag has a one-line definition in API list (if any thin).  
2. Docs: curiosity ≠ interest for ranking weights.  
3. No epistemic-emotion classifier on user text.

---

## 4. See also

[`EPISTEMIC_ELICITATION.md`](EPISTEMIC_ELICITATION.md) · [`EMOTION_ACCESS.md`](EMOTION_ACCESS.md) · [`CUE_THRESHOLD_KNOBS.md`](CUE_THRESHOLD_KNOBS.md)
