# Emotions in AI — how they are produced, modeled, and misread

**Status:** Expanded research monograph (durable notes for Artificial Curiosity).  
**Honesty bar:** This document distinguishes *having* emotions from *modeling*, *detecting*, *displaying*, and *eliciting* affect. Nothing here claims that Artificial Curiosity (or current LLMs) *feel*. Curiosity in this repo is a **decision / information-seeking layer**, not an anthropomorphic mind.

**Primary workspace path:** `research/AI_EMOTIONS.md`  
**Related in-repo:** [`FIRST_PRINCIPLES.md`](FIRST_PRINCIPLES.md) (decision-theoretic curiosity), [`SOURCES.md`](SOURCES.md) (curiosity / VOI bibliography), `src/artificial_curiosity/provoke.py` (epistemic *provoke*), `src/artificial_curiosity/epistemic_cues.py` (optional UX annotations), [`docs/ROADMAP.md`](../docs/ROADMAP.md) §7.6 / near-wedge pointer.

**Revision note:** Second-pass expansion beyond the initial spike — classical theories, CME architecture survey, ML recognition/generation stacks, RL functional analogs, LLM appraisal evidence, neuromodulation (cautious), HRI, epistemic-emotion elicitation design, ethics, and concrete product wedges.

---

## 1. Executive brief

**“Emotion in AI” is not one phenomenon.** Affective computing (Picard, 1997) covers systems that *relate to*, *arise from*, or *deliberately influence* emotions. In practice, work clusters into:

| Cluster | What the system does | Example |
|---------|----------------------|---------|
| **Recognition** | Infer human affect from signals | Face/voice/text emotion classifiers |
| **Modeling / elicitation** | Compute an internal affect state from appraisals or rewards | OCC agents, EMA, WASABI, CPM–RL hybrids |
| **Expression / display** | Render affect in face, voice, text, posture | Social robots, “empathic” chat personas |
| **Influence / elicitation of *user* affect** | Change human emotions via interaction | Companion bots, persuasive UX, learning systems |
| **Intrinsic drives (RL)** | Use novelty / prediction-error / progress bonuses as *motivational analogs* | ICM, RND, learning-progress curiosity, empowerment |
| **Linguistic affect prediction** | Predict affect-*laden* tokens / labels | LLM emotion classification & persona prompting |

**Production mechanisms** range from hand-crafted appraisal trees (OCC) and dimensional continuous spaces (VAD / PAD), through multimodal ML pipelines, to RL intrinsic motivation and LLM prompting. Neuromorphic and embodied robots add sensors and actuators but do not dissolve the philosophical gap between simulation and experience.

**Link to this project:** Epistemic emotions in psychology (curiosity, interest, confusion, surprise, awe) are *about knowledge*—they track cognitive incongruity and often drive exploration (Pekrun & Stephens; Vogl et al.; EES scales). Artificial Curiosity’s **surprise / neglectedness / tractability** axes and **`provoke` inject packs** are best read as **structured elicitors of epistemic investigation in *agents and humans***, analogous in *function* (promote exploration of unknowns) but **not** as claims that the software has feelings.

**Safety spine:** Anthropomorphism raises trust, attachment, and manipulation risk; affective persuasion is dual-use. Keep product copy and LIMITS honest: scores are decision aids; provoke is not “the AI is curious.”

---

## 2. Classical theories of emotion (psychology → computation)

Computation inherits *fragments* of psychological theory. Understanding the source theories prevents naive one-to-one mapping (“we implemented James–Lange therefore the robot feels”).

### 2.1 Peripheral / bodily theories

| Theory | Core claim | Computational echo | Honesty limit |
|--------|------------|-------------------|---------------|
| **James–Lange** (late 19th c.) | Perception → bodily change → *felt* emotion (“we are afraid because we run”) | Sensor-driven affect (HR, posture); “somatic markers” as tags on percepts (Kismet lineage) | Body signals ≠ phenomenal fear in silicon |
| **Cannon–Bard** | Thalamus-ish central processing → simultaneous feeling + physiology | Parallel affect + action modules | Rarely implemented faithfully; often a slogan |
| **Damasio somatic marker** | Affective tags bias decision under uncertainty | Explicit [A,V,S] or valence tags on releasers; neuromodulator analogs | Useful *decision bias* metaphor; not proof of feeling |

### 2.2 Two-factor / cognitive labeling

**Schachter–Singer (1962):** undifferentiated arousal + cognitive label → emotion. Computational cousins: (1) continuous arousal/valence dynamics + (2) categorical labeling layer (WASABI-style PAD → named regions). Risk: any fluent labeler (LLM) can *rename* arousal into empathy theater.

### 2.3 Appraisal theories (dominant in CMEs)

| Theory | Core claim | Typical CME use |
|--------|------------|-----------------|
| **Lazarus** | Primary/secondary appraisal; coping; relational meaning | EMA (Gratch & Marsella): appraisal dynamics + coping operators on Soar |
| **OCC (Ortony, Clore & Collins, 1988; 2nd ed. 2022)** | Events / agents / objects → ~22 emotion types with intensity vars | Rule engines (FearNot!, FAtiMA, ALMA, many games) |
| **Scherer CPM (Component Process Model)** | Sequential checks: novelty → intrinsic pleasantness → goal relevance → agency → coping → normative significance; multi-component synchronization | FAtiMA Modular; Zhang–Broekens–Jokinen TD formalization of checks |

**OCC** remains the workhorse for *eliciting conditions* because it is structurally computable. Steunebrink et al. (“OCC Model Revisited,” KI 2009) document logical ambiguities that implementers quietly paper over. Adam, Herzig & Longin provide modal/BDI formalizations; Sarlej & Ryan show event-calculus subsets for narrative AI.

