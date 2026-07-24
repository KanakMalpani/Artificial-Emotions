# Cue threshold knobs — profile-scoped elicitation (research)

**Status:** Spec for ROADMAP cue knobs; code already accepts profile fields.  
**Honesty:** Thresholds change **tag frequency**, not scientific truth. Tuning for “more curiosity tags” is a UX A/B lever, not an emotion engine.

*Generated: 2026-07-25 | Code: `epistemic_cues.derive_epistemic_cues`*

---

## 1. What already exists

`derive_epistemic_cues` reads optional kwargs, else `ValueProfile` attributes, else defaults:

| Knob | Default | Effect when crossed |
|------|---------|---------------------|
| `cue_surprise_high` | `0.55` | Adds `surprise_signal` + `incongruity` (if unanswered-like) |
| `cue_neglectedness_high` | `0.55` | Adds `boredom_guard` |
| `cue_answerability_low` | `0.45` | Adds `confusion_risk` when answerability below + unanswered-like |

Returned payload already includes `thresholds` used — good for audit.

**Gap for sibling:** Confirm fields on `ValueProfile` schema + docs/examples; expose in web profile editor; document in agent card that knobs are **annotation intensity**, not ERS.

---

## 2. Psych-informed ranges (not calibrated)

| Intent | Suggested knobs | Rationale |
|--------|-----------------|-----------|
| **Conservative** (fewer tags) | surprise≥0.65, neglect≥0.65, answerability_low≤0.35 | Medium-gap literature: avoid tagging everything as incongruity |
| **Default** | 0.55 / 0.55 / 0.45 | Current |
| **Sensitive** (more confusion_risk) | answerability_low=0.55 | Safer for public demo — more “propose one experiment” framing |
| **Anti-boredom** | neglect≥0.45 | More boredom_guard on mid-neglect items |

Do **not** claim these map to EES cut-scores. Yanagisawa & Honda (arXiv [2401.00007](https://arxiv.org/abs/2401.00007)): info-gain peaks at intermediate surprise — lowering `cue_surprise_high` too far floods incongruity tags and may mimic over-arousal.

---

## 3. Eval protocol (tie to elicit A/B)

1. Fix ranked list; vary only cue knobs + inject template.  
2. Primary metric: investigation rubric (falsifier, specificity) — [`EPISTEMIC_ELICITATION.md`](EPISTEMIC_ELICITATION.md).  
3. Secondary (humans only): short EES curiosity/confusion items.  
4. Log `thresholds` in elicit eval JSON for reproducibility.

---

## 4. Safety note

Persuasion detection work finds **epistemic emotion** among top predictors of belief change (arXiv [2511.22109](https://arxiv.org/abs/2511.22109)). Lowering thresholds to maximize tags increases framing intensity — keep public-demo knobs **conservative** + disclaimer. See [`AFFECTIVE_SAFETY.md`](AFFECTIVE_SAFETY.md).

---

## 5. Productize next

1. Ensure `ValueProfile` documents `cue_*` fields (if missing, add optional floats).  
2. Web: advanced “cue sensitivity” slider → three presets (conservative/default/sensitive).  
3. Agent tool: pass-through already via profile; don’t add a separate “maximize curiosity” tool.  
4. Tests: snapshot tag sets at three presets on a fixture unknown.

---

## 6. Key citations

| Work | Role |
|------|------|
| Pekrun EES | Lab instrument only |
| Loewenstein / Yanagisawa–Honda | Medium gap / inverted-U |
| Hoang et al. 2511.22109 | Epistemic emotion ↔ persuasion risk |
| In-repo | `epistemic_cues.py`, elicit A/B |
