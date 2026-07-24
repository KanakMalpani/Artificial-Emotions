# Artificial Curiosity

**Rank valuable unanswered scientific questions. Do not use it to answer them.**

Artificial Curiosity is a curiosity layer for people and agents deciding what to
investigate next. It turns a domain, topic, and explicit `ValueProfile` into
ranked unknowns, gap evidence, uncertainty bands, and investigation briefs.

[![CI](https://github.com/KanakMalpani/Artificial-Curiosity/actions/workflows/ci.yml/badge.svg)](https://github.com/KanakMalpani/Artificial-Curiosity/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)

> Scores are decision aids, not scientific truth or calibrated forecasts. A
> literature neighborhood is evidence to inspect, not proof that a question is
> answered or unanswered.

## 60-second demo

Clone the repository and install it from that local checkout:

```bash
git clone https://github.com/KanakMalpani/Artificial-Curiosity.git
cd Artificial-Curiosity
python -m venv .venv
```

```bash
# macOS / Linux
source .venv/bin/activate
pip install -e ".[dev]"

# Windows PowerShell
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

Ask for a fast, offline-ranked investigation pack:

```bash
curiosity spark --domain ai --n 5 --json
```

The result includes ranked questions, a `value_profile`, provisional gap status,
score bands, flags, investigation briefs, and an `inject` string. Paste `inject`
into another model when you want it to choose an unknown, propose a first
investigation, and name falsifiers.

The default `spark` path uses curated seeds and heuristic scoring; it requires
neither an LLM key nor a network connection. Use `curiosity run` or
`spark --literature` when you want literature-neighborhood checks.

## What it does—and does not do

| It does | It does not |
|---|---|
| Ranks candidate unanswered questions under a named or supplied `ValueProfile` | Answer research questions or replace literature review |
| Separates related work from an “answered” conclusion | Provide a value-free or objectively correct priority order |
| Produces operationalizations, briefs, flags, confidence, and score bands | Prove a gap is real, calculate EVSI, or run experiments |
| Suppresses near-duplicates before top-N results | Act as a closed-loop AI scientist or biosafety authority |
| Exposes CLI, Python, HTTP, MCP, and OpenAI-style tool surfaces | Lock you into an LLM provider |

The score axes are impact, neglectedness, tractability, surprise, answerability,
and risk. They are proxies. The displayed `[low–high]` range is an
evidence-strength envelope, not a statistical confidence interval.

## Use it from your stack

| Surface | Entry point | Use it for |
|---|---|---|
| CLI | `curiosity spark`, `curiosity run` | Shell workflows and quick inspection |
| Python | `provoke`, `CuriosityEngine` | Libraries and notebooks |
| MCP (stdio) | `curiosity-mcp` | Cursor, Claude Desktop, Claude Code, Copilot, and other MCP hosts |
| HTTP | `curiosity serve` | REST/OpenAPI clients and agent backends |
| OpenAI-style tools | `examples/openai_tools.json` or `/v1/agent/tools` | Function-calling hosts |

Complete host-specific setup is in [docs/PLUGINS.md](docs/PLUGINS.md).

### CLI

```bash
# Fast local pack: curated seeds + heuristics
curiosity spark --domain biology --profile alignment_lab --json

# Full pipeline, but keep it offline
curiosity run --domain ai --n 5 --no-literature --json

# Compare the same candidate pool under two value choices
curiosity compare-profiles --domain ai \
  --a humanity_default --b alignment_lab --n 6 --json

# Inspect available profiles and tools
curiosity profiles
curiosity-mcp --list-tools
```

Supported seed domains are `ai`, `biology`, `physics`, `climate`, `medicine`,
`materials`, `social`, `energy`, and `general`. List the current presets with
`curiosity profiles`; every ranking has a `ValueProfile`, including the default.

### Python

```python
from artificial_curiosity import CuriosityConfig, CuriosityEngine, provoke

pack = provoke(domain="ai", n=5, fast=True, profile_name="alignment_lab")
print(pack["inject"])

results = CuriosityEngine(
    CuriosityConfig(
        domain="climate",
        n_return=5,
        use_literature=False,
    )
).run()
```

### MCP

Start the stdio server:

```bash
curiosity-mcp
# equivalent: python -m artificial_curiosity.mcp_server
```

For a local Cursor configuration, prefer the venv interpreter rather than a
bare command on `PATH`:

```json
{
  "mcpServers": {
    "artificial-curiosity": {
      "command": "C:\\path\\to\\Artificial-Curiosity\\.venv\\Scripts\\python.exe",
      "args": ["-m", "artificial_curiosity.mcp_server"]
    }
  }
}
```

Core tools are `provoke_curiosity` / `spark`, `rank_unknowns` /
`run_curiosity`, `list_domains`, and `list_profiles`. The server also exposes
comparison, brief-critique, worksheet, affect, and evaluation helpers. Use
`CURIOSITY_MCP_TIER` to reduce the exposed tool set. See
[docs/PLUGINS.md](docs/PLUGINS.md) for Cursor, Claude, Copilot, Continue, and
Windsurf configurations.

### HTTP and OpenAI-style tools

```bash
curiosity serve
```

The server listens on `127.0.0.1:8000` by default.

```bash
# Fast pack for a browser, curl, or agent
curl "http://127.0.0.1:8000/v1/curiosity/provoke?domain=ai&n=5&fast=true"

# Interactive API reference
# http://127.0.0.1:8000/docs
```

| Route | Purpose |
|---|---|
| `GET /health`, `GET /ready` | Liveness, configuration summary, and offline readiness |
| `GET\|POST /v1/curiosity/provoke` | Fast investigation pack |
| `POST /v1/curiosity/run` | Full ranking pipeline |
| `GET /v1/profiles`, `GET /v1/domains` | Discover ranking inputs |
| `GET /v1/agent` | Machine-readable capability and honesty guide |
| `GET /v1/agent/tools` | OpenAI-compatible function schemas |
| `GET /v1/emotions/catalog`, `POST /v1/emotions/mix` | Computational-affect catalog and mix |

Load `examples/openai_tools.json`, or fetch `/v1/agent/tools` and pass its
`tools` array to an OpenAI-compatible chat-completions client. Execute emitted
calls with this HTTP API or with
`artificial_curiosity.agent_tools.dispatch_tool`.

## Computational affect and epistemic cues

The mixable **emotion catalog** has **25** named emotions across four families:

- **Epistemic (10):** `curiosity`, `interest`, `confusion`, `surprise`, `awe`, `wonder`, `boredom`, `intrigue`, `uncertainty`, `enjoyment`
- **Basic (7):** `joy`, `sadness`, `anger`, `fear`, `disgust`, `anticipation`, `trust`
- **Social (4):** `pride`, `shame`, `gratitude`, `admiration`
- **Achievement (4):** `hope`, `relief`, `frustration`, `anxiety`

There are two related but distinct affect surfaces:

- **Epistemic cues / annotate** — tag information gaps, incongruity, and confusion risk (`honesty: "annotation_only"`).
- **Emotion mixes / `feel()`** — normalize catalog weights and, by default, return `honesty: "computational_affect"` plus a `felt_simulation` (PAD mood, intensity, first-person framing).

`simulate_feeling=True` is the default (also via `feel()`). Pass `simulate_feeling=False` for weights and PAD only. Neither surface claims biological consciousness, measured human affect, clinical scores, or biometric emotion recognition.

Separately, `emotion_pack("affective_science")` is a **ranking seed pack** of unanswered affect-science questions — not the mix catalog.

```bash
curiosity emotions mix curiosity=40 confusion=30 awe=30 --json
curiosity emotions mix curiosity=40 confusion=30 awe=30 --simulate-feeling false --json
curiosity emotions annotate \
  "What remains unknown about epistemic emotion elicitation?" \
  --surprise 0.7 --json
```

```python
from artificial_curiosity import annotate_epistemic, mix_emotions, feel

mix = mix_emotions(curiosity=40, confusion=30, awe=30)
assert mix["honesty"] == "computational_affect"
print(mix["felt_simulation"]["inner_monologue"])

felt = feel(curiosity=50, awe=50)
print(felt["felt_simulation"]["intensity"])

cues = annotate_epistemic(
    "What remains unknown about epistemic emotion elicitation?",
    surprise=0.7,
)
assert cues["honesty"] == "annotation_only"
```

The mix accepts percentages or unit weights, normalizes them to one, and rejects unknown IDs, negatives, all-zero mixes, and more than eight components. It warns when fear/anxiety/anger-type framing dominates. Details: [docs/EMOTIONS.md](docs/EMOTIONS.md). Design notes live under [research/](research/) (e.g. [AI_EMOTIONS.md](research/AI_EMOTIONS.md), [EMOTION_MIXING.md](research/EMOTION_MIXING.md)) — internal monographs, not journal papers. Gap verification stays primary over idea-novelty checkers; see [research/IDEA_NOVELTY_CHECKER.md](research/IDEA_NOVELTY_CHECKER.md).

## Optional LLM and literature paths

The package can use any OpenAI-compatible `/chat/completions` endpoint for
generation, judging, and grounded gap reading. Configuration belongs in the
environment or an uncommitted `.env`; start from [.env.example](.env.example).

```bash
# Configure locally; do not commit credentials.
export LLM_API_KEY=...
export LLM_BASE_URL=https://api.openai.com/v1
export LLM_MODEL=gpt-4o-mini

curiosity run --domain ai --llm --no-literature --n 5

# Example local OpenAI-compatible server
curiosity run --domain ai --llm --model llama3.2 \
  --base-url http://localhost:11434/v1 --no-literature
```

`run` uses OpenAlex by default when literature is enabled. Semantic Scholar and
a merged mode are available through `--literature-backend`; network results are
still neighborhoods to inspect, not full-text understanding. Provider and
verification notes are in [docs/PROOFS.md](docs/PROOFS.md).

## How the ranking works

```text
ValueProfile + domain/topic
            │
            ▼
Generate candidates ──► Verify literature neighborhood ──► Score and gate
   seeds / packs / LLM        OpenAlex / Semantic Scholar       heuristics / LLM
            └──────────────────────► Diversify ──────► briefs + inject pack
```

1. **Generate:** use curated seeds, optional JSON domain packs, and optionally
   an LLM.
2. **Verify:** retrieve and classify a literature neighborhood. Related work is
   not silently treated as an answer.
3. **Score and gate:** score the axes, then apply answerability, risk, and
   likely-answered gates.
4. **Diversify:** remove close near-duplicates (normalized Jaccard by default;
   embeddings are optional).
5. **Brief:** return a question, operationalization, rationale, gap evidence,
   score context, flags, and suggested first moves.

Trust boundaries:

- Curated seeds and heuristics support the offline path; they are not a
  representative scientific corpus.
- Optional network boundaries are OpenAlex, Semantic Scholar, and the
  OpenAI-compatible endpoint you configure.
- Secrets stay in environment variables. HTTP deliberately does not accept a
  caller-provided LLM base URL or literature-cache path.
- Dual-use screening is a weighted heuristic with a human-review flag—not a
  biosafety decision.
- Scores remain stakeholder-dependent because the `ValueProfile` is explicit.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the module map and
[docs/LIMITS.md](docs/LIMITS.md) for the full bounds.

## Verification, status, and limits

| Area | Current behavior |
|---|---|
| Version | `0.4.0` ([pyproject.toml](pyproject.toml)) |
| Default path | Curated seeds + heuristic ranking; no LLM key or network required |
| Literature | OpenAlex by default; optional Semantic Scholar; gap checks remain provisional |
| LLM | Optional OpenAI-compatible provider configured by environment |
| Diversity | Normalized Jaccard by default; embedding backend is an optional extra |
| Scores | Explicit-value decision aids with provisional bands, not oracle outputs |
| Affect | `annotation_only` cues; `computational_affect` emotion-mix simulation |
| Safety | Heuristic dual-use signals and human-review flags, not a biosafety oracle |
| CI | Ruff and pytest run on push and pull request |

Run the locally supported checks:

```bash
pytest -q
pytest tests/e2e -q
curiosity eval
curiosity-mcp --list-tools
```

Read [docs/PROOFS.md](docs/PROOFS.md) for behavior-specific commands and
[docs/LIMITS.md](docs/LIMITS.md) before relying on a rank in a real decision.

## Documentation

| Read this | For |
|---|---|
| [docs/INDEX.md](docs/INDEX.md) | Documentation entry point |
| [docs/PLUGINS.md](docs/PLUGINS.md) | MCP, HTTP, and OpenAI-style tool setup |
| [docs/EMOTIONS.md](docs/EMOTIONS.md) | Cues, catalog, and computational-affect mixes |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Modules and trust boundaries |
| [docs/LIMITS.md](docs/LIMITS.md) | What the system does not establish |
| [docs/PROOFS.md](docs/PROOFS.md) | Reproducible product checks |
| [examples/README.md](examples/README.md) | Example payloads and protocols |
| [research/](research/) | Optional design rationale and research notes |

## Contributing and security

Start with [CONTRIBUTING.md](CONTRIBUTING.md). Small, focused changes are
easier to review. Changes to ranking, gap logic, tools, or public claims should
include tests and updates to the relevant limits and proof documentation.

Keep credentials in local environment files; never commit `.env`, API keys, or
tokens. Before exposing HTTP beyond localhost, configure `CURIOSITY_API_KEY`
or `CURIOSITY_API_KEYS` and do not bind `0.0.0.0` without authentication. Do
not put credentials or exploit details in a public issue; report vulnerabilities
to the repository maintainer privately.

## License

[MIT](LICENSE)