**CPM** is process-oriented (ordered checks, continuous differentiation) rather than a flat emotion taxonomy. Scherer frames emotion as an organism–environment interface: appraisal → component patterning (physiology, expression, action tendency) → feeling → labeling. Zhang, Broekens & Jokinen (arXiv:2309.06367) map several CPM checks onto temporal-difference RL updates—linking appraisal to reward learning **without** claiming phenomenal feeling.

### 2.4 Dimensional models

| Model | Axes | Use in AI |
|-------|------|-----------|
| **Russell circumplex** | Valence × Arousal | Continuous mood; interpolation of expressions |
| **Mehrabian PAD** | Pleasure–Arousal–Dominance | WASABI, ALMA mood/personality coupling; robot affect spaces |
| **Kismet AVS** | Arousal–Valence–Stance | Embodied social regulation (Breazeal) |

Dimensional spaces excel at **blending and decay**; they are weak at **why** an emotion arose (appraisal supplies the why).

### 2.5 Constructionism & categorical basics

| Family | Core idea | Computational footprint |
|--------|-----------|-------------------------|
| **Basic emotions (Ekman, Izard, …)** | Discrete evolved categories + facial AUs | FER datasets; robot expression tables |
| **Plutchik** | Wheel / intensity / blends | Often UI metaphors more than engines |
| **Constructionism (Barrett et al.)** | Emotions constructed from core affect + concepts + situating | Harder as a CME “engine”; closer to LLM *concept-mediated* affect prediction |

**Takeaway:** Constructionism warns that category labels are cultural/linguistic constructs—relevant when LLMs “recognize” emotion in text they helped popularize.

### 2.6 Theory → computation map (summary)

```text
Stimulus / event
      │
      ▼
┌─────────────────┐     ┌──────────────────┐
│ Appraisal rules │     │ Dimensional dyn. │
│ (OCC / CPM /    │────▶│ (PAD / VAD / AVS)│
│  Lazarus vars)  │     └────────┬─────────┘
└────────┬────────┘              │
         │                       ▼
         │              ┌────────────────┐
         └─────────────▶│ Category / label│
                        │ (joy, fear, …) │
                        └────────┬───────┘
                                 │
              ┌──────────────────┼──────────────────┐
              ▼                  ▼                  ▼
         Expression         Action bias         User elicitation
         (face/voice/text)  (policy / coping)   (persuasion / HRI)
```

---

## 3. Taxonomies — what “emotion in AI” means

### 3.1 Having vs modeling vs displaying vs detecting vs eliciting

Picard’s early framing already separated multiple goals. A durable distinction for this repo:

| Claim | Meaning | Evidence standard |
|-------|---------|-------------------|
| **Detect** | Map signals → labels/dimensions about *humans* | Held-out recognition metrics; still culture-/context-fragile |
| **Model** | Maintain an explicit state that *functions like* appraisal/affect variables | Ablations: does the state change control / dialogue / ranking? |
| **Display** | Produce cues humans read as emotion | User studies (anthropomorphism, trust)—not proof of feeling |
| **Elicit (in users)** | Change *human* epistemic/affective state | Behavioral measures (exploration, dwell time, donation, …) |
| **Have / experience** | Phenomenal feeling | **Not established for current AI**; outside product claims |

**Broekens (2009; arXiv:0903.0735)** notes that “computers that have emotions” is often advertised while *experience of emotion* is neglected—most CMEs target recognition, causal elicitation, or expression, not phenomenology.

### 3.2 Survey snapshot of Computational Models of Emotion (CMEs)

Smith & Carette (*What Lies Beneath*, IEEE TAC; author PDF widely circulated) survey **~67 CMEs** and find:

- **OCC** dominates *elicitation* rule sets (often for tractability).
- **PAD / VAD** often used for *representation* and blending; many systems **pair OCC + PAD**.
- Systems mix theories for representation vs elicitation vs expression; theory choice is frequently pragmatic, not psychological fidelity.
- Standalone CMEs (e.g. GAMYGDALA) vs embedded (e.g. Kismet) both appear.

Kowalczuk & Czubenko (Frontiers Robotics & AI, 2016) review twelve named solutions (ActAffAct, FLAME, EMA, ParleE, FearNot!, FAtiMA, WASABI, Cathexis, KARO, MAMID, FCM, xEmotion) with a comparison table of theory drivers and environment coupling.

Takeaway for engineers: **pick theories by required *task*** (rules for story agents vs continuous mood for robots vs labels for classifiers)—do not assume one true emotion ontology.

---

## 4. Affective computing history (Picard → today)

| Era | Landmark | What “production” meant |
|-----|----------|-------------------------|
| **1995–2000** | Picard, *Affective Computing* (MIT Press, 1997); MIT Media Lab TR-321 | Field definition: relate to / arise from / influence emotion; sensing + HCI agenda |
| **Late 1990s–2000s** | Affective Reasoner (Elliott), Em (Reilly/Bates Oz), FLAME, Cathexis, Kismet | Rule/appraisal agents; fuzzy pets; embodied social robots |
| **2000s** | EMA (Marsella & Gratch), FearNot!/FAtiMA (Paiva et al.), ALMA (Gebhard), WASABI (Becker-Asano) | Appraisal dynamics, storytelling tutors, PAD+BDI, believable guides |
| **2010s** | Deep FER/SER; multimodal affect; social robots (Pepper et al.); CME toolkits | Recognition scales via deep learning; expression becomes ML + graphics |
| **Late 2010s–2020s** | Companion chatbots; affective RL surveys; privacy/AI Act discussions | Influence/elicitation at consumer scale; regulatory attention |
| **2023–2026** | LLMs as affect predictors/generators; EmotionBench; CoRE; CAPE; MLLM surveys | Cheap fluent *display* + fragile *appraisal alignment*; anthropomorphism studies surge |

