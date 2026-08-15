# Plugins — use Artificial Emotions on any AI platform

No vendor lock-in. After clone:

```bash
git clone https://github.com/KanakMalpani/Artificial-Emotions.git
cd Artificial-Emotions
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
| **MCP stdio** (`emotions-mcp`) | Cursor, Claude Desktop, Claude Code, VS Code Copilot Chat |
| **HTTP API** (`emotions serve`) | Any agent that can call REST / OpenAPI |
| **OpenAI tools JSON** | Function-calling agents (OpenAI, Groq, OpenRouter, local) |
| **LangGraph (host-side)** | Copy-paste in [§4](#4-langgraph-host-side-optional); uses `GET /v1/agent/tools`. `langgraph` is not a package extra. |
| **CLI** (`emotions spark`) | Humans + scripts. Also `emotions export unknowns` (file JSON; no webhooks) and `emotions pack check` (CONTRIBUTING bar). |

Scores use an explicit `ValueProfile` and are **decision aids**, not oracles.

### Plugin UX rules (keep the tool a good citizen)

- **Job boundary:** rank / provoke unknowns — never claim to answer the questions or replace lit review.
- **Progressive disclosure:** `provoke`/`spark` (fast) → `run_curiosity` (lit) → `emotions eval` (harness). Prefer resources (`curiosity://limits`, profiles, domains) before large runs.
- **Descriptions:** documentation, not persuasion — no “best tool”, “always call first”, or “the AI becomes curious.”
- **Emotions:** optional framing tools; do not force mix/cues into every flow. Annotation only — does not feel.
- **Pin by path:** hosts should pin the MCP command to this repo’s venv binary so a similarly named malicious server cannot win by description alone.

---

## 1. MCP (recommended for IDE assistants)

Console script (after `pip install -e .`):

```bash
emotions-mcp
# equivalent:
python -m artificial_emotions.mcp_server
```

Tools exposed (core):

- `provoke_curiosity` / `spark` — instant ranked unknowns + `inject` pack
- `rank_unknowns` / `run_curiosity` — full pipeline (optional OpenAlex)
- `export_unknowns` — wrap an already-ranked set as a JSON document (file / HTTP body; no webhook URLs)
- `list_domains`, `list_profiles`
- `preference_weight_hints` — preview (default) or apply tiny ValueProfile weight deltas from inline events; not calibrated; no filesystem paths

Affect / framing (optional — annotation only; does not feel): `list_epistemic_cues`, `emotion_catalog`, `mix_emotions`, `annotate_epistemic`, `emotion_pack`, `elicit_helpers`. Tier via `CURIOSITY_MCP_TIER`. Full list: `emotions-mcp --list-tools`.

### Cursor

Add to Cursor MCP settings (`.cursor/mcp.json` in the project, or global MCP config):

```json
{
  "mcpServers": {
    "artificial-emotions": {
      "command": "emotions-mcp",
      "args": []
    }
  }
}
```

If `emotions-mcp` is not on `PATH`, point at the venv interpreter:

```json
{
  "mcpServers": {
    "artificial-emotions": {
      "command": "/absolute/path/to/.venv/bin/python",
      "args": ["-m", "artificial_emotions.mcp_server"]
    }
  }
}
```

Windows example:

```json
{
  "mcpServers": {
    "artificial-emotions": {
      "command": "C:\\path\\to\\Artificial-Emotions\\.venv\\Scripts\\python.exe",
      "args": ["-m", "artificial_emotions.mcp_server"]
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
    "artificial-emotions": {
      "command": "emotions-mcp",
      "args": []
    }
  }
}
```

Restart Claude Desktop after saving.

### Claude Code / other MCP hosts

Same stdio pattern: command = `emotions-mcp` (or `python -m artificial_emotions.mcp_server`). Optional env for LLM-backed tools:

