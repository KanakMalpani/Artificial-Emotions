# Emotion mixing / blends — research notes for percentage mixes

**Status:** Durable design research for Artificial Curiosity’s **mixable emotion catalog** (UX annotations only).  
**Honesty bar:** Same as [`AI_EMOTIONS.md`](AI_EMOTIONS.md) — percentages are **framing weights**, not intensities of felt emotion in the software, and not clinical diagnoses of users.  
**Related:** [`EMOTION_ACCESS.md`](EMOTION_ACCESS.md) (public contract), [`SOURCES.md`](SOURCES.md), product surface `GET /v1/emotions/catalog` · `POST /v1/emotions/mix`.

*Generated: 2026-07-24 | Sources: Exa + prior monograph | Confidence: High on CME/psych mechanisms; Medium on exact PAD numeric anchors (illustrative).*

---

## 1. Executive summary

Psychology and computational emotion models (CMEs) both treat **mixtures** as first-class: same-valence blends are common; cross-valence “mixed feelings” occur; dimensional spaces (PAD/VAD) make **interpolation** natural; Plutchik formalizes **dyads** as adjacent primary compounds; OCC supplies **intensity** variables per category rather than a single % blend API. For this repo, a practical contract is: accept `{emotion_id: percent|weight}`, **normalize to sum 1.0**, return a **blend profile** (weighted PAD anchors + cue tags + framing text) labeled `honesty: annotation_only`. Do **not** claim the AI feels the blend, that weights equal EES scores, or that PAD interpolation is a validated psych instrument.

**Addendum:** Speech mix / LDL literature ([`EMOTION_MIXING_ADDENDUM.md`](EMOTION_MIXING_ADDENDUM.md)) — distribution metaphor only; joint steering can break proportional control.

---

## 2. Broader emotion sets usable in tools

| Family | Typical members | Tool use | Fit here |
|--------|-----------------|----------|----------|
| **Basic / categorical** (Ekman; Plutchik 8) | Anger, fear, joy, sadness, disgust, surprise (+ anticipation, trust) | FER labels; expression tables; NLP multilabel | Catalog ids for *framing*; not FER |
| **Dimensional** (Russell VAD; Mehrabian PAD) | Continuous pleasure/arousal/(dominance) | Mood decay, expression morphs, ALMA/WASABI | Optional **anchors** for mix interpolation |
| **OCC appraisal** (~22 types) | Joy, distress, hope, fear, pride, shame, … | Rule engines (FAtiMA, GAMYGDALA, ALMA) | Cite, don’t reimplement; intensity ≠ our % |
| **Epistemic** (Pekrun EES; Vogl et al.) | Surprise, curiosity, enjoyment, confusion, anxiety, frustration, boredom (+ awe/interest in extended sets) | Learning / investigation UX | **Primary product vocabulary** |
| **Social / achievement** | Pride, shame, gratitude, admiration; hope, relief, frustration | Tutors, HRI, narrative agents | Secondary catalog family |

**Epistemic core (product-first):** curiosity, interest, confusion, surprise, awe/wonder, boredom, intrigue/uncertainty — aligned with EES + information-gap theory (Loewenstein) and this repo’s existing cue tags.

---

## 3. How blending is justified (psychology & CME)

### 3.1 Hierarchical affect & mixed feelings

Watson & Stanton (*Emotion Review*, 2017): same-valence **blends** (e.g. fear+sadness) are central to Positive/Negative Activation structure; **cross-valence** mixtures (nervous+alert) are compatible but less central. Implication: multi-label / multi-weight APIs match how people actually report affect better than forced single-category APIs.

### 3.2 PAD / VAD interpolation

Marsella, Gratch & Petta (computational models survey): dimensional models excel at **continuous behavior generation** because three axes map cleanly to actuators/mood. WASABI / ALMA maintain PAD **mood** that blends over time; FLAME uses fuzzy membership for intensity/blending. **Weighted average of PAD vectors** is the standard engineering move — justified as a *representation* blend, not as proof of phenomenology.

### 3.3 Plutchik dyads