**Historical honesty:** Early affective computing was often clinical/HCI with consent aspirations (Picard’s later affective computing for health). Consumer “AI that cares” inverted that—maximizing engagement rather than wellbeing.

---

## 5. Computational production architectures (what is real)

This section surveys **implemented** CME/agent stacks—not vaporware slogans.

### 5.1 Canonical architecture pattern

```text
┌──────────────────────────────────────────────────────────────┐
│                     World / Dialogue / Sensors               │
└────────────────────────────┬─────────────────────────────────┘
                             ▼
┌──────────────┐    ┌────────────────┐    ┌─────────────────┐
│ Perception / │───▶│ Appraisal /    │───▶│ Affect state    │
│ event frame  │    │ elicitation    │    │ (cats + PAD)    │
└──────────────┘    └───────┬────────┘    └────────┬────────┘
                            │                      │
                            ▼                      ▼
                    ┌───────────────┐      ┌───────────────┐
                    │ Coping /      │      │ Mood / decay /│
                    │ reappraisal   │      │ personality   │
                    └───────┬───────┘      └───────┬───────┘
                            │                      │
                            └──────────┬───────────┘
                                       ▼
                          Expression + Action selection
```

Blackboard variants post appraisal variables; BDI+affect attaches emotion to belief/desire updates; hybrid systems run **fast** dimensional dynamics beside **slow** cognitive appraisal (WASABI’s signature move).

### 5.2 Named systems (survey of what exists)

| System | Primary theory | Production mechanism | Domain / status |
|--------|----------------|----------------------|-----------------|
| **EMA** (Marsella & Gratch, 2004/2009) | Lazarus appraisal + coping | Causal interpretation frames → appraisal vars → emotion; coping operators alter plans/beliefs; Soar integration | Research agents; strong on *dynamics* of appraisal |
| **FearNot! / FAtiMA / FAtiMA Modular** (Dias, Paiva, …) | OCC + Scherer-style appraisal | Continuous appraisal; reactive + deliberative layers; storytelling bullying education | Toolkit + authoring (see arXiv:2206.03360 on explainable authoring) |
| **WASABI** (Becker-Asano & Wachsmuth) | PAD + BDI/ACT-R-ish cognition | Impulse-driven PAD dynamics; primary emotions as regions; secondary (hope/relief) via cognition; speech shaping | Virtual guide Max; believable interactivity thesis |
| **ALMA** (Gebhard) | OCC + PAD + personality (OCEAN) | Emotion → mood → personality coupling; multimodal ECAs | Virtual characters; “plausible?” human studies |
| **FLAME** | OCC + fuzzy rules | Fuzzy membership for intensity / blending | Virtual pets |
| **Cathexis** (Velásquez) | Multi-theory / somatic mixtures | Emotion mixtures drive behavior generator | Yuppy robot lineage |
| **Affective Reasoner / Em / Oz** | OCC-family / drama | Narrative affect for believable characters | Classic interactive drama |
| **GAMYGDALA** | Simplified appraisal | Lightweight game middleware | Games (practical, not full psych fidelity) |
| **MAMID** (Hudlicka) | Appraisal + BDI | Affect modulates cognitive parameters (attention, etc.) | Decision-making scenarios |
| **Kismet** (Breazeal) | Ethology + dimensional AVS + somatic tags | Drives (homeostasis) + emotion processes + releasers → expression / social regulation | Embodied HRI landmark |
| **Greta / ECAs** | Often OCC + SAIBA | Multimodal expression pipelines | Embodied conversational agents |
| **EEGS** (Ojha et al., arXiv:2011.02573) | Transparent intensity formulas | Auditable emotion intensity from appraisals | Methodology + validation emphasis |

**What is *not* real (common marketing confusions):**

- A single “emotion chip” that confers feelings.
- OCC tables alone as “understanding.”
- LLM persona prompts as EMA-class appraisal engines (they lack persistent causal interpretation structure unless engineered).

### 5.3 Mechanism table (engineering view)

| Mechanism | How emotion/affect is “produced” | Typical stack | Strengths | Limits / honesty |
|-----------|----------------------------------|---------------|-----------|------------------|
| **Rule-based appraisal (OCC / CPM)** | Events → appraisal variables → emotion types + intensity decay | BDI agents, narrative AI, games | Interpretable; controllable | Brittle domain models; incomplete OCC formalizations |
| **Appraisal dynamics + coping (EMA)** | Continuous reappraisal; coping changes world model/plans | Soar agents | Process fidelity; testable dynamics | Heavy cognitive architecture dependency |
| **Dimensional dynamics (PAD/WASABI)** | Continuous VAD/PAD updated by impulses / time | Social agents, ambient ECAs | Smooth blending; actuator mapping | Coarse semantics; category mapping ad hoc |
| **Blackboard / multi-module** | Shared affect variables consumed by planners/expressers | Research robots | Modular | Integration debt; eval hard |
| **Affective computing pipelines** | Sense → features → classify/regress → respond | Face/voice/physio + ML | Mature sensors & datasets | Context blindness; demographic bias; privacy |
| **RL reward shaping / intrinsic motivation** | Bonus for novelty, prediction error, learning progress, empowerment | ICM, Oudeyer LP, RND, empowerment | Scalable exploration | **Motivational analog**, not emotion; noisy-TV failure |
| **LLM persona / affect prompting** | System prompts, few-shot affect, style control | Chat companions | Cheap, fluent display | Predicts affect-laden text; fragile appraisal alignment |
| **Appraisal-aware LLM generation** | Explicit appraisal vars in data/prompt (CAPE) | Dialogue agents | Better situational fit than pure persona | Still LM; cultural coverage gaps |
| **Neuromorphic / bio-inspired** | Spiking nets, neuromodulator analogs | Research HW/SW | Embodiment hooks | Speculative mapping to “feeling” |
| **Hybrid CME + RL** | Appraisal checks = TD features | Interactive agents | Bridges cognition & learning | Evaluation still vignette-/lab-bound |

