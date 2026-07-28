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
| decompose | `decompose.py` | Curiosity depth: sub-questions, first step, falsifiers, stop rules |
| appraisal | `appraisal.py` | Derives affect *from* a run — emotion as output, with evidence |
| trajectory | `trajectory.py` | Session memory: seen ids, mined terms, dead ends, surprises |
| modulate | `modulate.py` | Bounded, logged config changes driven by affect |
| explore | `explore.py` | The loop: appraise → feel → modulate → remember |
| stances | `stances.py` | Seven non-curiosity questions over one ranked set — views, never re-rankings |
| discover | `discover.py` | Swanson ABC linking — generates questions from a corpus |
| validate | `validate.py` | Time-split retrospective validation with a random baseline |
| affect | `affect.py` | PAD mood, felt simulation, blends and tension |
| pipeline | `pipeline.py` | Orchestration (`CuriosityEngine`) |
| provoke | `provoke.py` | Instant spark + inject pack |
| emotions | `emotions.py` | Catalog / mix / cues (`annotation_only` + `computational_affect`) |
| resources | `resources.py` | Packaged data paths for worksheets / eval fixtures |
| preferences | `preferences.py` | Opt-in preference JSONL + thin hints |
| agent_tools | `agent_tools.py` → `agent_tools_pkg/` | Shared MCP / OpenAI / HTTP tool schemas |
| mcp_server | `mcp_server.py` | Stdio MCP (stdlib JSON-RPC) |
| api | `api.py` → `api_pkg/` | FastAPI (see below) |
| cli | `cli.py` → `cli_pkg/` | `emotions run \| spark \| serve \| …` |
| llm | `llm.py` | Provider-agnostic OpenAI-compatible client |
| config | `config.py` | Central env knobs |
| evals | `evals.py`, `eval_report.py` | Offline expert-eval / composite report |

## HTTP layer

`artificial_emotions.api:app` is the stable entry point (uvicorn target,
`emotions serve`, `TestClient`). It is a thin re-export; the implementation is
split by concern:

| Module | Holds |
|--------|-------|
| `api_pkg/__init__.py` | `create_app()` — middleware, error handlers, router wiring |
| `api_pkg/security.py` | Opt-in API-key middleware and path/key helpers |
| `api_pkg/error_handlers.py` | Exception → stable `{"error": {...}}` envelope |
| `api_pkg/schemas.py` | Pydantic request models (names are public OpenAPI schemas) |
| `api_pkg/routers/meta.py` | `/`, `/health`, `/ready`, `/v1/agent`, `/v1/domains` |
| `api_pkg/routers/profiles.py` | `/v1/profiles`, compare, constitution-compare |
| `api_pkg/routers/curiosity.py` | `/v1/curiosity/run`, `/v1/curiosity/provoke` |
| `api_pkg/routers/preferences.py` | `/v1/preferences/*` |
| `api_pkg/routers/evaluation.py` | `/v1/evals/*`, worksheets, brief critique, `/v1/curiosity/decompose`, `/v1/curiosity/explore` |
| `api_pkg/routers/emotions.py` | `/v1/emotions/*` and the `/v1/epistemic/*` alias |

Routers spell out full paths (no `prefix=`) so any route can be found by
grepping its literal URL. `tests/test_api_wiring.py` pins the served path set,
middleware order, and that every router module is actually included.

## CLI layer

`artificial_emotions.cli:main` backs the `emotions` console script (and the
`curiosity` alias kept for pre-rename configs).

| Module | Holds |
|--------|-------|
| `cli_pkg/__init__.py` | `main()` and the subcommand dispatch table |
| `cli_pkg/parser.py` | Every argparse definition, in one readable place |
| `cli_pkg/commands/ranking.py` | `run`, `spark`, `serve` |
| `cli_pkg/commands/profiles.py` | `profiles`, `compare-profiles` |
| `cli_pkg/commands/worksheets.py` | `critique-brief`, `voi-worksheet`, `surprise-worksheet`, `decompose` |
| `cli_pkg/commands/preferences.py` | `preferences hints \| summarize \| suggest-pair` |
| `cli_pkg/commands/evaluation.py` | `eval spotcheck \| elicit \| gap-status \| report \| cooccur` |
| `cli_pkg/commands/emotions.py` | `emotions` / `epistemic` subcommands |

The bare-flag fallback (`emotions --domain ai` → `run`) reads subcommand names
off the parser rather than a hardcoded list, so the two cannot drift apart.

## Agent tool layer

`artificial_emotions.agent_tools` is the stable import path. Dependencies run
strictly one way — nothing imports backwards:

```
schemas.py → handlers.py → registry.py → mcp_resources.py
```

