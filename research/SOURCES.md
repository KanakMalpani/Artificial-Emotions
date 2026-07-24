# Annotated Sources

All research for Artificial Curiosity lives in this repo under `research/`.
Primary synthesis: `RESEARCH.md`. Design basis: `FIRST_PRINCIPLES.md`. Product docs: `docs/`.

## Academic / preprint

| Work | URL | Used for |
|------|-----|----------|
| HybridQuestion (Zhao et al., 2025) | https://arxiv.org/html/2602.03849 | AI vs human divergence on *future* questions |
| SciMuse (Gu & Krenn) | https://arxiv.org/html/2405.17044v3 | Idea generation + interest prediction at scale |
| AutoDiscovery / Bayesian surprise | NeurIPS 2025 (AutoDS) | Surprisal > diversity for open-ended discovery |
| MIRAI | https://arxiv.org/html/2606.05443 | Impact prediction from title/abstract |
| Idea-Catalyst | https://www.arxiv.org/pdf/2603.12226 | Decompose → unresolved → cross-domain rank |
| ResearchBench | ACL findings 2026 | Inspiration / hypothesis / ranking decomposition |
| Jr. AI Scientist | arXiv 2511.04583 | Autonomous research risks & limits |
| Agentic AI Scientists Are Not Built For ASD | arXiv 2605.08956 | Problem-selection bottleneck / McNamara fallacy |
| Computational Theories of Curiosity (Oudeyer) | arXiv 1802.10546 | Intrinsic motivation foundations |
| Large-Scale Curiosity-Driven Learning (Pathak et al.) | arXiv 1808.04355 | RL curiosity ≠ scientific VOI |
| Emotions in AI / epistemic affect (synthesis) | [`AI_EMOTIONS.md`](AI_EMOTIONS.md) | Monograph: classical theories, CME architectures, ML/RL/LLM stacks, epistemic elicitation ↔ provoke |
| Consumer access to emotion / epistemic tooling | [`EMOTION_ACCESS.md`](EMOTION_ACCESS.md) | APIs, SDKs, OCC libs, LLM toolkits, EES, datasets (easy vs locked); minimal public contract |
| Emotion mixing / blends (synthesis) | [`EMOTION_MIXING.md`](EMOTION_MIXING.md) | PAD interpolation, Plutchik dyads, mixed feelings; % mix schema + honesty limits |
| Watson & Stanton, Emotion blends | DOI 10.1177/1754073916639659 | Same-valence blends vs cross-valence mixed feelings |
| Marsella, Gratch & Petta, CME review | https://people.ict.usc.edu/~gratch/papers/MarGraPet_Review-old.pdf | PAD for continuous blend; appraisal vs dimensional |
| Plutchik psychoevolutionary theory / dyads | Plutchik 1980/2001 | Primary/secondary/tertiary dyads; intensity rings |
| Semeraro et al., PyPlutchik | DOI 10.1371/journal.pone.0256503 | Quantitative wheel + dyad visualization |
| Plutchik + MoE classification | ACL 2024.emnlp-main.50 | Dyad decomposition in NLP labeling |
| ISPOR VOI Task Force | https://eprints.whiterose.ac.uk/id/eprint/158024/ | EVPI / EVSI / ENBS research prioritization |
| Picard, Affective Computing (1997) | MIT Press / Media Lab TR-321 | Field definition: relate to / arise from / influence emotion |
| OCC — Ortony, Clore & Collins | DOI 10.1017/CBO9780511571299 | Appraisal typology used by most CMEs |
| Scherer Component Process Model | Phil. Trans. R. Soc. B / handbook chapters | Multi-check appraisal process |
| Smith & Carette, What Lies Beneath | IEEE TAC; McMaster author PDF | Survey of ~67 CMEs; OCC+PAD theory-use map |
| Kowalczuk & Czubenko, modeling artificial emotion | Frontiers Robotics & AI 2016 | EMA / FAtiMA / WASABI / FLAME comparison |
| Marsella & Gratch, EMA | Cognitive Systems Research 2009 | Appraisal dynamics + coping |
| Becker-Asano, WASABI | Thesis / AAMAS papers | PAD dynamics + BDI secondary emotions |
| Gebhard, ALMA | IVA / AAMAS line | OCC + PAD + personality for ECAs |
| FAtiMA / FAtiMA-Toolkit | Dias & Paiva; arXiv:2206.03360 | OCC+appraisal storytelling agents; authoring |
| Ojha et al., EEGS | arXiv:2011.02573 | Transparent emotion intensity formulas |
| Zhang, Broekens & Jokinen | arXiv:2309.06367 | CPM appraisal ↔ TD/RL |
| Broekens, Modeling Experience of Emotion | arXiv:0903.0735 | Phenomenology gap in affective computing |
| Broekens et al., Emotion in RL agents | Machine Learning 2018 | Functional emotion models in RL |
| Breazeal, Kismet | IJHCS 2003 | Embodied drives + AVS social affect |
| Pekrun et al., Epistemically-Related Emotion Scales | DOI 10.1080/02699931.2016.1204989 | EES measurement (surprise…boredom) |
| Vogl et al., surprise/curiosity/confusion → exploration | DOI 10.3389/fpsyg.2019.02474 | High-confidence errors; meta-analytic path |
| Loewenstein, information-gap curiosity | Psych Bulletin 1994 | Classic elicitation account |
| Yanagisawa & Honda | arXiv:2401.00007 | Epistemic emotions as Bayesian information gain |
| EmotionBench (Huang et al.) | NeurIPS 2024; arXiv:2308.03656 | LLM emotional alignment fragility |
| CoRE | arXiv:2508.05880 | Fragile appraisal→emotion reasoning in LLMs |
| Human-like Affective Cognition in FMs | arXiv:2409.11733 | Structured affective cognition probes |
| CAPE appraisal-based generation | arXiv:2410.14145 | Appraisal-conditioned emotional dialogue |
| Broekens et al., fine-grained affective LLMs | arXiv:2309.01664 | Emergent affective processing probes |
| Becker et al., emotional robot trust | arXiv:2307.02924 | Emotion display can reduce trust |
| Affective computing × privacy / AI Act | arXiv:2509.20153 | Regulatory / ethics framing |
| Hume AI Expression / EVI / TTS | https://dev.hume.ai/intro | Easy cloud expression + empathic voice access |
| Microsoft Face emotion attribute retirement | Azure Responsible AI blog (2022) | Platform lock / withdrawal of emotion inference |
| Py-Feat facial expression toolbox | https://py-feat.org/ ; arXiv:2104.03509 | Easy local open FER SDK |
| FAtiMA Toolkit | https://github.com/GAIPS/FAtiMA-Toolkit ; ACM 10.1145/3510822 | Accessible OCC socio-emotional agents (C#/Unity) |
| GAMYGDALA | https://github.com/broekens/gamygdala ; IEEE TAC 2014 | Easy MIT/JS game appraisal engine |
| EmotionBench | arXiv:2308.03656 ; CUHK-ARISE GitHub | LLM emotional alignment toolkit (research / NC) |
| CAREBench | arXiv:2605.17176 | Appraisal-reasoning chain eval for LLMs |
| CAPE appraisal corpus | NAACL Findings 2025 | Appraisal-conditioned emotional generation (ZH) |
| GoEmotions | google-research / HF Apache-2.0 | Easy open text emotion labels (incl. curiosity) |
| AffectNet / RAF-DB access policies | DU academic agreement; RAF university form | Locked in-the-wild face datasets |