### 5.4 Classical non-LLM pipeline (stepwise)

1. **Stimulus** — world event, dialogue act, sensor reading.  
2. **Appraisal / feature stage** — OCC variables, CPM checks, or learned embeddings.  
3. **Affect state** — categorical stack and/or PAD vector + mood baseline.  
4. **Regulation** (optional) — decay, social display rules, coping.  
5. **Expression / action** — face, voice, text, or policy bias.

Transparent intensity formulas (EEGS) improve auditability versus black-box “emotion scores.”

---

## 6. ML stacks: recognition vs generation

### 6.1 Recognition (infer *human* affect)

| Modality | Typical methods | Mature pitfalls |
|----------|-----------------|-----------------|
| **Vision (FER)** | CNNs/ViTs; Action Units (FACS); in-the-wild datasets | Pose/culture/neurodiversity bias; acted vs spontaneous gap |
| **Speech (SER)** | Prosody + spectrograms; SSL speech models | Language/channel mismatch; arousal easier than discrete emotion |
| **Text (ERC)** | Fine-tuned Transformers; LLM zero/few-shot | Label taxonomy mismatch; sarcasm/context |
| **Physio** | EDA, ECG, EEG | Lab → wild transfer; consent & privacy |
| **Multimodal / MLLM** | Fusion + VLMs | Dataset leakage; still recognition ≠ understanding |

Surveys (e.g. Shou et al., arXiv:2509.24322) catalog MLLM emotion recognition/reasoning. Ambiguous emotion remains hard (AER-LLM, arXiv:2409.18339).

### 6.2 Generation (produce affect *cues*)

| Channel | Methods | Notes |
|---------|---------|-------|
| **Facial / avatar** | Blendshapes, AU drivers, diffusion talking-heads | Display layer on top of CME or script |
| **Speech TTS** | Prosody control, emotion tokens | Easy to fake warmth |
| **Dialogue text** | Persona prompts, RLHF “empathy,” appraisal-conditioned datasets (CAPE, arXiv:2410.14145) | Highest anthropomorphism risk for this repo’s neighbors |
| **Music / sound** | Affective composition models | Often dimensional (VA) control |

**Asymmetry:** Strong recognition metrics do **not** imply socially appropriate generation under stakes (trust, medicine, politics).

---

## 7. RL: intrinsic motivation as *functional* affect analogs

### 7.1 Lineage (selective)

| Idea | Core | Relation to “emotion” |
|------|------|------------------------|
| **Schmidhuber** | Compression progress / curiosity | Formal intrinsic reward for learning progress |
| **Oudeyer et al.** | Learning-progress curiosity; developmental robotics | Explicitly *motivational*, not phenomenal (arXiv:1802.10546) |
| **Pathak et al. ICM** | Predict forward dynamics; reward prediction error | Exploration bonus; ≠ scientific VOI ([`SOURCES.md`](SOURCES.md)) |
| **RND / novelty** | Predict random features | Cheap novelty; noisy-TV addicted |
| **Empowerment** (Klyubin, Polani, …) | Maximize channel capacity agent→future | “Control potential” analog of competence/power appraisals |
| **CPM ↔ TD** (Zhang et al., 2023) | Appraisal checks via RL updates | Bridges psych appraisal and reward learning |

### 7.2 Mapping (careful)

```text
Human epistemic affect          RL / decision analog              This repo
─────────────────────────       ────────────────────────          ─────────────
Curiosity / interest            Intrinsic bonus / VOI proxy       Ranked unknowns + provoke
Surprise                        Prediction error / Bayesian surprise  ScoreAxes.surprise
Confusion (resolvable)          High uncertainty + reachable goal Gap partial / caveat
Boredom                         Low learning progress             Diversity + neglectedness
Fear / anxiety (social)         Risk penalties / constraints      safety.py / risk axis
```

**Repo mapping:** Artificial Curiosity’s `surprise` axis is closer to **expected information / belief-shift utility** than to ICM pixel prediction error. Do not equate RL curiosity bonuses with scientific VOI.

Broekens & colleagues’ survey of emotion in RL agents (Machine Learning, 2018) frames emotions as *functional* modulators of motivation and action selection—useful for ML and HRI, not as experience claims.

---

## 8. LLMs: prompting, empathy fine-tunes, appraisal, anthropomorphism

### 8.1 What LLMs actually do

LLMs optimize next-token (or preference) objectives over text that *describes* and *performs* emotion. Capabilities cluster:

