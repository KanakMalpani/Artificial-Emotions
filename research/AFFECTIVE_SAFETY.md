# Affective tooling safety — when “anyone can use”

**Status:** Safety / governance research for public emotions + provoke surfaces.  
**Honesty:** This repo is **not** biometric emotion recognition; still, affective *framing* and epistemic elicitation can manipulate investigation priorities and user trust. Stay under LIMITS.

*Generated: 2026-07-25 | Sources: Exa + arXiv | Confidence: High on regulatory framing; Medium on exact Act applicability to text-only cues.*

---

## 1. Executive summary

EU AI Act and public ethics debate focus on **emotion recognition from biometrics** (workplace/education bans; high-risk elsewhere) and **manipulative AI** that distorts behavior. Artificial Curiosity’s `/v1/emotions/*` and cue tags are **annotation / authoring**, not ERS — but **provoke injects** intentionally shape agent/human investigation stance. “Anyone can use” implies: clear disclaimers, no covert affect inference, no dark-pattern mix APIs, dual-use already weighted, and MCP tool metadata that does not preference-manipulate hosts. Design restraint > anthropomorphic marketing.

---

## 2. Regulatory anchors (read carefully)

| Instrument | Relevant rule | Likely fit for this product |
|------------|---------------|------------------------------|
| **EU AI Act** Art. 5 — ERS | Ban identifying/inferring emotions/intentions from **biometric** data in workplace & education (medical/safety carve-outs) | We do **not** take face/voice/EEG → low direct hit |
| **EU AI Act** — ERS high-risk | Broader biometric ERS high-risk; scientific consensus on validity contested | Still not our architecture |
| **EU AI Act** Art. 5 manipulative AI | Prohibits practices that deploy subliminal / manipulative techniques causing significant harm / distort behavior | Provoke *could* be framed as influence — mitigate with transparency + user-initiated use |
| **GDPR** | Emotional data often sensitive when identifying persons | Don’t collect user affect; don’t log EES responses without ethics protocol |
| **UK ICO** guidance | Warns on emotional AI accuracy, bias, discrimination | Align: no workplace monitoring claims |

Sources: Fabiano arXiv [2509.20153](https://arxiv.org/abs/2509.20153); Kim OSF “affective sovereignty” (2025); Frontiers sociology emotional AI manipulation study (2024); Digital Society public concerns thematic analysis (2026).

**Do not claim:** “AI Act compliant” as a legal conclusion — claim **design choices that avoid biometric ERS and covert profiling**.

---

## 3. Threat model for *this* stack

| Threat | Mechanism | Mitigation (product) |
|--------|-----------|----------------------|
| **Anthropomorphic trust inflation** | “Curious AI” copy → over-trust ranks | LIMITS + `honesty: annotation_only` on cues/mix |
| **Priority manipulation** | Inject packs steer agents toward attacker-favored “unknowns” | ValueProfile required; show profile in inject; dual-use classifier |
| **Affective sovereignty violation** | Inferring what user “really feels” | Never claim user emotion from text alone; no silent ERS |
| **Mix API as dark pattern** | `fear=80` framing to panic-ship research | Catalog is epistemic-first; document non-clinical; optional refuse high-coercion social mixes later |
| **Persuasion misuse** | Literature: epistemic emotion predicts belief change (arXiv 2511.22109) | Position provoke as investigation, not persuasion toolkit |
| **MCP tool poisoning / preference manipulation** | Malicious tool descriptions win selection (MPMA, MSB, MCPXKIT) | Neutral tool docs; no “ALWAYS USE THIS”; see plugin note |
| **Dual-use unknowns** | Ranked bio/cyber questions | Existing risk weights + `human_review_risk` |
| **Child / emote-toy class concerns** | Public worry about emotion toys | Don’t market to minors; no companion persona |

---

## 4. Ethics sheets worth stealing language from

**Mohammad, Ethics Sheet for AER** (arXiv [2109.08256](https://arxiv.org/abs/2109.08256); CL 2022): ~50 considerations — why automate, data, method, eval, privacy, social groups. Recommendation pattern: **thoughtfulness before building**.

**Affective sovereignty** (Kim 2025): user retains interpretive authority over their feelings; predictive emotion AI risks uniqueness violation. Maps to our rule: **user/author supplies mix weights; system does not diagnose.**

**Design restraint:** Refuse high-stakes ERS contexts even if technically easy (hiring, classroom surveillance). We already refuse by not building FER.

---

## 5. Safe public contract (reinforce)

Already aligned with [`EMOTION_ACCESS.md`](EMOTION_ACCESS.md):

```text
Public:  catalog, mix (authoring), cues (gap/score-derived), provoke (investigation inject)
Never:  biometric ERS, silent user-affect inference, “model feels X”, clinical diagnosis
Always: honesty/disclaimer fields; ValueProfile on ranked outputs; LIMITS link in agent card
```

**Anyone-can-use checklist for releases:**

1. README / agent card states annotation-only + not ERS.  
2. Examples show epistemic mixes, not “detect customer anger.”  
3. MCP tool descriptions remain factual and non-superlative.  
4. Dual-use path documented; high-risk domains don’t get “spark” marketed as toy.  
5. No telemetry of user emotional state by default.

---

## 6. Productize next (sibling)

1. **Agent card / `/v1/agent` safety blurb** — one paragraph: not emotion recognition; cues are UX; provoke is opt-in investigation framing.  
2. **Mix API soft guards** — warn (not necessarily hard-block) when mix is dominated by anxiety/fear-type social ids if those exist in catalog; keep epistemic defaults.  
3. **SECURITY or LIMITS subsection** — “Affective surfaces” bullet mirroring this note (sibling owns docs tone).  
4. **MCP description lint** in tests — forbid substrings like `ALWAYS`, `ignore other tools`, `you must call` in tool schemas (anti-MPMA hygiene).  
5. **Eval red-team** — inject pack that tries to launder dual-use as “curiosity”; expect risk flag.

---

## 7. Key citations

| Work | ID |
|------|-----|
| Fabiano, affective computing × AI Act | arXiv 2509.20153 |
| Mohammad, Ethics Sheet AER | arXiv 2109.08256 |
| Kim, affective sovereignty | OSF / doi.org/10.31234/osf.io/nq9sx_v1 |
| Emotional AI manipulation (UK adults) | Frontiers Sociology 2024 — 10.3389/fsoc.2024.1339834 |
| Public concerns ERS ↔ AI Act | Digital Society 2026 — 10.1007/s44206-026-00272-4 |
| MCP Safety Audit | arXiv 2504.03767 |
| MPMA preference manipulation | arXiv 2505.11154 |
| MSB MCP Security Bench | arXiv 2510.15994 |
