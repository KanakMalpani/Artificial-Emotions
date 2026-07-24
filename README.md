# Artificial Curiosity

**Current AI answers questions. This is the curiosity layer — ranked unanswered questions, not Q&A.**

Ask any model or agent: *What should we investigate next?* Get investigation briefs with an explicit `ValueProfile`, gap evidence, and uncertainty bands. Plug in via **MCP**, **HTTP**, **OpenAI tools**, **CLI**, or **Python**.

[![CI](https://github.com/KanakMalpani/Artificial-Curiosity/actions/workflows/ci.yml/badge.svg)](https://github.com/KanakMalpani/Artificial-Curiosity/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)

> **v0.4.0** · Clone & install (not on PyPI yet) · Scores are **decision aids**, not oracles · Emotions are **annotation_only** framing — the system does **not** feel.

---

## Why this exists

Most AI tools optimize for *answers*. Research and product work still stall on a harder problem: **which unknowns are worth chasing?**

Artificial Curiosity generates candidate unknowns, checks that related literature ≠ answered, scores them on impact / neglectedness / tractability / surprise / answerability / risk, diversifies near-duplicates, and returns **investigation briefs** you can inject into any model.

| This is | This is not |
|---------|-------------|
| A curiosity layer for agents & labs | Literature Q&A / chatbot |
| Ranked *unanswered* questions | Citation forecasting |
| Explicit `ValueProfile` weights | Value-free “objective” ranking |
| MCP + HTTP + tools plugin | A locked-in vendor stack |
| Annotation-only epistemic cues / emotion mixes | Claimed felt emotion or EES scores |

---

## 60-second spark

```bash
git clone https://github.com/KanakMalpani/Artificial-Curiosity.git
cd Artificial-Curiosity
python -m venv .venv
```

```bash
# macOS / Linux
source .venv/bin/activate
pip install -e ".[dev]"

# Windows
.venv\Scripts\activate
pip install -e ".[dev]"
```

```bash
curiosity spark --domain ai --n 5
curiosity profiles
curiosity emotions mix curiosity=40 confusion=30 awe=30 --json
```

No API key required for the default fast path (curated seeds + heuristic ranking). Literature grounding uses **OpenAlex** (no key). Optional LLMs via any **OpenAI-compatible** provider — see [`.env.example`](.env.example).

---

## Plug into any platform

| Surface | Command / URL | Best for |
|---------|----------------|----------|
| **MCP** | `curiosity-mcp` | Cursor, Claude Desktop, Claude Code, VS Code Copilot |
| **HTTP** | `curiosity serve` → `:8000` | Agents, curl, OpenAPI |
| **OpenAI tools** | [`examples/openai_tools.json`](examples/openai_tools.json) or `GET /v1/agent/tools` | Function-calling hosts |
| **CLI** | `curiosity spark` / `curiosity run` | Humans + scripts |
| **Python** | `provoke`, `CuriosityEngine` | Libraries & notebooks |

Full install snippets for every host: **[`docs/PLUGINS.md`](docs/PLUGINS.md)**.

### MCP (stdio)

```bash
curiosity-mcp
# or: python -m artificial_curiosity.mcp_server
```

```json
{
  "mcpServers": {
    "artificial-curiosity": {
      "command": "curiosity-mcp",
      "args": []
    }
  }
}
```

Core tools: `provoke_curiosity` / `spark`, `rank_unknowns` / `run_curiosity`, `list_domains`, `list_profiles`. Affect tools (optional): `list_epistemic_cues`, `emotion_catalog`, `mix_emotions`, `annotate_epistemic`, `emotion_pack`, `elicit_helpers`. Progressive disclosure via `CURIOSITY_MCP_TIER`.

### HTTP

```bash
curiosity serve
```

| URL | Purpose |
|-----|---------|
| http://127.0.0.1:8000/docs | Interactive OpenAPI |
| http://127.0.0.1:8000/v1/curiosity/provoke?domain=ai&n=5 | Instant spark |
| http://127.0.0.1:8000/v1/emotions/catalog | Mixable emotion catalog |
| http://127.0.0.1:8000/v1/emotions/mix | POST framing mix (annotation only) |
| http://127.0.0.1:8000/v1/profiles | Named ValueProfile presets |
| http://127.0.0.1:8000/v1/agent | Machine guide + honesty block |
| http://127.0.0.1:8000/v1/agent/tools | OpenAI-compatible tool schemas |

### CLI demos

```bash
curiosity spark --domain biology --profile alignment_lab --json
curiosity run --domain ai --n 5 --no-literature --json
curiosity compare-profiles --domain ai --a humanity_default --b alignment_lab --n 6 --json
curiosity emotions cues
curiosity emotions annotate "What remains unknown about epistemic emotion elicitation?" --surprise 0.7
curiosity eval
curiosity-mcp --list-tools
```

More verified commands: **[`docs/PROOFS.md`](docs/PROOFS.md)**. Sample payloads: **[`examples/`](examples/)** ([index](examples/README.md)).

---

## Emotions / epistemic cues (honest)

Tag questions with epistemic cues, pull a named emotion catalog, or mix framing weights (e.g. curiosity 40% + confusion 30% + awe 30%).

These are **UX / investigation-framing annotations**. Responses carry `honesty: "annotation_only"`. The software does **not** feel emotions.

```python
from artificial_curiosity import emotion_catalog, mix_emotions, annotate_epistemic

print(emotion_catalog()["ids"][:5])
print(mix_emotions(curiosity=40, confusion=30, awe=30)["inject_fragment"])
print(annotate_epistemic(
    "What remains unknown about epistemic emotion elicitation?",
    surprise=0.7,
)["epistemic_cues"])
```

How-to: [`docs/EMOTIONS.md`](docs/EMOTIONS.md) · Background (optional): [`research/AI_EMOTIONS.md`](research/AI_EMOTIONS.md).

---

## Multi-provider LLM (optional)

Any OpenAI-compatible `/chat/completions` host:

```bash
export LLM_API_KEY=...
export LLM_BASE_URL=https://api.openai.com/v1
export LLM_MODEL=gpt-4o-mini

curiosity run --domain ai --llm --n 5 --no-literature
# Local Ollama example:
curiosity run --domain ai --llm --model llama3.2 --base-url http://localhost:11434/v1 --no-literature
```

(`OPENAI_API_KEY` / `OPENAI_BASE_URL` still work as aliases.) Credentials stay in the environment — never commit `.env`. Provider matrix notes: [`docs/PROOFS.md`](docs/PROOFS.md).

---

## Python API

```python
from artificial_curiosity import (
    CuriosityEngine,
    CuriosityConfig,
    provoke,
    list_epistemic_cues,
    annotate_epistemic,
)
from artificial_curiosity.agent_tools import dispatch_tool

pack = provoke(domain="ai", n=5, fast=True)
print(pack["inject"])

print(list_epistemic_cues()["tags"])
print(dispatch_tool("list_domains"))
```

---

## Architecture (sketch)

```
ValueProfile + domain ──▶ CuriosityEngine ──▶ Ranked unknowns + briefs
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
         Generate        Verify gap      Score + gate
       (seeds/packs/LLM) (OpenAlex/S2)  (heuristic/LLM)
              │               │               │
              └──────────▶ Diversify ◀────────┘
```

| Step | What happens |
|------|----------------|
| 1. Propose | Curated seeds + optional domain packs + optional LLM forge |
| 2. Verify | Literature neighborhood; **related ≠ answered** |
| 3. Score | Impact / neglectedness / tractability / surprise / answerability / risk |
| 4. Gate | Answerability, dual-use risk, likely-answered |
| 5. Diversify | Near-dup suppression (Jaccard default; optional embeddings) |
| 6. Brief | Investigation briefs + optional `inject` pack for any model |

Modules & trust boundaries: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

### Design invariants

- No value-free ranking — `ValueProfile` is always explicit  
- Related literature ≠ answered  
- Near-duplicates are suppressed  
- Scores carry confidence / `[low–high]` bands; heuristics are flagged  
- Offline path degrades gracefully when literature / LLM is unavailable  

---

## Domains & profiles

Offline seeds cover: **ai**, **biology**, **physics**, **climate**, **medicine**, **materials**, **social**, **energy** (plus **general**). Optional JSON **domain packs** under `src/artificial_curiosity/packs/`.

Named profiles: `humanity_default`, `funder_10y`, `alignment_lab`, `climate_adaptation`, `basic_science`, `near_term_ops`, `public_demo_strict_risk` — via `curiosity profiles`, `GET /v1/profiles`, or `--profile`.

---

## Docs map

| Doc | Purpose |
|-----|---------|
| [`docs/INDEX.md`](docs/INDEX.md) | Docs entry point |
| [`docs/PLUGINS.md`](docs/PLUGINS.md) | MCP / HTTP / tools install |
| [`docs/EMOTIONS.md`](docs/EMOTIONS.md) | Epistemic cues + mixes (does not feel) |
| [`docs/LIMITS.md`](docs/LIMITS.md) | Honest bounds — read before marketing |
| [`docs/PROOFS.md`](docs/PROOFS.md) | Demo commands for verified behaviors |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Pipeline overview |
| [`docs/DESIGN.md`](docs/DESIGN.md) | Short invariants |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | Agent playbook (stuck → §0→§3→§2) |
| [`docs/ROADMAP_SUMMARY.md`](docs/ROADMAP_SUMMARY.md) | One-page roadmap |
| [`docs/PUBLISHING.md`](docs/PUBLISHING.md) | Maintainer PyPI notes |
| [`examples/README.md`](examples/README.md) | Sample JSON / protocols |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Setup, seeds, packs, PR bar |

**Design rationale (optional):** [`research/`](research/) — first principles, F1–F15 failure modes, sources. Used to build the product; **not** required to run it. Index: [`research/INDEX.md`](research/INDEX.md).

---

## Web UI (optional)

```bash
curiosity serve                    # terminal 1 — API :8000
cd web && npm install && npm run dev   # terminal 2 — UI :5173
```

UI shows briefs, `[low–high]` bands, profile name, optional framing mix (annotation only), and profile compare. Decision aids, not oracles.

---

## Status & honesty

| Claim | Reality |
|-------|---------|
| Version | **0.4.0** (see `pyproject.toml`) |
| Install | Clone + `pip install -e .` — **not on PyPI yet** |
| Default path | Offline seeds + heuristics; no API key |
| Literature | OpenAlex (default); optional Semantic Scholar |
| LLM | Optional; any OpenAI-compatible host |
| Emotions | `annotation_only` — does **not** feel |
| Scores | Decision aids with uncertainty bands — **not** calibrated oracles |
| Dual-use | Weighted heuristic + human-review flag — **not** a biosafety oracle |
| CI | Ruff + pytest on push/PR (`.github/workflows/ci.yml`) |

Full bounds: [`docs/LIMITS.md`](docs/LIMITS.md).

---

## License

[MIT](LICENSE)
