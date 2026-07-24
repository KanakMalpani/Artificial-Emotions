# Artificial Curiosity

**Current AI answers questions. This system generates the most valuable unanswered ones.**

Clone → install → plug into **any** AI platform (MCP, HTTP, OpenAI tools, or CLI). Ask: *What should we investigate next?*

**Repo:** https://github.com/KanakMalpani/Artificial-Curiosity

## Install

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

No API key required for the default fast path (curated seeds + heuristic ranking). Literature grounding uses OpenAlex (no key). Optional LLMs via any OpenAI-compatible provider — see [`.env.example`](.env.example). Maintainer publish notes: [`docs/PUBLISHING.md`](docs/PUBLISHING.md).

## Three ways to plug in

| Mode | Command / URL | Best for |
|------|----------------|----------|
| **MCP plugin** | `curiosity-mcp` | Cursor, Claude Desktop, Claude Code, VS Code Copilot |
| **HTTP API** | `curiosity serve` → `:8000` | Agents, curl, OpenAPI (`/docs`) |
| **CLI spark** | `curiosity spark --domain ai` | Humans + scripts |

Full install snippets: **[`docs/PLUGINS.md`](docs/PLUGINS.md)**.

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

Tools: `provoke_curiosity` / `spark`, `rank_unknowns` / `run_curiosity`, `list_domains`, `list_profiles`, `list_epistemic_cues`, `annotate_epistemic`, `emotion_pack`, `elicit_helpers`.

### HTTP

```bash
curiosity serve
```

| URL | Purpose |
|-----|---------|
| http://127.0.0.1:8000/docs | Interactive OpenAPI |
| http://127.0.0.1:8000/v1/curiosity/provoke?domain=ai&n=5 | Instant spark |
| http://127.0.0.1:8000/v1/emotions/cues | Epistemic cue vocabulary |
| http://127.0.0.1:8000/v1/emotions/annotate | Annotate a question (POST/GET) |
| http://127.0.0.1:8000/v1/profiles | Named ValueProfile presets |
| http://127.0.0.1:8000/v1/agent | Machine guide for AI agents |
| http://127.0.0.1:8000/v1/agent/tools | OpenAI-compatible tool schemas |

### OpenAI function-calling

- Live: `GET /v1/agent/tools`
- Static: [`examples/openai_tools.json`](examples/openai_tools.json)

### Instant CLI

```bash
curiosity spark --domain ai --n 5
curiosity spark --domain biology --profile alignment_lab --json
curiosity profiles
curiosity emotions cues
curiosity emotions annotate "What remains unknown about epistemic emotion elicitation?" --surprise 0.7
```

Prints an `inject` pack for Claude, GPT, Gemini, Llama, or any local model.

**Epistemic cues / emotions surface** (investigation framing — not felt emotion): see [`docs/EMOTIONS.md`](docs/EMOTIONS.md).

## Domains

Offline seeds cover: **ai**, **biology**, **physics**, **climate**, **medicine**, **materials**, **social**, **energy** (plus **general** mix).

## Use with any LLM provider

Optional LLM path speaks **OpenAI-compatible** `/chat/completions`:

```bash
export LLM_API_KEY=...
export LLM_BASE_URL=https://api.openai.com/v1
export LLM_MODEL=gpt-4o-mini

curiosity --domain ai --llm --model llama3.2 --base-url http://localhost:11434/v1 --no-literature
```

(`OPENAI_API_KEY` / `OPENAI_BASE_URL` still work as aliases.) Credentials stay in the environment — never commit `.env`.

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
print(annotate_epistemic(
    "What remains unknown about epistemic emotion elicitation?",
    surprise=0.7,
)["epistemic_cues"])
print(dispatch_tool("list_domains"))
```

## What the system does

1. Propose candidate unknowns  
2. Verify they look unanswered in the literature (OpenAlex)  
3. Score impact / neglectedness / tractability / surprise / answerability / risk  
4. Diversify and return investigation briefs  

## Design invariants

- No value-free ranking — `ValueProfile` is explicit  
- Related literature ≠ answered  
- Near-duplicates are suppressed  
- Scores carry confidence / uncertainty bands; heuristics are flagged  

## Docs

| Doc | Purpose |
|-----|---------|
| [`docs/PLUGINS.md`](docs/PLUGINS.md) | Platform install (MCP / HTTP / tools) |
| [`docs/EMOTIONS.md`](docs/EMOTIONS.md) | Epistemic cues / affective pack (does not feel) |
| [`docs/LIMITS.md`](docs/LIMITS.md) | Honest bounds |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Pipeline overview |
| [`docs/PROOFS.md`](docs/PROOFS.md) | Demo commands for verified behaviors |
| [`docs/DESIGN.md`](docs/DESIGN.md) | Short design invariants |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | Agent playbook + roadmap (stuck → §0→§3→§2) · [`summary`](docs/ROADMAP_SUMMARY.md) |

**Design rationale (optional):** [`research/`](research/) — first principles, F1–F15 failure modes, sources. Used to build the product; not required to run it.

## Roadmap

See [`docs/ROADMAP.md`](docs/ROADMAP.md) for the **agent playbook** (stuck playbooks, priority wedges, session DoD) plus phased work orders (v0.2 → v2+). One-page overview: [`docs/ROADMAP_SUMMARY.md`](docs/ROADMAP_SUMMARY.md).

## Web UI (optional)

```bash
curiosity serve          # terminal 1 — API :8000
cd web && npm install && npm run dev   # terminal 2 — UI :5173
```

## Status

v0.1.0 — clone, install, MCP or HTTP plugin, spark. Works offline; optional any-provider LLM; optional OpenAlex grounding. Scores are decision aids, not oracles.

## License

[MIT](LICENSE)