```json
{
  "mcpServers": {
    "artificial-emotions": {
      "command": "emotions-mcp",
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

Smoke: after config, ask the host to list MCP tools — expect `provoke_curiosity`, `spark`, `rank_unknowns`, `run_curiosity`, `list_domains`, `list_profiles`, plus epistemic tools `list_epistemic_cues`, `emotion_catalog`, `mix_emotions`, `annotate_epistemic`, `emotion_pack`, `elicit_helpers`. Or run `emotions-mcp --list-tools` in a terminal. Resources (optional): `emotions-mcp --list-resources` → `curiosity://domains`, `curiosity://profiles`, `curiosity://limits`, `curiosity://emotions`. Epistemic cues how-to: [`EMOTIONS.md`](EMOTIONS.md).

### VS Code Copilot (MCP)

If your Copilot / VS Code build supports MCP servers, register the same stdio command as above. Prefer the venv `python -m artificial_emotions.mcp_server` form so the host finds the package.

Example (`.vscode/mcp.json` or Copilot MCP settings, depending on build):

```json
{
  "servers": {
    "artificial-emotions": {
      "type": "stdio",
      "command": "emotions-mcp",
      "args": []
    }
  }
}
```

Smoke: `emotions-mcp --list-tools` then confirm Copilot can invoke `list_domains`.

### Continue (VS Code / JetBrains)

Continue supports MCP servers in `config.json` / Continue settings. Add:

```json
{
  "mcpServers": [
    {
      "name": "artificial-emotions",
      "command": "emotions-mcp",
      "args": []
    }
  ]
}
```

Use the absolute venv python + `-m artificial_emotions.mcp_server` if the Continue host cannot find `emotions-mcp` on PATH. Smoke: `emotions-mcp --list-tools`.

### Windsurf

Windsurf MCP config follows the Cursor-like `mcpServers` map:

```json
{
  "mcpServers": {
    "artificial-emotions": {
      "command": "emotions-mcp",
      "args": []
    }
  }
}
```

Smoke: list tools in Windsurf’s MCP panel after restart; offline spark needs no API key.

---

## 2. HTTP plugin (`emotions serve`)

```bash
emotions serve
```

| URL | Purpose |
|-----|---------|
| http://127.0.0.1:8000/docs | Interactive OpenAPI |
| http://127.0.0.1:8000/health | Liveness + config summary |
| http://127.0.0.1:8000/ready | Readiness (offline spark/emotions) |
| http://127.0.0.1:8000/v1/curiosity/provoke?domain=ai&n=5 | Instant spark |
| http://127.0.0.1:8000/v1/curiosity/run | Full pipeline (POST) |
| http://127.0.0.1:8000/v1/export/unknowns | Ranked-set JSON export (POST; no webhooks) |
| http://127.0.0.1:8000/v1/emotions/catalog | Mixable emotion catalog |
| http://127.0.0.1:8000/v1/emotions/mix | POST mix weights |
| http://127.0.0.1:8000/v1/agent | Machine guide |
| http://127.0.0.1:8000/v1/agent/tools | OpenAI-compatible tool schemas |
| http://127.0.0.1:8000/v1/domains | Domain list |

### Copy-paste curls

```bash
# Spark (paste `inject` into any model)
curl -s "http://127.0.0.1:8000/v1/curiosity/provoke?domain=ai&n=5&fast=true"

# Export a ranked set (reuse /v1/curiosity/run `questions`; no webhook URLs)
curl -s -X POST http://127.0.0.1:8000/v1/export/unknowns \
  -H "Content-Type: application/json" \
  -d '{"questions":[{"rank":1,"question":{"question":"Which training interventions most increase honest uncertainty reporting under incentive pressure?"},"curiosity_score":0.8}],"domain":"ai"}'

# Catalog + mix (annotation_only framing weights — does not feel)
curl -s http://127.0.0.1:8000/v1/emotions/catalog
curl -s -X POST http://127.0.0.1:8000/v1/emotions/mix \
  -H "Content-Type: application/json" \
  -d '{"weights":{"curiosity":40,"confusion":30,"awe":30}}'
```

Errors use a stable shape: `{"error":{"code":"unknown_emotion","message":"…"}}`.

### Optional API key (WO-0.4.6)

