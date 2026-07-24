# Contributing

Thanks for interest in Artificial Curiosity.

## Setup

```bash
git clone https://github.com/KanakMalpani/Artificial-Curiosity.git
cd Artificial-Curiosity
python -m venv .venv
# macOS / Linux: source .venv/bin/activate
# Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest -q
```

### End-to-end suite

Fast-path e2e (API TestClient + CLI `main`, no OpenAlex) lives under `tests/e2e/`:

```bash
pytest tests/e2e -q          # API + CLI journeys
pytest -m e2e -q             # same via marker
pytest -m "not slow" -q      # full suite minus optional lit smoke
pytest -m slow -q            # optional OpenAlex run (skips if offline)
```

Optional semantic diversity:

```bash
pip install -e ".[embeddings]"
```

## Guidelines

- Prefer small, focused PRs.
- Keep rankings value-explicit (`ValueProfile`); do not claim value-free scores.
- Never commit `.env`, API keys, PyPI tokens, or local venvs.
- Product docs live in `docs/`; long research notes belong in `research/` (optional reading).
- Add or update tests when changing gates, gap logic, MCP/tools, or CLI.
- Update `docs/LIMITS.md` before marketing any new claim.

## Publishing (maintainers)

PyPI releases are owner-gated. See [`docs/PUBLISHING.md`](docs/PUBLISHING.md) for Trusted Publishing / `PYPI_API_TOKEN` workflow details. Do not put tokens in the repo.

## Surfaces to keep in sync

Shared tool contracts live in `src/artificial_curiosity/agent_tools.py` (MCP, OpenAI tools JSON, HTTP `/v1/agent/tools`).

Named ValueProfile presets live in `src/artificial_curiosity/models.py` (`VALUE_PROFILE_PRESETS`).

## Adding a domain seed (quality bar)

Seeds power the offline demo path. Edit `src/artificial_curiosity/seeds.py`.

### Schema (required fields)

| Field | Requirement |
|-------|-------------|
| `question` | Clear investigable unknown (≥12 chars); one primary unknown |
| `domain` | One of: ai, biology, physics, climate, medicine, materials, social, energy, general |
| `operationalization` | How we would know the question was answered (measurable success criteria) |
| `why_it_matters` | Stakeholder-relevant reason (not “sounds interesting”) |
| `tags` | Short topical tags for OpenAlex / diversity |
| `assumptions` / `enabling_questions` | Optional but encouraged |

### Quality bar (reject if missing)

1. **One primary unknown** — not a multi-program research agenda (F9).
2. **Operationalization** — falsifiable / measurable; not pure philosophy.
3. **Not already textbook-solved** — prefer frontiers the seed author believes are open.
4. **Dual-use awareness** — avoid seeds that primarily teach harm pathways; risk gate will hard-reject high-risk language (F10).

### Domain pack format (lightweight)

Until versioned packs ship (v0.3+), a “pack” is: a domain key in `SEED_QUESTIONS` plus ≥2 curated `UnansweredQuestion` entries meeting the bar above. Optional topic filters go through `seeds_for(domain, topic=...)`.

### Checklist before opening a seed PR

- [ ] `pytest -q` green
- [ ] New seed has operationalization + why_it_matters
- [ ] No secrets / no `.env`
- [ ] LIMITS unchanged unless claims changed

## ValueProfile presets

Do not add a “neutral” or value-free profile. New presets must name stakeholders and weights explicitly in `VALUE_PROFILE_PRESETS`.