| Module | Holds |
|--------|-------|
| `agent_tools_pkg/schemas.py` | JSON Schema fragments (MCP `inputSchema` / OpenAI `parameters`) |
| `agent_tools_pkg/handlers.py` | Tool implementations |
| `agent_tools_pkg/registry.py` | `TOOL_SPECS`, tier filtering, `dispatch_tool` |
| `agent_tools_pkg/mcp_resources.py` | `curiosity://` resource list and read |

`TOOL_SPECS` is the single source of truth: the MCP tool list, the OpenAI tool
list, and dispatch all derive from it.

## The affect loop

Elsewhere the affect layer renders weights you supply. The loop inverts that:

```
rank → appraise → feel → modulate → remember → rank
```

| Stage | Module | Contract |
|-------|--------|----------|
| Appraise | `appraisal.py` | Every signal carries `because` + `evidence`. Deterministic. |
| Feel | `emotions.py` / `affect.py` | Signals become a mix with PAD, triads, ambivalence. |
| Modulate | `modulate.py` | Changes **search behaviour**. ValueProfile weights untouched unless `allow_weight_deltas`, then capped at `MAX_WEIGHT_DELTA` and listed. |
| Remember | `trajectory.py` | Boredom needs a past; this is that past. |

**Trust boundary.** Ranking must stay a function of the stated `ValueProfile`.
Affect therefore moves breadth, literature use, decomposition and choice of
ground — not the scoring weights. `tests/test_explore_loop.py` pins that
invariant both ways.

### Stances: the second way an emotion can matter

Modulation is emotion as a *modifier* on curiosity's search. That leaves every
emotion that has nothing useful to say about breadth or literature with no job —
which is how a 54-entry catalog becomes furniture.

A **stance** is the other option: the emotion becomes the question itself. Same
ranked set, a different thing asked of it.

| Stance | Asks | Driven by |
|--------|------|-----------|
| `doubt` | Which of these am I most likely to be wrong about? | skepticism, suspicion, hubris, humility |
| `safety` | Which could hurt someone, and who reviews it? | anxiety, reluctance, compassion |
| `focus` | If I could only pursue one, what exactly would I do first? | absorption, determination, persistence |
| `close` | What should we stop doing, and what do we write down? | disappointment, resignation, satisfaction |
| `taste` | Which are badly posed, regardless of whether they matter? | elegance, parsimony, dissonance, clarity |
| `wonder` | What is most surprising, regardless of whether it is valuable? | wonder, surprise, insight, interest, enjoyment, uncertainty |
| `survey` | Who already owns this ground? | respect, envy, recognition |

**Second trust boundary.** A stance is a *view*. It never rescores or reorders
the ranked set it was handed — every payload carries
`honesty: "stance_view_only"` and disclaims re-ranking, and
`tests/test_stances.py` asserts the input ordering is byte-identical afterwards.

`tests/test_appraisal_coverage.py` closes the loop: **every** appraisable emotion
must either modulate search or drive a stance. Being named and disclaimed does
not count as a use.

## Product surfaces

| Surface | Entry |
|---------|--------|
| CLI | `emotions` |
| MCP | `emotions-mcp` |
| HTTP | `emotions serve` → `:8000` |
| OpenAI tools | `GET /v1/agent/tools` or `examples/openai_tools.json` |
| Python | `CuriosityEngine`, `provoke`, emotion helpers |
| Web (optional) | `web/` → `:5173` (proxies API) |

## Trust boundaries

- Network: OpenAlex (public), optional Semantic Scholar, optional OpenAI-compatible endpoint.
- No secrets in repo; API keys via environment only (`.env.example`).
- HTTP does **not** accept `literature_cache_dir` or `llm_base_url` (CLI/env only — path / SSRF hygiene).
- Literature classifier is heuristic — confidence reflected in output.
- Rankings require an explicit `ValueProfile` (defaults provided, not hidden).
- Emotion cues are `annotation_only`; mixes emit `computational_affect` /
  `felt_simulation` — not biological consciousness or user-affect measurement.

## Extension points

1. Add a domain pack JSON under `artificial_emotions/packs/` (see CONTRIBUTING).
2. Swap / merge literature backends (`literature_backend=openalex|semantic_scholar|both`).
3. Optional embedding diversity: `pip install '.[embeddings]'`.
4. Preference JSONL → thin re-rank / weight hints (not calibrated learning yet).
5. Keep tool schemas in sync via `agent_tools.py` (MCP, OpenAI JSON, HTTP).

See also: [DESIGN.md](DESIGN.md) · [LIMITS.md](LIMITS.md) · [PLUGINS.md](PLUGINS.md).
