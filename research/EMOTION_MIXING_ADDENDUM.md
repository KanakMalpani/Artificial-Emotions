# Emotion mixing addendum — speech/LDL vs annotation mixes (research)

**Status:** Deepening [`EMOTION_MIXING.md`](EMOTION_MIXING.md).  
**Honesty:** Speech synthesis / recognition mix papers do **not** validate our `{curiosity:40, confusion:30}` framing API as felt emotion. Steal **distribution** metaphors; reject biometric transfer.

*Generated: 2026-07-25*

---

## 1. Adjacent tech (do not over-port)

| Work | What it does | Misleading transfer |
|------|--------------|---------------------|
| **EmoMix** ([2306.00648](https://arxiv.org/abs/2306.00648)) | Diffusion TTS mixes emotion-conditioned noise | Audio affect ≠ investigation framing |
| **Mixed-EVC** ([2210.13756](https://arxiv.org/abs/2210.13756)) | Attribute vectors for mixed voice conversion | Still speech; ranking SVM among discrete labels |
| **Composable emotion steering TTS** ([2607.00946](https://arxiv.org/abs/2607.00946)) | Geometry of steering sites; joint steering ↑ intensity ↓ proportional control | Warns: multi-site mix can **break** proportional control — same risk if we over-stack cue+mix+inject |
| **EM2LDL** ([2511.20106](https://arxiv.org/abs/2511.20106)) | Multilingual speech corpus; **label distribution learning** over 32 categories | LDL ≈ our normalize-to-1 weights; they train SER — we must **not** train user-emotion classifiers |

**Useful metaphor only:** treat mix weights as a **distribution over framing labels**, not intensities of an internal mood engine.

---

## 2. Product implications

1. Keep mix API `honesty: annotation_only`.  
2. Soft guards already shipped — extend docs: stacking mix + sensitive cue presets + aggressive inject ≈ persuasion intensity ([`AFFECTIVE_SAFETY.md`](AFFECTIVE_SAFETY.md), arXiv 2511.22109).  
3. Public demo: disallow high-coercion social mixes (fear/anger-heavy) if not already.  
4. Do not add SER / voice / face pathways.

---

## 3. Productize next

- Docs: one sentence linking mix % ≈ LDL distribution metaphor (not SER).  
- Eval: when mix enabled, elicit rubric must not degrade vs epistemic-default mix.  
- Optional: `mix_intensity_cap` profile field (sum of non-epistemic weights ≤ τ).

---

## 4. Key citations

| Work | ID |
|------|-----|
| EmoMix | arXiv 2306.00648 |
| Mixed-EVC | arXiv 2210.13756 |
| Composable steering TTS | arXiv 2607.00946 |
| EM2LDL | arXiv 2511.20106 |
| In-repo | `emotions.py`, mix safety guards |
