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
 (seeds/packs/LLM)  (OpenAlex/S2)   (heuristic/LLM)
        │                │                │
        └──────────▶ Diversify ◀──────────┘
```

## Modules

| Module | Path | Role |
|--------|------|------|
| models | `models.py` | Schema + ValueProfile presets |
| seeds | `seeds.py` | Curated offline unknowns (multi-domain) |
| packs | `packs.py` | Versioned JSON domain packs |
| generate | `generate.py` | Seed + packs + optional LLM forge |
| openalex / literature | `openalex.py`, `literature.py` | Literature retrieval |
| verify | `verify.py` | Gap status classification |
| scoring | `scoring.py` | Axes + aggregate + gates |
| judge | `judge.py` | Optional LLM scoring / gap reader |
| diversity | `diversity.py` | Near-dup suppression |
| brief | `brief.py` | Investigation briefs |
| pipeline | `pipeline.py` | Orchestration (`CuriosityEngine`) |
| provoke | `provoke.py` | Instant spark + inject pack |
| emotions | `emotions.py` | Catalog / mix / cues (annotation only) |
| preferences | `preferences.py` | Opt-in preference JSONL + thin hints |
| agent_tools | `agent_tools.py` | Shared MCP / OpenAI / HTTP tool schemas |
| mcp_server | `mcp_server.py` | Stdio MCP (stdlib JSON-RPC) |
| api | `api.py` | FastAPI |
| cli | `cli.py` | `curiosity run \| spark \| serve \| …` |
| llm | `llm.py` | Provider-agnostic OpenAI-compatible client |
| config | `config.py` | Central env knobs |
| evals | `evals.py`, `eval_report.py` | Offline expert-eval / composite report |

## Product surfaces

| Surface | Entry |
|---------|--------|
| CLI | `curiosity` |
| MCP | `curiosity-mcp` |
| HTTP | `curiosity serve` → `:8000` |
| OpenAI tools | `GET /v1/agent/tools` or `examples/openai_tools.json` |
| Python | `CuriosityEngine`, `provoke`, emotion helpers |
| Web (optional) | `web/` → `:5173` (proxies API) |

## Trust boundaries

- Network: OpenAlex (public), optional Semantic Scholar, optional OpenAI-compatible endpoint.
- No secrets in repo; API keys via environment only (`.env.example`).
- HTTP does **not** accept `literature_cache_dir` or `llm_base_url` (CLI/env only — path / SSRF hygiene).
- Literature classifier is heuristic — confidence reflected in output.
- Rankings require an explicit `ValueProfile` (defaults provided, not hidden).
- Emotion / mix surfaces are `annotation_only` — not felt affect.

## Extension points

1. Add a domain pack JSON under `artificial_curiosity/packs/` (see CONTRIBUTING).
2. Swap / merge literature backends (`literature_backend=openalex|semantic_scholar|both`).
3. Optional embedding diversity: `pip install '.[embeddings]'`.
4. Preference JSONL → thin re-rank / weight hints (not calibrated learning yet).
5. Keep tool schemas in sync via `agent_tools.py` (MCP, OpenAI JSON, HTTP).

See also: [DESIGN.md](DESIGN.md) · [LIMITS.md](LIMITS.md) · [PLUGINS.md](PLUGINS.md).
