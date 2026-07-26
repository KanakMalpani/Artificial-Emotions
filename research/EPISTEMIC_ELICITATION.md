# Epistemic elicitation measurement → implications for `provoke`

**Status:** Deep research spike for ROADMAP §7.6 near-wedge *Epistemic emotion elicitation*.  
**Honesty bar:** Cues and inject framing are **investigation annotations**, not OCC/PAD engines and not claims that users or models “feel” EES emotions.  
**Related:** [`AI_EMOTIONS.md`](AI_EMOTIONS.md) §11–13, [`EMOTION_ACCESS.md`](EMOTION_ACCESS.md) §3.5, `src/artificial_emotions/epistemic_cues.py`, `provoke.py`.

*Generated: 2026-07-25 | Sources: Academia (S2 + arXiv) + Exa | Confidence: High on psych mechanisms; Medium on agent transfer; Low on calibrated EES→product conversion.*

---

## 1. Executive summary

Psychology measures epistemic emotions with **discrete scales (EES)** and **incongruity / high-confidence-error paradigms**. Those paradigms map cleanly onto what Artificial Emotions already ships: gap status + surprise/answerability axes + optional cue tags + provoke inject instructions. The productive product path is **not** embedding an EES API; it is **eval design**: A/B incongruity-framed injects → investigation quality (specificity, falsifiers), with optional short EES items only in human studies. Medium information gaps + sense of control beat “too wide / hopeless” gaps (Loewenstein; Pekrun control-value). Confusion is a **risk tag**, not a goal state. Profile `cue_*` knobs already exist — see [`CUE_THRESHOLD_KNOBS.md`](CUE_THRESHOLD_KNOBS.md) and `examples/cue_threshold_presets.json`.

---

## 2. Measurement instruments that matter

### 2.1 EES — Pekrun, Vogl, Muis & Sinatra (2017)