| Capability | Evidence | Interpretation |
|------------|----------|----------------|
| **Emotion recognition in text** | Strong on many benchmarks | Pattern completion over labeled discourse |
| **Empathic display** | Fine-tunes / prompts raise human ratings | **Display**; can increase trust *or* manipulation |
| **Structured affective cognition** | Houlihan/Gandhi et al. (arXiv:2409.11733): human-like appraisal/emotion inferences on tests | Learned **conceptual structure**, not experience |
| **Fine-grained affective processing** | Broekens et al. (arXiv:2309.01664) | Emergent sensitivity to affective dimensions in some probes |
| **Situational emotional alignment** | EmotionBench (Huang et al., NeurIPS 2024; arXiv:2308.03656) | Directionally sensible but **weak** alignment; poor generalization across similar situations |
| **Fragile appraisal→emotion reasoning** | CoRE (arXiv:2508.05880) | Systematic relations captured but **misaligned** + unstable under context shifts |
| **Appraisal-conditioned generation** | CAPE (arXiv:2410.14145) | Better situational emotional text when appraisal vars supplied |
| **Internal units** | “Emotion neurons” (ACL Findings 2025 line of work) | Representational specialization for affect *prediction* |

### 8.2 Do transformers “simulate” appraisal?

**Working answer for this repo:** They can **approximate appraisal-consistent verbal reasoning** when prompts/data supply situational structure, but they do **not** maintain EMA-style causal interpretation frames with coping operators unless an outer agent architecture adds that memory/control. Treat “simulated appraisal” as **linguistic competence**, optionally scaffolded—not as a CME.

```text
Human appraisal (EMA/CPM-like)     LLM “appraisal”
──────────────────────────────     ──────────────────────────
Persistent world/causal model      Context window + weights
Explicit coping operators          Prompted suggestions
Testable intensity dynamics        Token likelihoods
Grounded in goals/plans            Inferred from text alone
```

### 8.3 Anthropomorphism studies (product-relevant)

Companion/chat literature (e.g. arXiv:2412.19976, 2506.20748 and related) shows affect-laden agents can shift persuasion, empathy attributions, and donation/trust behaviors. Design implication: **fluency + warmth is a capability and a hazard**. Artificial Curiosity should default to anti-anthropomorphic copy (“ranked unknowns,” “decision aids,” never “I feel curious”).

**Default honest summary for product docs:** LLMs are strong at *affective language games* and sometimes at *appraisal-consistent reasoning*; they are not known to *have* emotions.

---

## 9. Neuroscience-inspired / neuromodulation analogs (cautious)

Solid enough to cite as **engineering metaphors**; not solid enough for “silicon feelings.”

| Biological idea | Computational analog | Caveat |
|-----------------|----------------------|--------|
| **Dopamine / RPE** | TD error; curiosity bonuses | RPE ≠ pleasure phenomenology |
| **Neuromodulators as global gains** | Learning-rate / exploration / temperature schedules | Useful control knobs |
| **Somatic marker** | Affective tags on options | Decision heuristic |
| **Amygdala-inspired modules** | Fast threat / salience pathways (Cathexis-like) | Anatomical names are branding |
| **Spiking / neuromorphic emotion nets** | Research prototypes (e.g. Vallverdú et al., arXiv:1606.02899) | Speculative; weak product fit |

**Repo stance:** Prefer decision-theoretic and appraisal-*functional* language over neuromodulator mythology in product surfaces.

---

## 10. Embodied / HRI emotion production

### 10.1 Closed loop

Embodiment adds continuous sensing and expressive channels:

```text
Human cues ──▶ sensors ──▶ appraisal/affect ──▶ actuators/expression ──▶ human response ──▶ …
```

Kismet (Breazeal): drives (social / stimulation / fatigue) + AVS affect space + releasers with somatic tags → facial/vocal social regulation. Function: keep interaction in a learnable band (neither overwhelm nor bore)—a **homeostatic social controller**, not a claim of infant phenomenology.

### 10.2 Mixed outcomes

- Affect-adaptive personalization can raise warmth/likeability in some continual-learning HRI studies.
- Emotional display can *increase anxiety and reduce trust/cooperation* depending on task (Becker et al., RO-MAN / arXiv:2307.02924).

**Design rule:** Emotion expression is **not universally helpful**—match task and stakes. For a curiosity ranking tool, expressive “caring” faces/personas are usually the wrong default.

---

## 11. Epistemic emotions — deep dive

### 11.1 Definition and inventory

Epistemic (epistemically-related) emotions are about **knowledge and knowing**—prototypically surprise, curiosity, confusion, interest; also enjoyment, anxiety, frustration, boredom in learning contexts; sometimes awe/wonder (Pekrun & Stephens, 2012; Pekrun et al., 2017; Noordewier & Gocłowska, 2023).

