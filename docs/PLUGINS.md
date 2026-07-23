# Plugins — use Artificial Curiosity on any AI platform

No vendor lock-in. After clone:

```bash
git clone https://github.com/KanakMalpani/Artificial-Curiosity.git
cd Artificial-Curiosity
python -m venv .venv
```

Activate the venv, then:

```bash
# macOS / Linux
source .venv/bin/activate
pip install -e ".[dev]"

# Windows
.venv\Scripts\activate
pip install -e ".[dev]"
```

Pick **one** integration surface:

| Surface | When to use |
|---------|-------------|
| **MCP stdio** (`curiosity-mcp`) | Cursor, Claude Desktop, Claude Code, VS Code Copilot Chat |
| **HTTP API** (`curiosity serve`) | Any agent that can call REST / OpenAPI |
| **OpenAI tools JSON** | Function-calling agents (OpenAI, Groq, OpenRouter, local) |
| **CLI** (`curiosity spark`) | Humans + scripts |

Scores use an explicit `ValueProfile` and are **decision aids**, not oracles.

---

## 1. MCP (recommended for IDE assistants)

Console script (after `pip install -e .`):

```bash
curiosity-mcp
# equivalent:
python -m artificial_curiosity.mcp_server
```

Tools exposed:

- `provoke_curiosity` / `spark` — instant ranked unknowns + `inject` pack
- `rank_unknowns` / `run_curiosity` — full pipeline (optional OpenAlex)
- `list_domains`

### Cursor

Add to Cursor MCP settings (`.cursor/mcp.json` in the project, or global MCP config):

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

If `curiosity-mcp` is not on `PATH`, point at the venv interpreter:

```json
{
  "mcpServers": {
    "artificial-curiosity": {
      "command": "/absolute/path/to/.venv/bin/python",
      "args": ["-m", "artificial_curiosity.mcp_server"]
    }
  }
}
```

Windows example:

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

### Claude Desktop

Edit Claude Desktop config (`claude_desktop_config.json`):

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

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

Restart Claude Desktop after saving.

### Claude Code / other MCP hosts

Same stdio pattern: command = `curiosity-mcp` (or `python -m artificial_curiosity.mcp_server`). Optional env for LLM-backed tools:

```json
{
  "mcpServers": {
    "artificial-curiosity": {
      "command": "curiosity-mcp",
      "env": {
        "LLM_API_KEY": "",
        "LLM_BASE_URL": "https://api.openai.com/v1",
        "LLM_MODEL": "gpt-4o-mini",
        "LLM_JUDGE_MODEL": ""
      }
    }
  }
}
```

Leave keys empty / unset for the default fast path (no LLM required).

Smoke: after config, ask the host to list MCP tools — expect `provoke_curiosity`, `spark`, `rank_unknowns`, `run_curiosity`, `list_domains`, `list_profiles`. Or run `curiosity-mcp --list-tools` in a terminal.

### VS Code Copilot (MCP)

If your Copilot / VS Code build supports MCP servers, register the same stdio command as above. Prefer the venv `python -m artificial_curiosity.mcp_server` form so the host finds the package.

Example (`.vscode/mcp.json` or Copilot MCP settings, depending on build):

```json
{
  "servers": {
    "artificial-curiosity": {
      "type": "stdio",
      "command": "curiosity-mcp",
      "args": []
    }
  }
}
```

Smoke: `curiosity-mcp --list-tools` then confirm Copilot can invoke `list_domains`.

### Continue (VS Code / JetBrains)

Continue supports MCP servers in `config.json` / Continue settings. Add:

```json
{
  "mcpServers": [
    {
      "name": "artificial-curiosity",
      "command": "curiosity-mcp",
      "args": []
    }
  ]
}
```

Use the absolute venv python + `-m artificial_curiosity.mcp_server` if the Continue host cannot find `curiosity-mcp` on PATH. Smoke: `curiosity-mcp --list-tools`.

### Windsurf

Windsurf MCP config follows the Cursor-like `mcpServers` map:

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

Smoke: list tools in Windsurf’s MCP panel after restart; offline spark needs no API key.

---

## 2. HTTP plugin (`curiosity serve`)

```bash
curiosity serve
```

| URL | Purpose |
|-----|---------|
| http://127.0.0.1:8000/docs | Interactive OpenAPI |
| http://127.0.0.1:8000/v1/curiosity/provoke?domain=ai&n=5 | Instant spark |
| http://127.0.0.1:8000/v1/curiosity/run | Full pipeline (POST) |
| http://127.0.0.1:8000/v1/agent | Machine guide |
| http://127.0.0.1:8000/v1/agent/tools | OpenAI-compatible tool schemas |
| http://127.0.0.1:8000/v1/domains | Domain list |

Example:

```bash
curl "http://127.0.0.1:8000/v1/curiosity/provoke?domain=ai&n=5&fast=true"
```

Paste `inject` from the JSON into any model.

---

## 3. OpenAI-compatible function calling

Load schemas from either:

- Static file: [`examples/openai_tools.json`](../examples/openai_tools.json)
- Live: `GET http://127.0.0.1:8000/v1/agent/tools` → use the `tools` array

Pass them as `tools` to any OpenAI-compatible `/chat/completions` host. When the model emits a tool call, execute it by:

1. Calling the matching HTTP route, or
2. `from artificial_curiosity.agent_tools import dispatch_tool` then `dispatch_tool(name, arguments)`

---

## 4. Sanity checks

```bash
curiosity spark --domain ai --n 3
python -c "from artificial_curiosity.agent_tools import mcp_tool_list; print(len(mcp_tool_list()))"
curiosity-mcp --list-tools
pytest -q
```

---

## Public-repo notes

- Copy `.env.example` → `.env` locally; never commit `.env` or API keys.
- Default spark path needs **no** key.
- OpenAlex literature grounding needs no key (optional `OPENALEX_MAILTO`).
- Optional LLM: set `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL` only in local env or MCP `env`.