Unset by default so local demos stay open. Set `CURIOSITY_API_KEY` (or comma-separated `CURIOSITY_API_KEYS`) to require `Authorization: Bearer <key>` or `X-API-Key` on `/v1/...` routes. `/health`, `/ready`, and `/` stay open; health reports `api_auth_required`. `emotions serve` refuses `0.0.0.0` unless `CURIOSITY_ALLOW_NONLOCAL_BIND=1`. Do not bind `0.0.0.0` without a key. Still not TLS.

Opt-in per-key request budget: set `CURIOSITY_API_QUOTA_REQUESTS` (and optionally `CURIOSITY_API_QUOTA_WINDOW_S`, default 86400). Unset = no quota. Exceeding the budget returns HTTP 429 with `error.code=quota_exceeded`. In-process only — not a billing meter.

Opt-in audit JSONL: set `CURIOSITY_AUDIT_LOG` to a file path. Logs HTTP method+path and MCP tool names plus status. Default off. Never request/response bodies, headers, or API keys.

Central env reference: `artificial_emotions.config` and `.env.example` (`LLM_TIMEOUT_S`, `LITERATURE_TIMEOUT_S`, `CURIOSITY_CORS_ORIGINS`, …).

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

Includes emotion tools: `emotion_catalog`, `mix_emotions`, `list_epistemic_cues`, `annotate_epistemic`, `emotion_pack`, `elicit_helpers`.

Pass them as `tools` to any OpenAI-compatible `/chat/completions` host. When the model emits a tool call, execute it by:

1. Calling the matching HTTP route, or
2. `from artificial_emotions.agent_tools import dispatch_tool` then `dispatch_tool(name, arguments)`

Minimal mix example request/response: [`examples/emotions_mix_request.json`](../examples/emotions_mix_request.json), [`examples/emotions_mix_response.json`](../examples/emotions_mix_response.json).

