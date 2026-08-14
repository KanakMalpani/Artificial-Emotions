# Threat model — local `emotions serve`

Honest bounds for **v1.0.0**. This document describes the HTTP surface started by
`emotions serve` (`artificial_emotions.api:app`). It is a **local soft guard**,
not a production SLO, not a WAF, and not a claim that the API is
production-ready or multi-tenant. ROADMAP §7.5 “enterprise” here means this
**local-v1** posture (opt-in keys, quota, audit) — not SSO, TLS, or SLOs.

Read with [`LIMITS.md`](LIMITS.md) (product honesty) and
[`ARCHITECTURE.md`](ARCHITECTURE.md) (trust boundaries). Machine pointer:
`GET /v1/agent` → `honesty` + `threat_model`.

## What this is / is not

| This document | Not this document |
|---------------|-------------------|
| Operator model for a **loopback** FastAPI process | Public multi-tenant API design |
| Controls that **exist in code today** (rate limit, CORS, auth, opt-in quota, opt-in audit) | TLS, WAF, shared rate limits, uptime SLOs |
| Residual risk if you bind beyond localhost | Production-ready public API |
| Local-v1 baseline for ROADMAP §7.5 “enterprise” | Proof gate “production-ready enterprise” (ROADMAP §10) |

Default bind is `127.0.0.1:8000` (`--host` / `CURIOSITY_HOST`). Binding
`0.0.0.0` without `CURIOSITY_API_KEY` is operator risk.

## Assets

| Asset | Why it matters | How it shows up |
|-------|----------------|-----------------|
| Operator LLM credentials | Spend / leak via outbound Chat Completions | Env `LLM_API_KEY`; HTTP `use_llm=true` uses **env** base URL, never a client URL |
| Optional S2 key | Quota / identity at Semantic Scholar | `S2_API_KEY` / `SEMANTIC_SCHOLAR_API_KEY` |
| HTTP API keys | Gate `/v1` when configured | `CURIOSITY_API_KEY` / `CURIOSITY_API_KEYS` (never logged) |
| Local memory JSON | Usage history on this machine | Default `~/.artificial_emotions/memory.json`; HTTP does **not** auto-persist |
| Ranked unknowns / briefs | Research intent, not usually secrets | `/v1/curiosity/*`, stances, worksheets |
| Preference / outcome events | Labeled axes the operator posted | `POST /v1/preferences/*` — **inline only**, no filesystem paths |
| OpenAPI /docs | Attack surface map | Open without a key (probe list) |

Dual-use filters on ranked questions are **heuristic product controls**, not an
HTTP security boundary. Residual evasion stays in LIMITS.

## Trust boundaries

```
[operator / local agent]
        │  loopback HTTP  (default 127.0.0.1)
        ▼
 AuditMiddleware → RateLimitMiddleware → OptionalApiKeyMiddleware → CORSMiddleware → routers
        │
        ├─ outbound: OpenAlex (public), optional Semantic Scholar, optional LLM host
        └─ disk: memory.json / temperament.toml only on explicit HTTP path overrides;
           opt-in audit JSONL when CURIOSITY_AUDIT_LOG is set (names + status only)
```

Middleware order is load-bearing (Starlette: last-added is outermost):
**audit → rate limit → auth → CORS**. Audit is outermost so 401/429 still
reach the log. Pinned in `tests/test_api_wiring.py`.

**In scope:** the FastAPI process and its env.

**Out of scope here:** MCP stdio (`emotions-mcp`) as an HTTP limiter (stdio is
a local process; opt-in `CURIOSITY_AUDIT_LOG` still records MCP tool names +
status); CLI `emotions explore` persistence; literature classifiers as
biosafety; phenomenal affect.

## Controls that ship (v1.0.0)

### Bind default

`emotions serve` defaults `--host 127.0.0.1`. Loopback is the intended demo.
Non-local bind is an operator choice, not a hardened mode.

### Auth — opt-in

Unset `CURIOSITY_API_KEY` / `CURIOSITY_API_KEYS` / alias
`ARTIFICIAL_CURIOSITY_API_KEY` → **all routes open** (local CLI DX).

When any key is set, routes outside the open list need
`Authorization: Bearer <key>` or `X-API-Key`. Compare is constant-time
(`secrets.compare_digest`); mismatch → **401** `{ "error": { "code": "auth_required" } }`.

Open list (auth **and** rate-limit exempt): `/`, `/health`, `/ready`, `/docs`,
`/openapi.json`, `/redoc`, plus `/docs/` and `/redoc/` prefixes only
(`is_auth_open_path` — not `startswith("/docs")` against `/docsEvil`).

`/health` reports `api_auth_required` and redacts LLM base URL host
(`scheme://[redacted]`).

### Rate limit — in-process, per client host

`CURIOSITY_API_RATE_LIMIT_PER_MINUTE` (default **60** / 60s sliding window;
`0` disables). Keyed by `request.client.host`. **429** with `Retry-After` and
`error.code = rate_limited`.

This is a **per-process** deque, not a distributed limiter. NAT / reverse-proxy
clients often share one host key. Multi-instance deployments do not share the
window. Not a WAF.

### Quota — opt-in, per matched API key

Unset `CURIOSITY_API_QUOTA_REQUESTS` or set `0` → **no quota** (local DX
unchanged). When set to a positive integer, each **matched** API key has an
in-process sliding-window budget (`CURIOSITY_API_QUOTA_WINDOW_S`, default
**86400**). Exceeding it returns **429** `{ "error": { "code": "quota_exceeded" } }`
with `Retry-After`.

