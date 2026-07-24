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
| Bisht et al. McNamara / hivemind (deep note) | [`PROBLEM_SELECTION_MCNAMARA.md`](PROBLEM_SELECTION_MCNAMARA.md) | Implications for profiles, diversity, ensembles |
| Computational Theories of Curiosity (Oudeyer) | arXiv 1802.10546 | Intrinsic motivation foundations |
| Large-Scale Curiosity-Driven Learning (Pathak et al.) | arXiv 1808.04355 | RL curiosity ≠ scientific VOI |
| Emotions in AI / epistemic affect (synthesis) | [`AI_EMOTIONS.md`](AI_EMOTIONS.md) | Monograph: classical theories, CME architectures, ML/RL/LLM stacks, epistemic elicitation ↔ provoke |
| Consumer access to emotion / epistemic tooling | [`EMOTION_ACCESS.md`](EMOTION_ACCESS.md) | APIs, SDKs, OCC libs, LLM toolkits, EES, datasets (easy vs locked); minimal public contract |
| Emotion mixing / blends (synthesis) | [`EMOTION_MIXING.md`](EMOTION_MIXING.md) | PAD interpolation, Plutchik dyads, mixed feelings; % mix schema + honesty limits |
| Epistemic elicitation → provoke | [`EPISTEMIC_ELICITATION.md`](EPISTEMIC_ELICITATION.md) | EES, incongruity paradigms, agent/human A/B protocol |
| Gap verify / question-rank competitors | [`GAP_VERIFICATION_COMPETITORS.md`](GAP_VERIFICATION_COMPETITORS.md) | SciMuse, ScholarEval, LitGapFinder, ResearchAgent, Owl-class |
| Affective tooling safety (public use) | [`AFFECTIVE_SAFETY.md`](AFFECTIVE_SAFETY.md) | AI Act ERS vs annotation; manipulation; design restraint |
| Agent plugin / MCP UX | [`AGENT_PLUGIN_UX.md`](AGENT_PLUGIN_UX.md) | Tool description hygiene; progressive disclosure; ScaleMCP |
| Approximate VOI / EVSI spike | [`VOI_APPROXIMATIONS.md`](VOI_APPROXIMATIONS.md) | ISPOR/ConVOI methods; worksheet vs fake EVSI |
| Preference calibration / LTR ladder | [`PREFERENCE_CALIBRATION.md`](PREFERENCE_CALIBRATION.md) | Pairwise prefs → profile weight hints → optional BT |
| Neglectedness ITN addendum | [`NEGLECTEDNESS_ITN.md`](NEGLECTEDNESS_ITN.md) | Importance×Tractability×Neglectedness honesty |
| Bayesian surprise / AutoDiscovery | [`BAYESIAN_SURPRISE.md`](BAYESIAN_SURPRISE.md) | Experimental surprisal ≠ lit surprise proxy |
| Dual-use ranking safety | [`DUAL_USE_RANKING.md`](DUAL_USE_RANKING.md) | Safeguarding AI scientists; Jr. AI risk report → filters |
| HybridQuestion method note | [`HYBRID_QUESTION.md`](HYBRID_QUESTION.md) | Multi-LLM vote + human foresight divergence |
| Constitutional / multi-stakeholder curiosity | [`CONSTITUTIONAL_CURIOSITY.md`](CONSTITUTIONAL_CURIOSITY.md) | Veto stacks vs fake consensus blends |
| Curiosity eval metric stack | [`CURIOSITY_EVAL_METRICS.md`](CURIOSITY_EVAL_METRICS.md) | RINoBench caveats; gap+rank+elicit primary |
| Gap verify methods (SciFact family) | [`GAP_VERIFY_METHODS.md`](GAP_VERIFY_METHODS.md) | Claim verify ≠ question settled; escalation pattern |
| Funding / OpenAlex neglect signals | [`FUNDING_NEGLECT_SIGNALS.md`](FUNDING_NEGLECT_SIGNALS.md) | Metadata honesty; adapter-only upgrades |
| Investigation design / falsifiers | [`INVESTIGATION_DESIGN.md`](INVESTIGATION_DESIGN.md) | BoxingGym struggle; elicit rubric upgrades |
| Problem selection / McNamara (Bisht et al.) | [`PROBLEM_SELECTION_MCNAMARA.md`](PROBLEM_SELECTION_MCNAMARA.md) | Hivemind; co-scientist; diversity |
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
| Noordewier & Gocłowska, shared/unique epistemic emotions | DOI 10.1037/emo0001314 | Discrete structure of awe…boredom |
| Nerantzaki et al., biased-answer feedback → epistemic emotions | DOI 10.5964/ejop.13847 | Negative feedback arousal |
| Loewenstein, information-gap curiosity | Psych Bulletin 1994 | Classic elicitation account |
| Yanagisawa & Honda | arXiv:2401.00007 ; Frontiers Psych 2025 | Epistemic emotions as Bayesian information gain / Wundt-like curve |
| SciMuse (Gu & Krenn) | arXiv:2405.17044 | Expert interest ranking of AI ideas |
| ResearchAgent | arXiv:2404.07738 | Iterative idea generation + reviewing agents |
| IdeaSynth | arXiv:2410.04025 | Literature-grounded idea facet canvas |
| ScholarEval | arXiv:2510.16234 | Soundness + contribution eval of research ideas |
| IdeaBench / AI Idea Bench 2025 | arXiv:2411.02429 ; 2504.14191 | Idea-generation benchmarks |
| LitGapFinder | clawRxiv 2603.00233+ | Concept co-occurrence gap → hypotheses (agent skill) |
| Ai2 Scholar QA | arXiv:2504.10861 | Open scientific QA (contrast class) |
| Mohammad, Ethics Sheet for AER | arXiv:2109.08256 | ~50 ethical considerations for emotion recognition |
| Fabiano, affective computing × AI Act / privacy | arXiv:2509.20153 | Regulatory framing |
| MCP Safety Audit | arXiv:2504.03767 | MCP exploit classes + scanner |
| MPMA (preference manipulation) | arXiv:2505.11154 | Adversarial MCP descriptions |
| MSB (MCP Security Bench) | arXiv:2510.15994 | End-to-end MCP attack eval |
| MCPXKIT | arXiv:2508.12538 | 31 MCP attack methods |
| ScaleMCP | arXiv:2505.06416 | Dynamic MCP tool retrieval UX |
| Heath et al., EVSI moment matching | arXiv:1611.01373 ; 1804.09590 | Tractable EVSI approximations |
| Kunst et al., ConVOI EVSI methods guide | arXiv:1910.03368 | Which approx method given skills/model |
| Li, Jalal, Heath TGA EVSI | arXiv:2401.17393 | Nonlinear net-benefit correction |
| Sadatsafavi et al., EVSI for validation | arXiv:2401.01849 | VOI lens on external validation studies |
| Lingeman & Yu, LTR scientific documents | arXiv:1611.01400 | Expert relatedness ≠ text similarity |
| Ai et al., unbiased learning to rank | arXiv:2004.13574 | Offline/online ULTR; position bias |
| PFP preference feature preservation | arXiv:2506.11098 | Online preference learning majority-feature bias |
| BT-σ LLM-as-a-jury | arXiv:2602.16610 | Judge reliability from pairwise comps |
| DMLRank nonparametric preference ranking | arXiv:2601.21816 | GARS + efficient CIs for prefs |
| 80,000 Hours / GiveWell ITN framing | 80000hours.org ; GiveWell Labs posts | Cause-level neglectedness vocabulary |
| AutoDiscovery (Bayesian surprise ASD) | arXiv:2507.00310 ; NeurIPS 2025 | Surprisal-guided open-ended discovery |
| Risks of AI Scientists (safeguarding) | arXiv:2402.04247 | Human/agent/environment regulation triad |
| Jr. AI Scientist risk report | arXiv:2511.04583 | Fabrication, review hacking, citation risks |
| HybridQuestion | arXiv:2602.03849 | Human–AI collaboration on future questions |
| Abdollahpouri & Burke, multi-stakeholder RS | arXiv:1907.13158 | Multi-party recommendation / fairness taxonomy |
| EthicAlly (CAI ethics support) | arXiv:2508.00856 | Assist ethics design; don’t replace REC |
| RINoBench (novelty judgment) | arXiv:2603.10303 | LLM novelty scores diverge from expert gold |
| RND relative neighbor density novelty | arXiv:2503.01508 | Cross-domain novelty proxy |
| Ideation–execution gap | arXiv:2506.20803 | Pre-exec LLM idea advantage can reverse |
| SciFact / SciFact-Open | arXiv:2004.14974 ; 2210.13777 | Scientific claim verification (+ open-domain drop) |
| DeepSciVerify | arXiv:2605.27710 | Abstract-first claim–citation escalation |
| SciClops | arXiv:2110.13090 | Claim extract/cluster for science fact-check |
| Alperin et al., OpenAlex vs Scopus | arXiv:2404.17663 | Coverage vs metadata accuracy tradeoffs |
| Alonso-Alvarez & van Eck, OpenAlex Africa | arXiv:2409.01120 | High coverage; weaker funder/affiliation metadata |
| BoxingGym experimental design benchmark | arXiv:2501.01540 | LLMs struggle at EIG-optimal experiments |
| LeGIT LLM-guided intervention targeting | arXiv:2503.01139 | LLM assists causal discovery design |
| Kumar et al., IAScore / Distinctness | arXiv:2409.06185 | Automated future-idea eval metrics |
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
| Elicitation A/B protocol example | `examples/elicit_ab_protocol.json` |
| VOI worksheet template | `examples/voi_worksheet_template.json` |
| Preference events / weight hints | `preferences.py` |
| Constitution veto-stack example | `examples/constitution_veto_stack.json` |
| Gap status fixture template | `examples/gap_status_fixture_template.json` |