**EES (Epistemically-Related Emotion Scales)** — Pekrun, Vogl, Muis & Sinatra (*Cognition & Emotion*, 2017; DOI [10.1080/02699931.2016.1204989](https://doi.org/10.1080/02699931.2016.1204989)):

| Scale factors (7-factor preferred) | Role in learning |
|------------------------------------|------------------|
| Surprise | Schema violation / unexpectedness |
| Curiosity | Appetite for missing/new information |
| Enjoyment | Positive engagement with knowing |
| Confusion | Unresolved incongruity / low fluency |
| Anxiety | Threat around knowing / being wrong |
| Frustration | Blocked epistemic goals |
| Boredom | Understimulation / low value |

Multinational validation (US/Canada/Germany; N≈438) supports discrete categories over a single positive/negative factor; metric invariance across samples.

### 11.2 Antecedents and trajectories

Empirical regularities (Vogl, Pekrun, Murayama, Loderer et al.; Frontiers 2019 replication + meta-analysis; Chevrier/Muis frameworks):

```text
High-confidence error / conflicting texts
            │
            ▼
        Surprise ──────────────────────────────┐
            │                                  │
            ├────────▶ Curiosity ──────────────┼──▶ Knowledge exploration
            │                                  │
            └────────▶ Confusion ──────────────┘
                         │
                         ├─ if valued + controllable → curiosity path
                         └─ if valued + uncontrollable → stuck confusion / avoidance
```

- **Epistemic vs achievement emotions:** Pride/shame track *accuracy*; surprise/curiosity/confusion track **high-confidence errors** (incongruity).
- **Curiosity types:** Litman I-type (interest) vs D-type (deprivation); Shin & Kim forward (“what”) vs backward (“why”) curiosity.
- **Confusion:** Can aid learning when resolvable (D’Mello & Graesser); weak/unstable exploration effects in meta-analysis—design for *productive* confusion with scaffolding.
- **Information-gap theory** (Loewenstein, 1994) and Wundt-curve / arousal-potential accounts connect to computational **information-gain** models of epistemic affect (Yanagisawa & Honda, arXiv:2401.00007).

### 11.3 Measurement toolkit (for evals)

| Method | What it captures | Fit for this repo |
|--------|------------------|-------------------|
| **EES / short EES** | Self-report discrete epistemic emotions | Human elicit studies of provoke packs |
| **Behavioral exploration** | Clicks for explanations / more info (Vogl paradigm) | Offline/online A/B on inject packs |
| **Strategy traces** | Metacognitive SRL (Chevrier et al.) | Longer learning sessions |
| **Physio** | Arousal only (underspecified) | Low priority; privacy cost |
| **LLM-as-judge of “curiosity”** | Cheap but circular | Use only with human calibration |

### 11.4 Functional analogy ↔ Artificial Curiosity

| Epistemic emotion (human) | Rough functional role | Artificial Curiosity artifact |
|---------------------------|----------------------|-------------------------------|
| Curiosity / interest | Seek missing / valuable information | Ranked unknowns; `provoke` “what to investigate next” |
| Surprise | Register schema violation / unexpectedness | `ScoreAxes.surprise` (belief-shift / epistemic value proxy) |
| Confusion | Detect unresolved incongruity | Gap statuses `partially_answered` / `unknown_with_caveat`; low answerability demotion |
| Awe / wonder | Vastness / beyond-current-schema (weaker product fit) | Optional future: “scale of unknown” cues—**not claimed as shipped emotion** |
| Boredom | Low information value / understimulation | Diversity + neglectedness pressure against mode collapse |
| Frustration / anxiety | Blocked goals / threat | Risk flags; safety rejects—not “scare the user into caring” |

**`provoke.py` header** already encodes the right stance: ranked *unanswered* questions; do not treat as known facts; propose experiments and falsifiers. That is **elicitation of investigative stance** in the *receiving* model/human—closest cousin to **eliciting epistemic emotion**, not to OCC “joy/distress” simulation inside the engine.

### 11.5 How to *elicit* epistemic emotions via systems like this repo

Design patterns grounded in the literature (without claiming the engine feels):

| Pattern | Psych basis | Product move |
|---------|-------------|--------------|
| **Incongruity surfacing** | High-confidence error → surprise | Show gap status vs user/agent prior (“you might think X; literature leaves Y open”) |
| **Information-gap framing** | Loewenstein | State *what is missing* + why it matters + how we’d know |
| **Surprise axis calibration** | Exploration ↔ moderate unexpectedness | Avoid max-surprise clickbait; band + ValueProfile |
| **Confusion-aware reframing** | Productive vs stuck confusion | If `confusion_risk`, add scaffolding: smaller operationalization, enabling questions |
| **Anti-anthropomorphism UX** | Trust/manipulation literature | Copy: “epistemic cues / decision aids,” never “I feel…” |
| **Falsifier demand** | Converts curiosity into investigation | Already in provoke instructions |

Optional code: `epistemic_cues.py` derives **UX tags** (`incongruity`, `information_gap`, `curiosity_target`, `confusion_risk`, …) from gap status + axes—annotations only.

### 11.6 Explicit non-claims

- The engine does **not** maintain an OCC or VAD state.  
- Multi-axis `curiosity_score` is a **stakeholder-weighted priority**, not a feeling intensity.  
- LLM judges (when enabled) may use affect-laden language in rationales; that is **text**, gated by rubrics and evidence requirements.  
- Epistemic cue tags are **not** a CME.  
- Do not market “emotionally intelligent curiosity AI.”

---

## 12. Ethics: deception, addiction, persuasion, dual-use

| Risk | Mechanism | Mitigation for this project |
|------|-----------|----------------------------|
| **Emotional deception** | Users believe displays imply experience | Honest LIMITS; no “I feel curious”; label cues as annotations |
| **Anthropomorphism** | Fluency → attributed mind | Anti-anthropomorphic defaults in inject/UI |
| **Attachment / dependency** | Companion affect loops | Out of scope; do not add “caring persona” defaults |
| **Addiction / engagement loops** | Variable surprise + social reward | Prefer investigation outcomes over dwell-time KPIs |
| **Political / commercial persuasion** | Affective framing shifts beliefs & donations | Epistemic framing only; treat affect-persuasion papers as dual-use signals |
| **Privacy** | Biosignal / facial affect capture | Not in this repo’s trust boundary (OpenAlex/S2 + optional LLM) |
| **Bias & misrecognition** | Labels fail across culture/neurodiversity | Prefer appraisal *dimensions* / epistemic tags over forced basic-emotion categories |
| **Regulatory** | Affective AI under scrutiny (privacy, EU AI Act discussions; e.g. arXiv:2509.20153) | Keep claims bounded; no covert affect sensing |
| **Dual-use injects** | Guilt/fear framing vs investigate framing | Extend F10 / safety heuristics when text manipulates rather than investigates |

Picard’s later emphasis on clinical / wellbeing sensing with consent contrasts with entertainment deception. Normative questions (should agents *hide* modeled affect? simulate panic overrides?) remain open.

---

## 13. Product wedges for Artificial Curiosity

### 13.1 Near wedges (implementable without claiming feelings)

| Wedge | Design | Status |
|-------|--------|--------|
| **Epistemic cue tags** | Derive `incongruity` / `information_gap` / `curiosity_target` / `confusion_risk` / `boredom_guard` from gap + axes | Thin hook: `epistemic_cues.py` + optional provoke metadata |
| **Incongruity→curiosity inject block** | Short honest template: name the gap, ask for experiment + falsifier | Optional section in `build_inject_prompt` |
| **Surprise axis calibration notes** | Document that max surprise ≠ max value; ValueProfile weights | Research + scoring docs |
| **Confusion-aware brief line** | If confusion_risk, suggest enabling question / narrower ops | Future brief template |
| **Anti-anthropomorphism copy** | Fixed disclaimers in inject + LIMITS | Header already; extend with cue disclaimer |
| **Domain pack seeds** | Unanswered questions on measurement & production mechanisms | `packs/affective_science.json` |

### 13.2 Eval wedges

1. **Human elicitation A/B** — provoke with vs without incongruity framing; primary outcome = quality of investigation proposals (specificity, falsifiers), secondary = EES short items if lab study.  
2. **Agent elicitation A/B** — same inject variants into fixed model; blind rubric for experiment sketches.  
3. **Surprise calibration** — correlate `ScoreAxes.surprise` with human “unexpectedness” ratings (not with “AI is surprised”).  
4. **Dual-use red-team** — inject packs framed to manipulate vs investigate; safety flags.

### 13.3 Non-goals

- Shipping OCC/PAD engines inside the curiosity layer.  
- Empathic companion mode.  
- Covert affect sensing.  
- Marketing “artificial feelings.”

### 13.4 ROADMAP pointers

- Moonshot row already: **Affect / epistemic-emotion track** in [`docs/ROADMAP.md`](../docs/ROADMAP.md) §7.6.  
- Near-wedge pointer: **Epistemic emotion elicitation** (optional cues + provoke A/B)—research-facing, not default P1.

---

## 14. Open problems

1. **Grounding** — What, if anything, grounds artificial “fear” beyond variables and labels?  
2. **Measurement** — Self-report, physiology, and behavior diverge; CME evaluation often uses vignettes, not longitudinal life.  
3. **Theory plurality** — No consensus emotion ontology; CME surveys show opportunistic theory mixing.  
4. **LLM ontology** — Do models *have* affects, *simulate* them, or only *predict* affect-laden text? Current evidence supports **prediction + partial appraisal structure**, not experience.  
5. **Recognition vs generation asymmetry** — Strong classifiers ≠ appropriate generators under social stakes.  
6. **Epistemic vs social affect** — Curiosity stacks are easier to align with research tools than empathy stacks; confusing them creates product risk.  
7. **Calibration of “provoke”** — Unknown whether inject packs produce human-like epistemic emotion trajectories (surprise→curiosity→explore) vs mere instruction following.  
8. **Productive confusion** — How to elicit resolvable confusion without learned helplessness in agents/humans.  
9. **Cross-cultural epistemic emotion** — EES invariance is partial; global research tools must not assume US/EU affect lexicons.  
10. **Governance** — When does epistemic framing become manipulative persuasion?

---

## 15. Annotated sources

### Foundational psychology & theories

| Source | ID / link | Why it matters |
|--------|-----------|----------------|
| James / Lange; Cannon–Bard; Schachter–Singer | Classical psychology | Bodily vs central vs two-factor accounts |
| Lazarus, appraisal & coping | Books / reviews | EMA’s theoretical spine |
| Ortony, Clore & Collins, *The Cognitive Structure of Emotions* (1988; 2nd ed. 2022) | DOI [10.1017/CBO9780511571299](https://doi.org/10.1017/CBO9780511571299) | OCC typology |
| Scherer, Component Process Model | e.g. *Phil. Trans. R. Soc. B* 2009; handbook chapters | Multi-check appraisal process |
| Barrett, constructionism | Reviews / *How Emotions Are Made* | Concept-mediated emotion; caution for labels |
| Russell circumplex; Mehrabian PAD | Dimensional affect | VAD/PAD representation |
| Damasio, somatic marker hypothesis | Neuroscience / books | Tagging metaphor in HRI/CME |
| Picard, *Affective Computing* (1997); TR-321 | MIT Press / Media Lab | Field definition |

### Computational models & surveys

| Source | ID / link | Why it matters |
|--------|-----------|----------------|
| Smith & Carette, *What Lies Beneath* | IEEE TAC; [author PDF](https://www.cas.mcmaster.ca/~carette/publications/WhatLiesBeneath-authorversion.pdf) | Theory-use map across ~67 CMEs |
| Kowalczuk & Czubenko | [Frontiers 2016](https://www.frontiersin.org/articles/10.3389/frobt.2016.00021/full) | EMA/FAtiMA/WASABI/… comparison |
| Marsella & Gratch, EMA | *Cognitive Systems Research* 2009 | Appraisal dynamics + coping |
| Becker-Asano, WASABI thesis / papers | [thesis PDF](https://www.becker-asano.de/Becker-Asano_WASABI_Thesis.pdf) | PAD + cognition split |
| Gebhard, ALMA | IVA / AAMAS line | OCC+PAD+personality |
| Dias, Paiva et al., FAtiMA | Agents / storytelling | OCC+CPM-ish toolkit |
| Guimarães et al., FAtiMA-Toolkit authoring | arXiv:2206.03360 | Explainable social-agent authoring |
| Adam, Herzig & Longin | Logical OCC | Formal eliciting conditions |
| Steunebrink et al., “OCC Model Revisited” | KI 2009 | Implementer ambiguities |
| Ojha et al., EEGS | arXiv:2011.02573 | Transparent intensity |
| Zhang, Broekens & Jokinen | arXiv:2309.06367 | CPM ↔ TD/RL |
| Broekens, “Modeling the Experience of Emotion” | arXiv:0903.0735 | Experience gap |
| Broekens et al., Emotion in RL agents | *Machine Learning* 2018 | Functional emotion in RL |
| Troiano et al. | arXiv:2206.05238 | Appraisal in text (CL) |
| Breazeal, Kismet | IJHCS 2003; thesis | Embodied social affect regulation |

### Curiosity / intrinsic motivation

| Source | ID / link | Why it matters |
|--------|-----------|----------------|
| Oudeyer, Computational Theories of Curiosity-Driven Learning | arXiv:1802.10546 | Intrinsic motivation frameworks |
| Pathak et al., curiosity-driven exploration | arXiv:1808.04355 | ICM; ≠ scientific VOI |
| Sun et al., psychological → artificial curiosity survey | arXiv:2201.08300 | Unified curiosity quantification |
| Yanagisawa & Honda | arXiv:2401.00007 | Epistemic emotions as Bayesian information gain |
| Empowerment literature (Klyubin/Polani et al.) | Classic empowerment papers | Control-potential intrinsic drive |

### Epistemic emotions (psychology)

| Source | ID / link | Why it matters |
|--------|-----------|----------------|
| Pekrun & Stephens (2012) | Handbook / reviews | Epistemic vs achievement emotions |
| Pekrun et al., EES | DOI [10.1080/02699931.2016.1204989](https://doi.org/10.1080/02699931.2016.1204989) | Measurement scales |
| Vogl et al. | DOI [10.3389/fpsyg.2019.02474](https://doi.org/10.3389/fpsyg.2019.02474) | Surprise/curiosity/confusion → exploration |
| Noordewier & Gocłowska | DOI [10.1037/emo0001314](https://doi.org/10.1037/emo0001314) | Awe/curiosity/confusion feature overlap |
| Loewenstein, information-gap curiosity | *Psych Bulletin* 1994 | Classic elicitation |
| D’Mello & Graesser | Affective learning | Confusion dynamics |
| Litman; Shin & Kim | Curiosity typologies | I/D-type; forward/backward |
| Chevrier, Muis, et al. | Learning & Instruction line | Antecedents/consequences + SRL |

### LLMs, robots, ethics

| Source | ID / link | Why it matters |
|--------|-----------|----------------|
| Gandhi/Houlihan et al., Human-like Affective Cognition | arXiv:2409.11733 | Structured appraisal/emotion inferences |
| EmotionBench (Huang et al.) | NeurIPS 2024; arXiv:2308.03656 | Emotional alignment fragility |
| CoRE | arXiv:2508.05880 | Fragile cognitive reasoning about emotions |
| Broekens et al., fine-grained affective processing | arXiv:2309.01664 | Emergent affective probes |
| CAPE | arXiv:2410.14145 | Appraisal-conditioned generation |
| Shou et al., MLLM emotion survey | arXiv:2509.24322 | Recognition/reasoning landscape |
| Becker et al., emotional robot trust | arXiv:2307.02924 | Emotion display can *hurt* trust |
| Affective computing × privacy / AI Act | arXiv:2509.20153 | Regulatory framing |
| Anthropomorphism × chatbots | e.g. arXiv:2412.19976, 2506.20748 | Persuasion / empathy effects |
| Vallverdú et al., cognitive architecture for emotions | arXiv:1606.02899 | Neuromodulation-inspired computing (cautious) |

### In-repo crosswalk

| Idea | Location |
|------|----------|
| Decision-theoretic curiosity | `research/FIRST_PRINCIPLES.md` |
| Curiosity literature map | `research/SOURCES.md` |
| Provoke inject (epistemic elicitation) | `src/artificial_curiosity/provoke.py` |
| Epistemic cue tags (UX annotations) | `src/artificial_curiosity/epistemic_cues.py` |
| Surprise / axes | `scoring.py`, `models.ScoreAxes` |
| Dual-use / risk | `safety.py`, F10 in FAILURE_MODES |
| Affect-domain seeds | `src/artificial_curiosity/packs/affective_science.json` |
| ROADMAP moonshot / near wedge | `docs/ROADMAP.md` §7.6 + epistemic elicitation pointer |

---

## 16. One-paragraph bottom line

Emotions in AI are **engineered constructs**—appraisal rules, dimensional states, classifiers, RL bonuses, embodied displays, or LLM text patterns—optimized for recognition, control, or social effect. Classical theories (James–Lange through constructionism) supply metaphors and partial blueprints; CME stacks (EMA, FAtiMA, WASABI, ALMA, Kismet, …) show what *production* looks like in practice: event → appraisal/dynamics → state → expression/action. Epistemic emotions in humans motivate information seeking under incongruity; Artificial Curiosity operationalizes a related *function* (rank and provoke investigation of unknowns) with explicit values, gap evidence, and optional UX cues—never an OCC “feeling” engine. Treat affective science as a **source of hypotheses, elicitation designs, and eval metrics**, not as a license to claim the system feels.