| Item | Detail |
|------|--------|
| Full name | Epistemically-Related Emotion Scales |
| DOI | [10.1080/02699931.2016.1204989](https://doi.org/10.1080/02699931.2016.1204989) |
| Emotions | Surprise, curiosity, enjoyment, confusion, anxiety, frustration, boredom |
| Validation | Multinational (US/Canada/Germany, N≈438); learning from **conflicting texts**; 7-factor model; metric invariance North America ↔ Germany |
| Dynamics | Scores change with conflicting task information; relate to perceived task value and strategy use |

**Product implication:** EES is a **lab instrument for humans**, not a runtime API. Short item subsets can score provoke A/B studies; do not expose `/v1/emotions/ees` as if the server measures users.

### 2.2 Behavioral + multi-channel complements

| Channel | Example | Fit for provoke eval |
|---------|---------|----------------------|
| Knowledge exploration clicks | Vogl et al. 2019 | Online A/B: “open more detail / propose experiment” |
| Multimodal trajectories | Wang et al. 2026 (BJEP) — tech-enhanced problem solving | Research only; out of product scope |
| LLM-rated investigation quality | Rubric: specificity, falsifier, enabling question | **Primary offline/agent metric** (no biosignals) |

Self-report alone is biased (recall, desirability); Pekrun & colleagues recommend complementing EES with behavior. For agent injects, **behavior = investigation artifacts**.

### 2.3 Curiosity vs interest (measurement pitfall)

Schmidt & Rotgans / Pekrun line (*Educational Psychology Review*): curiosity ≈ information-gap + sense that closure is **possible** + **intrinsic** value of closure; interest overlaps but is broader. Molar “curiosity+interest” items are sometimes justified for learning interventions. For this repo, keep catalog ids separate (`curiosity`, `interest`) but allow mixes ([`EMOTION_MIXING.md`](EMOTION_MIXING.md)); do not treat them as interchangeable axes in scoring.

---

## 3. Causal regularities (what to elicit)

### 3.1 Surprise → curiosity/confusion → exploration

**Vogl, Pekrun, Murayama, Loderer, Schubert** ([Frontiers in Psychology 2019](https://doi.org/10.3389/fpsyg.2019.02474); ~106 citations on S2):

- High-confidence errors / incongruity → surprise.
- Paths from surprise to **curiosity** and **confusion**.
- Curiosity (and to some extent confusion) → knowledge exploration.
- Effects described as robust across replications / meta-analytic path work in that line.

**Noordewier & Gocłowska** (*Emotion* 2023; DOI [10.1037/emo0001314](https://doi.org/10.1037/emo0001314)): shared vs unique features of awe, surprise, curiosity, interest, confusion, boredom — supports **discrete** epistemic categories (aligned with EES factoring), not a single “arousal” blob.

**Nerantzaki, Metallidou & Efklides** — cognitive conflict as arousal mechanism for epistemic emotions (*American Journal of Psychology*).

**Nerantzaki et al. 2025** — negative feedback that one’s answer is biased arouses epistemic emotions ([Europe’s Journal of Psychology](https://doi.org/10.5964/ejop.13847)).

### 3.2 Medium gap + control (Wundt / Loewenstein / Bayesian IG)

| Claim | Source | Provoke translation |
|-------|--------|---------------------|
| Medium information gaps elicit curiosity; too large → withdrawal | Loewenstein 1994; Pekrun control-value | Prefer ranked items with non-trivial but non-hopeless `answerability`; `confusion_risk` when low |
| Curiosity needs sense of control that gap can close | Peterson & Cohen; Pekrun | Inject: “propose one first experiment” + enabling question when confusion_risk |
| Bayesian info-gain peaks as inverted-U vs surprise | Yanagisawa & Honda arXiv [2401.00007](https://arxiv.org/abs/2401.00007) → *Frontiers in Psychology* 2025 | Aligns with keeping surprise high but not dumping unoperationalizable mega-gaps at top |

### 3.3 What *not* to optimize

| Anti-goal | Why |
|-----------|-----|
| Maximize confusion | Confusion can motivate *or* shut down; treat as risk, not reward |
| Maximize anxiety/frustration EES | Learning literature: often maladaptive for exploration quality |
| Claim anthropomorphic “the AI is curious” | Trust/manipulation risk; LIMITS honesty |
| Equate high `surprise` axis with user EES surprise | Different objects (score proxy vs self-report) |

---

## 4. Mapping onto shipped code (no rewrite required)

| Psych construct | Already in product | Gap |
|-----------------|-------------------|-----|
| Information gap | `GapStatus` unanswered / partial / caveat; cue `information_gap` | — |
| Curiosity target | Ranked unknowns + `curiosity_target` | — |
| Incongruity | High surprise + unanswered; or “related ≠ answered” notes → `incongruity` | Could log cue hit-rates in eval harness |
| Confusion risk | Partial/caveat or low answerability → `confusion_risk` | Optional: inject enabling-question prompt (already in `incongruity_investigate_block`) |
| Surprise signal | `surprise` axis threshold → `surprise_signal` | Thresholds are heuristic (`0.55`) — document in eval, don’t pretend calibrated to EES |
| Boredom guard | High neglectedness → `boredom_guard` | Weak psych link; honesty: anti-trend heuristic more than EES boredom |
| Investigation stance | `provoke` + falsifier demand | Primary outcome for A/B |

Current derivation (deterministic, offline-safe): `derive_epistemic_cues` in `epistemic_cues.py`.

---

## 5. Recommended elicitation eval protocol (research wedge)

### 5.1 Agent A/B (cheap, ship-first)

1. Fix domain + `ValueProfile` + model + temperature.
2. Conditions: (A) baseline inject, (B) inject + `incongruity_investigate_block` + cue line, (C) optional mix framing (`curiosity`+`confusion` weights — annotation only).
3. Blind rubric (human or separate judge model):  
   - names missing knowledge  
   - one first experiment  
   - falsifier  
   - enabling question if `confusion_risk`  
4. Report deltas + disagreement; **do not** claim EES equivalence.

### 5.2 Human study (optional, lab)

1. Conflicting / gap brief as stimulus (EES paradigm cousin).
2. Short EES items (curiosity, confusion, surprise, boredom) pre/post.
3. Primary *product* outcome still investigation quality; EES is secondary process measure.
4. Pre-register that medium-gap items should raise curiosity more than mega-gap items.

### 5.3 Explicit non-claims for any write-up

- Not validated clinical emotion detection.
- Not EU AI Act “emotion recognition” (no biometrics; see [`AFFECTIVE_SAFETY.md`](AFFECTIVE_SAFETY.md) when written).
- Not proof that LLMs experience epistemic emotions (Hoang et al. 2025 even use *LLM-rated* epistemic emotion as a **persuasion** feature — dual-use warning).

---

## 6. Productize next (for sibling / engineering)

Concrete, small wedges — research proposes, product owns:

1. **`curiosity eval elicit` (or eval suite flag)** — run agent A/B with/without incongruity block; write JSON scores under `evals/`.
2. **Cue telemetry in briefs** — already on items; add aggregate “% with confusion_risk in top-n” to eval report (debug false-hard gaps).
3. **Example pack** — `examples/elicit_ab_protocol.json` describing conditions + rubric (no secrets).
4. **Threshold config** — optional profile knobs for `surprise_high` / `answerability_low` used by `derive_epistemic_cues` (defaults stay).
5. **Do not** ship EES questionnaire API or biometric affect; keep `/v1/emotions/*` as catalog/mix/cues.

---

## 7. Open questions

1. Do cue tags change agent behavior beyond the prose investigate-block alone? (ablate tags vs block)
2. Cross-cultural EES invariance is only partial (NA↔DE in original); global UX copy must stay plain (“information gap”), not culturally loaded affect metaphors.
3. Persuasion literature treating epistemic emotion as a belief-change lever (arXiv [2511.22109](https://arxiv.org/abs/2511.22109)) — reinforce safety: provoke is for *investigation*, not covert attitude change.

---

## 8. Key citations

| Work | ID | Use |
|------|-----|-----|
| Pekrun et al., EES | DOI 10.1080/02699931.2016.1204989 | Measurement |
| Vogl et al. | DOI 10.3389/fpsyg.2019.02474 | Surprise→curiosity/confusion→explore |
| Noordewier & Gocłowska | DOI 10.1037/emo0001314 | Discrete epistemic feature structure |
| Loewenstein | *Psych Bulletin* 1994 | Information-gap curiosity |
| Yanagisawa & Honda | arXiv 2401.00007 | Bayesian IG / Wundt-like curve |
| Nerantzaki et al. | DOI 10.5964/ejop.13847 | Feedback → epistemic arousal |
| ROADMAP §7.6 | `docs/ROADMAP.md` | Near-wedge placement |