LangGraph (or any `bind_tools` graph) can pass the same `tools` array — [§4](#4-langgraph-host-side-optional).

---

## 4. LangGraph (host-side, optional)

`langgraph` is **not** a runtime dependency of `artificial-emotions` (v1.0.0). Install it only in the agent project that will call this stack. This recipe is documentation, not a CI-tested extra.

Load live OpenAI-compatible schemas from `GET /v1/agent/tools` and execute calls via that payload’s `http_fallbacks` against local `emotions serve`. Do not add webhook URLs. Rankings stay **decision aids** under an explicit `ValueProfile` — the graph does not answer the unknowns and does not feel.

**Prereq:** `emotions serve` on `127.0.0.1:8000`. If `CURIOSITY_API_KEY` is set, send `Authorization: Bearer <key>`.

**Host venv only** (not this package):

```bash
pip install langgraph langchain-openai
```

Any chat model with `bind_tools` works; `ChatOpenAI` is an example.

```python
"""Host-side LangGraph loop using GET /v1/agent/tools. Not an artificial-emotions extra."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, MessagesState, StateGraph
from langchain_core.messages import ToolMessage

BASE = os.environ.get("CURIOSITY_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
API_KEY = os.environ.get("CURIOSITY_API_KEY", "")
# Aliases exist on the tools list but share a canonical http_fallbacks key.
ALIASES = {"spark": "provoke_curiosity", "run_curiosity": "rank_unknowns"}


def _headers(extra: dict[str, str] | None = None) -> dict[str, str]:
    headers = {"Accept": "application/json"}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    if extra:
        headers.update(extra)
    return headers


def _request(
    method: str,
    path: str,
    *,
    query: dict[str, Any] | None = None,
    body: dict[str, Any] | None = None,
) -> Any:
    url = BASE + path
    if query:
        url += "?" + urllib.parse.urlencode(
            {k: v for k, v in query.items() if v is not None}
        )
    data = None
    headers = _headers()
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"error": {"code": "http_error", "message": raw[:500]}}


def load_agent_tools() -> tuple[list[dict[str, Any]], dict[str, str]]:
    payload = _request("GET", "/v1/agent/tools")
    fallbacks: dict[str, str] = payload["http_fallbacks"]
    callable_names = set(fallbacks) | set(ALIASES)
    tools = [
        t
        for t in payload["tools"]
        if t.get("type") == "function" and t["function"]["name"] in callable_names
    ]
    return tools, fallbacks


def execute_via_http(
    name: str, args: dict[str, Any], fallbacks: dict[str, str]
) -> Any:
    key = ALIASES.get(name, name)
    spec = fallbacks.get(key)
    if spec is None:
        return {"error": {"code": "no_http_fallback", "message": name}}
    methods, path = spec.split(" ", 1)
    params = dict(args or {})
    for pname, pval in list(params.items()):
        token = "{" + pname + "}"
        if token in path:
            path = path.replace(token, urllib.parse.quote(str(pval), safe="-_"))
            params.pop(pname)
    if "{" in path:
        return {"error": {"code": "missing_path_param", "message": path}}
    if "POST" in methods.split("|"):
        return _request("POST", path, body=params)
    return _request("GET", path, query=params)


def build_graph():
    tools, fallbacks = load_agent_tools()
    llm = ChatOpenAI(model="gpt-4o-mini").bind_tools(tools)

    def agent(state: MessagesState) -> dict[str, Any]:
        return {"messages": [llm.invoke(state["messages"])]}

    def tool_node(state: MessagesState) -> dict[str, Any]:
        last = state["messages"][-1]
        out: list[ToolMessage] = []
        for call in getattr(last, "tool_calls", []) or []:
            result = execute_via_http(call["name"], call.get("args") or {}, fallbacks)
            out.append(
                ToolMessage(
                    content=json.dumps(result, default=str),
                    tool_call_id=call["id"],
                )
            )
        return {"messages": out}

    def route(state: MessagesState) -> str:
        last = state["messages"][-1]
        return "tools" if getattr(last, "tool_calls", None) else END

    graph = StateGraph(MessagesState)
    graph.add_node("agent", agent)
    graph.add_node("tools", tool_node)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", route, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")
    return graph.compile()


if __name__ == "__main__":
    app = build_graph()
    app.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Spark 3 fast unknowns in domain ai under profile "
                        "alignment_lab. Rank; do not answer the questions."
                    ),
                }
            ]
        }
    )
```

### Smoke (no LangGraph required)

```bash
emotions serve
curl -s http://127.0.0.1:8000/v1/agent/tools
```

Expect `format` = `openai.tools`, a non-empty `tools` array, and `http_fallbacks`. This repository does not run LangGraph in CI — do not read the snippet as “verified on every LangGraph release.”

### Equivalent without LangGraph

- **HTTP / OpenAI tools:** [§3](#3-openai-compatible-function-calling) — pass the same `tools` array to any chat-completions host.
- **In-process** (this package already installed; no `emotions serve`):

```python
from artificial_emotions.agent_tools import dispatch_tool, openai_tools

schemas = openai_tools()  # same contract as GET /v1/agent/tools
result = dispatch_tool(
    "provoke_curiosity",
    {"domain": "ai", "n": 3, "fast": True, "profile_name": "alignment_lab"},
)
# Paste result["inject"] into the model. Scores are decision aids, not oracles.
```

---

## 5. Sanity checks

```bash
emotions spark --domain ai --n 3
emotions export unknowns --no-literature --json   # ranked-set JSON; no webhooks
emotions pack check                               # CONTRIBUTING operationalization + why_it_matters
python -c "from artificial_emotions.agent_tools import mcp_tool_list; print(len(mcp_tool_list()))"
emotions-mcp --list-tools
curl -s http://127.0.0.1:8000/v1/agent/tools      # LangGraph recipe smoke (no langgraph extra)
pytest -q
```

---

## Public-repo notes

- Copy `.env.example` → `.env` locally; never commit `.env` or API keys.
- Default spark path needs **no** key.
- OpenAlex literature grounding needs no key (optional `OPENALEX_MAILTO`).
- Optional LLM: set `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL` only in local env or MCP `env`.
- Quality gate: GitHub Actions `ci.yml` (lint + pytest) runs on every PR/push — independent of PyPI publish billing.
