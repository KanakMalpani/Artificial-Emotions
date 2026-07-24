# Consumer access patterns — AI / epistemic emotion capabilities

**Status:** Product-design research (how *anyone* can reach affect / epistemic tooling).  
**Scope:** APIs, libraries, HRI stacks, LLM toolkits, measurement instruments, datasets — what’s easy vs locked.  
**Honesty bar:** Same as [`AI_EMOTIONS.md`](AI_EMOTIONS.md) — detection, modeling, display, and elicitation are not “having feelings.” Artificial Curiosity ships **epistemic cue annotations + investigation ranking**, not a CME or affect sensor.

**Related:** [`AI_EMOTIONS.md`](AI_EMOTIONS.md) (theory / mechanisms), [`SOURCES.md`](SOURCES.md), [`CAPABILITY.md`](CAPABILITY.md), `src/artificial_curiosity/emotions.py`, example schemas under `examples/emotions_*.json`.

---

## 1. Executive brief

**Anyone who wants “emotion AI” today faces a fragmented market:**

| Need | Easiest path today | Locked / hard |
|------|-------------------|---------------|
| Face/voice *expression* scores for apps | Cloud SDKs (Hume Expression Measurement; legacy Face++/AWS) or local Py-Feat / OpenFace | Microsoft retired Face emotion attributes; Affectiva moved enterprise (Smart Eye); large face datasets need academic agreements |
| NPC / HRI *appraisal* (OCC-ish) | FAtiMA Toolkit (C#/Unity), GAMYGDALA (JS/MIT) | Full EMA/Soar stacks; little Python-first OCC |
| Text emotion labels | HF Transformers + GoEmotions; prompt/JSON classifiers | Culture/taxonomy mismatch; sarcasm |
| LLM “emotional alignment” eval | EmotionBench, CAREBench, CAPE (research) | Non-commercial licenses on some; not product APIs |
| *Epistemic* emotion (curiosity, confusion, …) | Psych scales (EES) + behavioral exploration; **this repo’s cue tags** | No mass-market EES API; almost no consumer SDK for epistemic affect |
| Rank *what to investigate next* with epistemic framing | **Artificial Curiosity** (library / CLI / HTTP / MCP) | Not a FER/SER product; no biosignal path |

**Product implication for this repo:** Do not compete with Hume/Py-Feat on face/voice. Own the **easy public contract for epistemic investigation framing** — resources, JSON schemas, examples, and thin HTTP/MCP surfaces that third parties can wire into agents, tutors, and research tools without pretending the engine feels.

---

## 2. Access-pattern taxonomy

```text
Consumer / developer intent
        │
        ├─▶ Sense human affect ────────── recognition APIs / local FER
        ├─▶ Simulate agent affect ─────── OCC / PAD / game engines
        ├─▶ Speak / look emotional ────── TTS, avatars, persona prompts
        ├─▶ Measure epistemic emotion ── EES / behavior / (rare) toolkits
        └─▶ Elicit investigation ──────── information-gap UX + ranked unknowns  ← this repo
```

| Pattern | What “access” means | Typical consumer | Fit for Artificial Curiosity |
|---------|---------------------|------------------|------------------------------|
| **A. Cloud recognition API** | `POST media → emotion scores` | App/product teams | Out of scope (privacy + wrong job) |
| **B. Local SDK / toolbox** | `pip install` / Unity package | Researchers, indie games | Adjacent (interop docs only) |
| **C. Appraisal middleware** | Events + goals → OCC labels | Games, HRI | Non-goal; cite FAtiMA/GAMYGDALA |
| **D. LLM toolkit / prompts** | Classify / generate affect text | Chat apps, eval harnesses | Partial: inject packs + honesty copy |
| **E. Instrument + dataset** | Scales, labeled corpora | Psych / ML researchers | Eval wedge (EES short items) |
| **F. Epistemic cue + rank API** | Gap/axes → tags + unknowns | Agents, educators, funders | **Primary public contract** |

---

## 3. Survey — what’s easy vs locked

### 3.1 Commercial / cloud emotion recognition

| Offering | Access model | Easy? | Notes |
|----------|--------------|-------|-------|
| **Hume AI** — Expression Measurement, EVI, Octave TTS | API key + Python/TS/.NET/Swift SDKs; batch + streaming | **Yes** for funded apps | Multimodal expression scores; docs stress expressions ≠ felt emotion ([dev.hume.ai](https://dev.hume.ai/intro)). Expression Measurement historically emphasized face/prosody/language; product surface evolving toward voice/TTS. |
| **Amazon Rekognition** Face emotions | AWS account + API | Medium | Basic categories; privacy/compliance burden |
| **Face++ (Megvii)** | Cloud API | Medium (region/account) | Common in benchmarks with Azure/Affectiva/Baidu (Yang et al. commercial FER comparison) |
| **Microsoft Azure Face — emotion attributes** | Historically API; **retired** for emotion inference | **Locked / gone** for new emotion use | Microsoft retired capabilities that “purport to infer emotional states” citing privacy, lack of consensus, demographic generalization ([Azure blog, 2022](https://azure.microsoft.com/en-us/blog/responsible-ai-investments-and-safeguards-for-facial-recognition/)); Face recognition itself is limited-access |
| **Affectiva / Affdex** | Enterprise / Smart Eye stack | **Locked** for casual builders | Once a research/API path; now commercial media/auto; iMotions integration for labs |

**Takeaway:** Cloud face-emotion is either **paywalled + policy-gated** or **being withdrawn** by major platforms. Voice/expression APIs (Hume) remain the path of least resistance for *display/recognition* products — not for epistemic research ranking.

### 3.2 Open recognition toolkits (local)

| Toolkit | License / install | Easy? | Strength |
|---------|-------------------|-------|----------|
| **Py-Feat** ([py-feat.org](https://py-feat.org/), [cosanlab/py-feat](https://github.com/cosanlab/py-feat)) | MIT toolbox; check per-model licenses (some non-commercial) | **Yes** for Python researchers | AU + emotion + V/A (v2); preprocess/analyze/visualize; HF weights |
| **OpenFace** | Academic / research use norms | Medium (build complexity) | Landmarks + AUs; widely cited |
| **LibreFace / MediaPipe FaceMesh** | Varies | Medium | Geometry / expression features |

**Takeaway:** Local FER is **accessible to technical users**; not a one-line “anyone” path. Model license fine print still locks commercial use of some weights.

### 3.3 OCC / appraisal libraries (agent emotion *simulation*)

| System | Access | Easy? | Theory |
|--------|--------|-------|--------|
| **FAtiMA Toolkit** ([GAIPS/FAtiMA-Toolkit](https://github.com/GAIPS/FAtiMA-Toolkit), Apache-2.0) | C# libraries + authoring GUI; Unity demos | Medium (Unity/.NET) | OCC + socio-emotional assets; designed for accessibility vs monolithic FAtiMA (Mascarenhas et al., ACM 2022; authoring arXiv:2206.03360) |
| **GAMYGDALA** ([broekens/gamygdala](https://github.com/broekens/gamygdala), MIT) | JavaScript (+ Phaser plugins) | **Yes** for web/games | Lightweight OCC-style appraisal from goals + beliefs (Popescu, Broekens & van Someren, IEEE TAC 2014) |
| **EMA** (Marsella & Gratch) | Research Soar integration | Hard | Appraisal dynamics + coping — not a consumer SDK |
| **ALMA / WASABI** | Papers + research code lineages | Hard | OCC+PAD / PAD+BDI |

**Takeaway:** If a third party wants *character emotions*, point them to **GAMYGDALA (JS)** or **FAtiMA (C#/Unity)** — not to Artificial Curiosity. This repo should **interop by vocabulary** (honest disclaimers), not reimplement OCC.

### 3.4 LLM emotion toolkits & benchmarks

| Resource | Access | Easy? | Use |
|----------|--------|-------|-----|
| **EmotionBench** (CUHK-ARISE; arXiv:2308.03656; NeurIPS 2024) | GitHub + HF; **research use, no commercial** | Medium | Situations → questionnaire deltas vs human norms |
| **CAREBench** (arXiv:2605.17176) | HF CC-BY-NC-ND + scripts | Medium | Appraisal reasoning chain eval |
| **CAPE** (NAACL Findings 2025) | Paper + dataset corpus (Chinese appraisal dialogues) | Research | Appraisal-conditioned generation |
| **HF text classifiers / GoEmotions models** | `pip` + Apache-2.0 data | **Yes** | 27-label text emotion incl. *curiosity* / *confusion* (social, not EES) |
| **Prompt-JSON emotion GGUF / templates** | Local runners | Easy but unvalidated | Cheap; not scientific measurement |

**Takeaway:** LLM affect is **easy to glue** and **easy to overclaim**. Prefer structured appraisal benchmarks for eval; keep product copy anti-anthropomorphic.

### 3.5 Epistemic emotion measurement (EES & cousins)

| Instrument | Access | Easy? | Notes |
|------------|--------|-------|-------|
| **EES — Epistemically-Related Emotion Scales** (Pekrun, Vogl, Muis & Sinatra, *Cognition & Emotion*, 2017; DOI [10.1080/02699931.2016.1204989](https://doi.org/10.1080/02699931.2016.1204989)) | Journal / publisher; items via paper | Medium (psych practice + ethics) | Surprise, curiosity, enjoyment, confusion, anxiety, frustration, boredom |
| **Behavioral exploration** (Vogl et al., Frontiers 2019) | Paradigm replication | Medium | Clicks for explanations — good A/B for provoke packs |
| **This repo epistemic cues** | Library + HTTP | **Yes** | Tags only — not EES scores; see §5 |

**Gap:** There is **no** widely deployed commercial “EES-as-a-Service.” Epistemic emotion remains a **psychometrics + study design** problem. Artificial Curiosity can (1) emit framing tags, (2) document EES as optional human eval, (3) never claim cue tags = EES scores.

### 3.6 Open datasets — easy vs locked

| Dataset | Access | Easy? |
|---------|--------|-------|
| **GoEmotions** | Public CSV / HF; Apache-2.0 | **Easy** |
| **FER2013 / many HF FER mirrors** | Public (check license) | Easy for toys; quality/bias limits |
| **RAF-DB** | Free for university-affiliated researchers; no redistribute | **Locked** (form + affiliation) |
| **AffectNet** | Academic agreement (IRB, non-commercial, no third-party share); commercial license separate | **Locked** |
| **EmotionBench / CAREBench situations** | Public for research; NC on some | Medium |

**Takeaway:** Text emotion data is open; **in-the-wild face** gold standards are gated. Product docs should not depend on redistributing AffectNet/RAF-DB.

### 3.7 HRI / embodiment access

| Path | Easy? | Caution |
|------|-------|---------|
| Social robot SDKs (vendor-specific) + FAtiMA/expression | Medium | Emotion *display* can reduce trust in some tasks (Becker et al., arXiv:2307.02924) |
| Companion chat + empathic TTS (Hume EVI, etc.) | Easy | High anthropomorphism / persuasion risk |
| Curiosity ranking inject into robot tutor | Easy via HTTP/MCP | Prefer investigation framing over “caring face” |

---

## 4. What “anyone” actually needs (jobs to be done)

| Persona | Job | Best access pattern | This repo should give them |
|---------|-----|---------------------|----------------------------|
| Indie app maker | React to user tone | Hume / local SER / text classifier | Links + ethics checklist — not a face API |
| Game / HRI builder | Believable NPC affect | GAMYGDALA / FAtiMA | Explicit non-overlap statement |
| Teacher / edtech | Spark productive curiosity | Epistemic framing + ranked gaps | **Provoke + cues + elicit helpers** |
| AI agent builder | Tool to prefer unknowns | OpenAPI + MCP tools | Stable schemas + examples |
| Affective scientist | Measure epistemic emotion | EES + behavior | Pack seeds + eval notes; no fake EES API |
| Policy / safety | Limit covert affect | Prefer no biosignal; honest labels | LIMITS + disclaimers in every payload |

---

## 5. Recommended minimal public contract (this repo)

**Principle:** One honest, offline-safe surface for **epistemic investigation framing**, plus discoverable resources. Do not expand into FER/SER/OCC.

### 5.1 Resources (what third parties consume)

| Resource | Purpose | Stability |
|----------|---------|-----------|
| Cue vocabulary | `information_gap`, `curiosity_target`, `confusion_risk`, `surprise_signal`, `incongruity`, `boredom_guard` | Freeze names; extend only with changelog |
| Honesty fields | Every emotions payload includes `honesty: "annotation_only"` + `disclaimer` | Required |
| Domain pack | `affective_science` seed questions | Versioned JSON |
| Elicit helpers | Incongruity → experiment → falsifier framing text | Semver soft |
| Ranked unknowns | Existing provoke/run contract | Already public |
| Example schemas | `examples/emotions_*.json` | Contract samples |

### 5.2 Surfaces (implementation already converging)

| Surface | Path / entry | Notes |
|---------|--------------|-------|
| Python | `artificial_curiosity.emotions` | `list_epistemic_cues`, `annotate_epistemic`, `elicit_helpers`, `emotion_pack` |
| HTTP | `/v1/emotions/*` (+ `/v1/epistemic/*` aliases) | See OpenAPI-ish shapes below |
| Agent / MCP | `list_epistemic_cues` (+ annotate if exposed) | Same JSON |
| CLI | emotions / cues subcommands (if shipped) | Mirror HTTP |

**Non-goals in the contract:** face upload, voice stream, OCC state machine, “emotion intensity of the AI,” silent biosensing.

### 5.3 OpenAPI-ish shapes (for product agent / third parties)

Use these as the **recommended** request/response contracts. Field names match `emotions.py` / `AnnotateEmotionsRequest` where already implemented.

#### `GET /v1/emotions/cues`

```yaml
responses:
  200:
    description: Cue catalog
    content:
      application/json:
        schema:
          type: object
          required: [cues, tags, honesty, disclaimer]
          properties:
            cues:
              type: array
              items:
                type: object
                required: [tag, meaning]
                properties:
                  tag: { type: string }
                  meaning: { type: string }
            tags:
              type: array
              items: { type: string }
            honesty:
              type: string
              enum: [annotation_only]
            disclaimer: { type: string }
            docs: { type: string }
            note: { type: string }
```

#### `POST /v1/emotions/annotate` (also GET with query params)

```yaml
requestBody:
  required: true
  content:
    application/json:
      schema:
        type: object
        required: [question]
        properties:
          question: { type: string, minLength: 12 }
          gap_status:
            type: string
            enum: [unanswered, partially_answered, likely_answered, unknown_with_caveat]
            default: unanswered
          surprise: { type: number, minimum: 0, maximum: 1, default: 0.5 }
          neglectedness: { type: number, minimum: 0, maximum: 1, default: 0.5 }
          answerability: { type: number, minimum: 0, maximum: 1, default: 0.5 }
          notes: { type: string, default: "" }
          domain: { type: string, default: "ai" }
responses:
  200:
    content:
      application/json:
        schema:
          type: object
          required: [question, gap_status, axes, epistemic_cues, honesty, disclaimer]
          properties:
            question: { type: string }
            gap_status: { type: string }
            axes:
              type: object
              properties:
                surprise: { type: number }
                neglectedness: { type: number }
                answerability: { type: number }
            epistemic_cues:
              $ref: '#/components/schemas/EpistemicCues'
            inject_fragment: { type: string }
            honesty: { type: string, enum: [annotation_only] }
            disclaimer: { type: string }
```

#### `EpistemicCues` (embedded on annotate + provoke unknowns)

```yaml
EpistemicCues:
  type: object
  required: [tags, primary, disclaimer, honesty]
  properties:
    tags:
      type: array
      items:
        type: string
        enum:
          - incongruity
          - information_gap
          - curiosity_target
          - confusion_risk
          - surprise_signal
          - boredom_guard
    primary: { type: string }
    disclaimer: { type: string }
    honesty: { type: string, enum: [annotation_only] }
```

#### `GET /v1/emotions/elicit`

```yaml
responses:
  200:
    content:
      application/json:
        schema:
          type: object
          required: [framing, inject_prefix, how_to_use, honesty, disclaimer]
          properties:
            framing: { type: string }
            inject_prefix: { type: string }
            how_to_use:
              type: array
              items: { type: string }
            honesty: { type: string, enum: [annotation_only] }
            disclaimer: { type: string }
            docs: { type: string }
```

#### `GET /v1/emotions/pack?name=affective_science`

```yaml
parameters:
  - name: name
    in: query
    schema: { type: string, default: affective_science }
responses:
  200:
    content:
      application/json:
        schema:
          type: object
          required: [name, count, questions, honesty, disclaimer]
          properties:
            name: { type: string }
            pack_name: { type: string }
            version: { type: string }
            domain: { type: string }
            description: { type: string }
            count: { type: integer }
            questions:
              type: array
              items:
                type: object
                properties:
                  id: { type: string }
                  question: { type: string }
                  operationalization: { type: string }
                  why_it_matters: { type: string }
                  tags: { type: array, items: { type: string } }
                  assumptions: { type: array, items: { type: string } }
            honesty: { type: string, enum: [annotation_only] }
            disclaimer: { type: string }
            docs: { type: string }
            research: { type: string }
```

#### Compose with curiosity (existing)

```text
GET|POST /v1/curiosity/provoke  → unknowns[].epistemic_cues + inject
POST     /v1/curiosity/run      → ranked unknowns (optional cues)
```

Third parties who only want **spark + framing**:

1. `GET /v1/curiosity/provoke?domain=ai&n=5&fast=true`  
2. Optionally `GET /v1/emotions/elicit` for framing prefix  
3. Paste `inject` into any LLM tool loop  

### 5.4 Library contract (Python one-liners)

```python
from artificial_curiosity.emotions import (
    list_epistemic_cues,
    annotate_epistemic,
    elicit_helpers,
    emotion_pack,
)
from artificial_curiosity import provoke  # ranked unknowns + inject
```

### 5.5 Example files

| File | Role |
|------|------|
| [`examples/emotions_cues_response.json`](../examples/emotions_cues_response.json) | Catalog sample |
| [`examples/emotions_annotate_request.json`](../examples/emotions_annotate_request.json) | Annotate body |
| [`examples/emotions_annotate_response.json`](../examples/emotions_annotate_response.json) | Annotate result |
| [`examples/emotions_elicit_response.json`](../examples/emotions_elicit_response.json) | Elicit helpers sample |

---

## 6. Ethics — consent & manipulation when “anyone can use” affect tooling

Broad access amplifies dual-use. Design defaults:

| Risk | Why “open access” worsens it | Mitigation for this repo |
|------|------------------------------|---------------------------|
| **Covert sensing** | Face/voice APIs invite always-on webcam | **No** media upload endpoints; document that FER is out of trust boundary |
| **Consent theater** | TOS click ≠ informed affect processing | Recommend explicit consent for any *human* affect sensing third parties bolt on; our cues annotate *questions*, not people |
| **Emotional deception** | Fluent “I feel…” agents | Forced `honesty`/`disclaimer`; anti-anthropomorphic inject copy |
| **Manipulation / persuasion** | Affect framing shifts donations, trust, votes | Epistemic framing only (gap → experiment → falsifier); dual-use red-team in FAILURE_MODES |
| **Addiction loops** | Variable surprise + social reward | Optimize for investigation quality, not dwell time |
| **Misrecognition harm** | Biased FER → unfair treatment | Don’t ship FER; warn integrators |
| **Scale of epistemic nudge** | Provoking curiosity can still steer agendas | Require explicit ValueProfile; surface weights |
| **Regulatory** | Affective AI under privacy / AI Act scrutiny (e.g. arXiv:2509.20153) | Bounded claims; no covert affect |

**Consent rule of thumb for integrators:**

1. If you process **biometric / face / voice** → obtain purpose-limited consent; prefer on-device; allow opt-out.  
2. If you use **only this repo’s epistemic tags** → disclose that tags are *UX annotations for investigation*, not mood diagnosis.  
3. If you run **EES / surveys** → IRB / informed consent as psychology practice requires.  
4. Never market cue tags or provoke packs as “emotion recognition of the user.”

---

## 7. Recommendations for Artificial Curiosity product design

1. **Own pattern F** (epistemic cue + rank). Advertise “investigation framing for agents & humans,” not “Emotion AI.”  
2. **Publish the minimal contract** (§5) + `examples/emotions_*.json` so third parties integrate without reading the monograph.  
3. **Link out** for patterns A–C (Hume, Py-Feat, FAtiMA, GAMYGDALA) instead of reimplementing.  
4. **Keep every emotions response self-describing** (`honesty`, `disclaimer`).  
5. **Optional eval kit** (docs only): short EES items + behavioral “open explanation” clicks for provoke A/B — do not fake an EES API.  
6. **MCP/OpenAI tools**: expose `list_epistemic_cues` + `annotate_epistemic` + `provoke_curiosity` as the agent triad.  
7. **Ethics in README one-liner:** annotations ≠ feelings; no covert sensing.

---

## 8. Annotated sources (access-focused)

| Source | Link | Used for |
|--------|------|----------|
| Hume AI docs / SDKs | https://dev.hume.ai/intro | Cloud expression + voice access pattern |
| Microsoft Responsible AI Face changes | https://azure.microsoft.com/en-us/blog/responsible-ai-investments-and-safeguards-for-facial-recognition/ | Emotion attribute retirement / limited access |
| Yang et al., commercial FER under distortion | https://www.jorgegoncalves.com/docs/tvc20.pdf | AWS / Face++ / Azure / Affectiva / Baidu landscape |
| Py-Feat | https://py-feat.org/ ; arXiv:2104.03509 | Easy local FER toolbox |
| FAtiMA Toolkit | https://github.com/GAIPS/FAtiMA-Toolkit ; ACM 10.1145/3510822 | Accessible OCC social agents |
| GAMYGDALA | https://github.com/broekens/gamygdala ; IEEE TAC 2014 | Easy game appraisal (MIT/JS) |
| EmotionBench | arXiv:2308.03656 ; https://github.com/CUHK-ARISE/EmotionBench | LLM emotion alignment toolkit (NC) |
| CAREBench | arXiv:2605.17176 | Appraisal-chain LLM eval |
| CAPE | ACL Anthology 2025.findings-naacl.353 | Appraisal-conditioned generation data |
| GoEmotions | https://github.com/google-research/google-research/tree/master/goemotions | Easy open text emotion data |
| AffectNet license | University of Denver academic agreement | Locked face dataset |
| RAF-DB | http://www.whdeng.cn/RAF/model1.html | Affiliation-gated FER data |
| Pekrun et al., EES | DOI 10.1080/02699931.2016.1204989 | Epistemic emotion measurement |
| Vogl et al. | DOI 10.3389/fpsyg.2019.02474 | Surprise/curiosity/confusion → exploration |
| Becker et al. | arXiv:2307.02924 | HRI emotion display can hurt trust |
| Affective computing × AI Act | arXiv:2509.20153 | Regulatory framing |
| In-repo theory | [`AI_EMOTIONS.md`](AI_EMOTIONS.md) | Mechanisms & honesty bar |

---

## 9. One-paragraph bottom line

Consumer “emotion AI” access is easy for **cloud expression / empathic voice**, **local FER toolboxes**, **game OCC middleware**, and **LLM text affect** — and increasingly **locked** for platform face-emotion APIs and gold-standard face datasets. **Epistemic** emotion (curiosity, confusion, …) has strong psychometrics (EES) but almost no mass-market SDK. Artificial Curiosity should make *that* gap easy: a **minimal public contract** of cue vocabulary, annotate/elicit/pack resources, example JSON, and compose-with-provoke HTTP/MCP — always labeled `annotation_only` — while pointing builders elsewhere for face, OCC, and companion affect, with consent and anti-manipulation defaults.