### Consumer access patterns (summary)

| Pattern | Easy | Locked / hard | See |
|---------|------|---------------|-----|
| Cloud face/voice expression | Hume (key + SDK) | Azure emotion attrs retired; Affectiva enterprise | [`EMOTION_ACCESS.md`](EMOTION_ACCESS.md) §3.1 |
| Local FER | Py-Feat, OpenFace | Some model weights NC | §3.2 |
| OCC appraisal middleware | GAMYGDALA (JS), FAtiMA (C#) | Full EMA/Soar | §3.3 |
| LLM affect toolkits | HF classifiers, prompt JSON | EmotionBench NC; fragile alignment | §3.4 |
| Epistemic emotion (EES) | Scale items + behavior paradigms | No mass-market EES API | §3.5 |
| Datasets | GoEmotions | AffectNet, RAF-DB gated | §3.6 |
| This repo public contract | `/v1/emotions/*` + examples | Not a FER/OCC product | §5 |

## Products (contrast class — answer/search, not curiosity ranking)

| Product | URL | Gap vs this project |
|---------|-----|---------------------|
| Elicit | https://elicit.com/ | Answers / reviews given a question |
| Consensus | https://consensus.app/ | Literature consensus search |
| ResearchRabbit | https://www.researchrabbit.ai/ | Citation exploration |
| FutureHouse (Crow/Falcon/Owl/Robin) | https://www.futurehouse.org/ | Strong agents; Owl checks existence, not value-rank |
| Sakana AI Scientist | https://sakana.ai/ai-scientist-nature/ | End-to-end papers; weak upstream prioritization |

## How sources map into code

| Source idea | Code location |
|-------------|---------------|
| VOI / ITN axes | `scoring.py`, `models.ValueProfile` |
| Bayesian surprise proxy | `ScoreAxes.surprise` |
| Gap ≠ related neighborhood | `verify.py` (overlap-gated) |
| Human value judgment | `ValueProfile` required |
| Mode collapse / duplicates | `diversity.py` |
| Failure catalog | `research/FAILURE_MODES.md` + `tests/test_failure_modes.py` |
| Epistemic cue tags (UX only) | `epistemic_cues.py` + `provoke.py` |
| Emotions / epistemic public surface | `emotions.py`; `/v1/emotions/*` |
| Emotion access contract examples | `examples/emotions_*.json` |
| Affective-science seed pack | `packs/affective_science.json` |