Plutchik: eight primaries; all other emotions are **mixtures**; adjacent pairs form **primary dyads** (joy+trust→love, fear+surprise→awe, anticipation+joy→optimism, …), with secondary/tertiary/opposite dyads by wheel distance. Intensity has mild/medium/strong rings. NLP work (PyPlutchik; EMNLP 2024 Plutchik+MoE; SPOKE geometric embeddings) treats dyads as compositional. **Caution:** dyad names are **taxonomic metaphors**; exposing a `plutchik_dyad_hint` is optional enrichment, not a scientific claim that the user “has love.”

### 3.4 OCC intensity (not the same as mix %)

OCC emotions have **intensity variables** (desirability × likelihood, etc.). Simultaneous appraisals can yield **multiple active emotions** (EMA stacks appraisals; mood summarizes). That is **not** the same as user-authored `curiosity=40, confusion=30`. Our mix API is **authoring / framing**, closer to FLAME fuzzy blends or game middleware sliders than to live OCC derivation.

### 3.5 What % mixes must NOT claim

| Claim | Why invalid |
|-------|-------------|
| “The model feels 40% curious” | No phenomenal state; annotation only |
| “User affect measured at these %” | No biosignal / EES instrument in this surface |
| “PAD blend is clinically validated mood” | Anchors are illustrative literature-ish defaults |
| “Equals OCC intensity” | Different formal object |
| “Plutchik dyad = ground truth compound emotion” | Heuristic wheel geometry |

---

## 4. Practical API schema (this repo)

```text
Input:  { emotion_id: number, ... }   # percent (0–100) OR weight (≥0)
Rules:  1–8 components; known catalog ids; non-negative; sum > 0
Norm:   w_i' = w_i / Σw  →  weights sum to 1.0; percents = 100·w_i'
Out:    blend { weights, percents, pad, families, cue_tags, framing, inject_fragment }
        + honesty: annotation_only + disclaimer
Reject: unknown id, empty, all-zero, >max components, negative weights
```

**Soft validation:** Accept either scale (40+30+30 or 0.4+0.3+0.3); if max value ≤ 1.5 treat as weights, else as percentages — always re-normalize. Document both in `docs/EMOTIONS.md`.

**Max components:** 8 (enough for rich mixes; prevents spam).

---

## 5. Product mapping

| Artifact | Role |
|----------|------|
| `packs/emotion_catalog.json` | Named emotions + family + PAD anchors + elicit hints + cue links |
| `emotion_catalog()` / `GET /v1/emotions/catalog` | List individuals |
| `mix_emotions(...)` / `POST /v1/emotions/mix` | Percentage mixes |
| Existing cues/annotate/elicit/pack | Unchanged; mix *extends* contract |

---

## 6. Annotated sources (mixing-focused)

| Source | Link / ID | Used for |
|--------|-----------|----------|
| Watson & Stanton, Emotion blends | DOI 10.1177/1754073916639659 | Same-valence blends vs cross-valence mixed feelings |
| Marsella, Gratch & Petta, CME review | https://people.ict.usc.edu/~gratch/papers/MarGraPet_Review-old.pdf | PAD for continuous blend; appraisal vs dimensional |
| Plutchik psychoevolutionary theory | Plutchik 1980/2001; dyad tables | Primary/secondary/tertiary dyads; intensity rings |
| Semeraro et al., PyPlutchik | DOI 10.1371/journal.pone.0256503 | Quantitative wheel + dyad visualization |
| Plutchik + MoE classification | ACL Anthology 2024.emnlp-main.50 | Dyad decomposition in NLP labeling |
| SPOKE Plutchik geometry | OpenReview SPOKE (2025/26) | Opposition / dyad composition / intensity as constraints |
| Pekrun et al., EES | DOI 10.1080/02699931.2016.1204989 | Epistemic discrete set |
| Vogl et al. | DOI 10.3389/fpsyg.2019.02474 | Surprise/curiosity/confusion → exploration |
| Becker-Asano WASABI | Thesis / AAMAS | PAD dynamics + blending mood |
| Gebhard ALMA | IVA/AAMAS | OCC + PAD simultaneous emotion/mood |
| In-repo | [`AI_EMOTIONS.md`](AI_EMOTIONS.md), [`EMOTION_ACCESS.md`](EMOTION_ACCESS.md) | Honesty bar + public contract |

---

## 7. Bottom line

**Individuals** = catalog entries (esp. epistemic). **Mixes** = normalized weights over catalog ids → interpolated PAD + cue tags + investigation framing. Justified by psych blends, PAD CME practice, and Plutchik composition — always **annotation_only**.
