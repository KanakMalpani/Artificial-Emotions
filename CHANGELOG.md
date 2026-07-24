# Changelog

## 0.4.0 — 2026-07-24

Production-ready hardening of the public surface (emotions + API + plugins).

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

### Honesty
- Emotions remain **annotation_only** framing — not felt affect; scores ≠ oracles
