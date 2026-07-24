# Changelog

## 0.4.0 — 2026-07-24

Production-ready hardening of the public surface (emotions + API + plugins).

### Docs / packaging surface (same release line)
- World-class README + docs INDEX / CONTRIBUTING / examples index aligned to v0.4.0
- ROADMAP_SUMMARY + PUBLISHING version pins corrected (were stale at 0.3.1)
- Honesty: not on PyPI; emotions annotation_only; scores ≠ oracles

### Added
- Central `artificial_curiosity.config` (env knobs: LLM_*, CURIOSITY_API_KEY, timeouts, CORS)
- Structured errors (`CuriosityError` + stable codes) and HTTP exception handlers
- `GET /ready` readiness checks; richer `/health` (version, timeouts, auth/cors summary)
- CI workflow (`.github/workflows/ci.yml`): ruff + pytest on PR/push (separate from publish)
- Stdlib logging on optional lit/LLM/embedding soft-fails

### Changed
- Package version **0.4.0**; Development Status classifier → Beta
- Dependency ranges clarified (`pydantic`/`fastapi`/`uvicorn` upper bounds; extras `dev`, `embeddings`)
- Emotion mix/catalog/annotate raise typed `CuriosityError` (still subclasses `ValueError`)
- Auth reject responses use `{ "error": { "code": "auth_required", … } }`
- Regenerated `examples/openai_tools.json` to include emotion catalog/mix tools
- HTTP no longer accepts `literature_cache_dir` or `llm_base_url` (CLI/env only — path injection / SSRF)
- `/ready` returns **503** when checks fail

### Honesty
- Emotions remain **annotation_only** framing — not felt affect; scores ≠ oracles
