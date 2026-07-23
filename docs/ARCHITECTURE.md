# Architecture

```
┌─────────────┐   ┌──────────────┐   ┌─────────────┐
│ ValueProfile│──▶│ Curiosity    │──▶│ Ranked Qs + │
│ Domain/Topic│   │ Engine       │   │ Briefs      │
└─────────────┘   └──────┬───────┘   └─────────────┘
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
   Generate         Verify Gap        Score+Gate
   (seeds/LLM)      (OpenAlex)     (heuristic/LLM)
        │                │                │
        └──────────▶ Diversify ◀──────────┘
```

## Modules

| Module | Path | Role |
|--------|------|------|
| models | `models.py` | Schema + value profile |
| seeds | `seeds.py` | Curated offline unknowns (multi-domain) |
| generate | `generate.py` | Seed + optional LLM forge |
| openalex | `openalex.py` | Literature retrieval |
| verify | `verify.py` | Gap status classification |
| scoring | `scoring.py` | Axes + aggregate + gates |
| judge | `judge.py` | Optional LLM scoring |
| diversity | `diversity.py` | Near-dup suppression |
| brief | `brief.py` | Investigation briefs |
| pipeline | `pipeline.py` | Orchestration |
| provoke | `provoke.py` | Instant spark + inject pack |
| agent_tools | `agent_tools.py` | Shared MCP / OpenAI / HTTP tool schemas |
| mcp_server | `mcp_server.py` | Stdio MCP (stdlib JSON-RPC) |
| api | `api.py` | FastAPI |
| cli | `cli.py` | `curiosity run \| spark \| serve` |
| llm | `llm.py` | Provider-agnostic OpenAI-compatible client |

## Product surfaces

| Surface | Entry |
|---------|--------|
| CLI | `curiosity` |
| MCP | `curiosity-mcp` |
| HTTP | `curiosity serve` → `:8000` |
| OpenAI tools | `GET /v1/agent/tools` or `examples/openai_tools.json` |
| Python | `CuriosityEngine`, `provoke` |

## Trust boundaries

- Network: OpenAlex (public), optional OpenAI-compatible endpoint.
- No secrets in repo; API keys via environment only.
- Literature classifier is heuristic — confidence reflected in output.
- Rankings require an explicit `ValueProfile` (defaults provided, not hidden).

## Extension points

1. Swap OpenAlex for Semantic Scholar / other literature APIs.
2. Add embedding-based diversity (replace Jaccard).
3. Add human preference logging → learn value profile weights.
4. Add longitudinal outcome tracking for calibration.