Open local serve (no keys configured) does **not** apply a quota — there is no
key to bucket. Unknown / unmatched keys are not bucketed. Same process-memory
limits as the host rate limit: not a billing meter, not multi-tenant, not
shared across instances.

### Audit JSONL — opt-in, names + status, default off

Unset `CURIOSITY_AUDIT_LOG` → **off**. When set to a file path, append JSONL
records of HTTP method+path and MCP tool name plus status. Never request or
response bodies, headers, query strings, or API keys. Probe paths (`/health`,
`/ready`, `/docs`, …) are skipped. Fail-soft: a bad path must not break HTTP.
Local operator log, not a SIEM. `/health` reports `audit_log_enabled` as a
boolean only — never the path.

### CORS — deny by default

`CURIOSITY_CORS_ORIGINS` default **empty** (no `Access-Control-Allow-Origin`).
Opt-in comma list, e.g. `http://127.0.0.1:3000`. `*` is still accepted if the
operator sets it; credentials are then off.

This replaced the old web-demo default of `*`. Browser demos must opt in
explicitly. CORS is not authentication.

### Request-shape hygiene (already in `/v1`)

| Guard | Where |
|-------|--------|
| No `llm_base_url` on HTTP bodies | SSRF / key leak — env/CLI only |
| No `literature_cache_dir` on HTTP bodies | Path injection — env/CLI only |
| No `webhook_url` / callback URLs on `POST /v1/export/unknowns` | SSRF — file / JSON body is the v1 export path |
| Preference hints/summarize | Inline events only (max 500) |
| Memory `forget` / `reset` | `confirm=true`; HTTP explore does not auto-write |
| Structured errors | `{ "error": { "code", "message", "details?" } }` — no secrets |

## Local-v1 vs production enterprise

ROADMAP §7.5 “enterprise” at **1.0.0** is this **local-v1** baseline: opt-in
keys, in-process rate limit, CORS deny, opt-in per-key quota, opt-in audit
JSONL. Unset quota/audit keeps current local DX. It is **not** multi-tenant
SSO, TLS, a WAF, or an SLO.

| Control | Shape at 1.0.0 | Status |
|---------|----------------|--------|
| **Quota** | Per-key budget (`CURIOSITY_API_QUOTA_*`); **429** `quota_exceeded` when exceeded | **Shipped, opt-in.** Unset/0 = no quota. |
| **Audit JSONL** | Opt-in log of HTTP/MCP **tool names + status**; never secret bodies; default off | **Shipped, opt-in.** Unset = off. |

Do not treat this file as a production SLO or a multi-tenant design.

## Residual risks (accepted for local DX)

| Risk | Why it remains | Operator move |
|------|----------------|---------------|
| Open API when keys unset | Demo DX | Set a key before any non-local bind |
| Rate limit is per process / per host | In-memory sliding window | Reverse proxy / WAF if you expose the port |
| Quota is per process / per matched key | In-memory window; no key → no bucket | Opt-in only; not a shared billing meter |
| Audit JSONL is local names+status | Opt-in file; not a SIEM; default off | Set `CURIOSITY_AUDIT_LOG` if you want a log |
| CORS `*` still possible | Explicit opt-in | Do not set `CURIOSITY_CORS_ORIGINS=*` on a shared bind |
| LLM spend via `use_llm=true` | Keys live in the serve process env | Keep keys off, or require API key + do not bind `0.0.0.0` |
| `POST /v1/imagination/transfer` `corpus_path` | Trusted/local path read (CLI parity) | Prefer inline `corpus`; do not expose HTTP |
| Memory `path` on forget/reset/dream | Optional local JSON path | Default path + `confirm=true`; `CURIOSITY_NO_MEMORY=1` opts out |
| `/docs` open when auth is on | Probe/DX | Fine on loopback; not a public catalog |
| No TLS in-process | Uvicorn plaintext | Put TLS on a reverse proxy if you leave localhost |
| No multi-tenant isolation | One process, one env | Do not share a serve with untrusted tenants |
| Dual-use heuristic | Product filter, not a WAF | LIMITS residual; not a serve control |

## Operator checklist (local)

1. Leave the default bind (`127.0.0.1`) unless you know you need otherwise.
2. Before `--host 0.0.0.0` or a LAN bind: set `CURIOSITY_API_KEY` (or
   `CURIOSITY_API_KEYS`).
3. Keep CORS empty unless a **specific** browser origin needs it.
4. Keep `CURIOSITY_API_RATE_LIMIT_PER_MINUTE` at the default unless you are
   debugging; `0` disables the soft guard.
5. Do not put `llm_base_url` or cache directories in HTTP clients — they are
   rejected by design.
6. Quota and audit are **opt-in local knobs**, not a production control plane.
   Set `CURIOSITY_API_QUOTA_REQUESTS` and `CURIOSITY_AUDIT_LOG` only when you
   want them; unset keeps demo DX.

## Proof this is not an SLO

There is no availability target, no multi-instance budget, no TLS termination
in-tree, and no claim that auth+CORS+rate-limit equal a hardened public API.
ROADMAP §10 still requires auth, quotas, audit, threat model, **and SLOs**
before “production-ready enterprise.” Local-v1 quota/audit exist; SLOs,
TLS, and multi-tenant isolation do not. This file is the local threat model
only.

See also: [`LIMITS.md`](LIMITS.md) § Security posture · [`PLUGINS.md`](PLUGINS.md)
HTTP notes · `.env.example`.
