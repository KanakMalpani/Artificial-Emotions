# Annotated Sources

All research for Artificial Curiosity lives in this repo under `docs/`.
Primary synthesis: `RESEARCH.md`. Design basis: `FIRST_PRINCIPLES.md`.

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
| ISPOR VOI Task Force | https://eprints.whiterose.ac.uk/id/eprint/158024/ | EVPI / EVSI / ENBS research prioritization |

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
| Failure catalog | `docs/FAILURE_MODES.md` + `tests/test_failure_modes.py` |
