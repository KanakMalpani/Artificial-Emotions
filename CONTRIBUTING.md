# Contributing

Thanks for interest in **Artificial Emotions** — a curiosity layer that ranks valuable *unanswered* questions (not Q&A).

## Setup

```bash
git clone https://github.com/KanakMalpani/Artificial-Emotions.git
cd Artificial-Emotions
python -m venv .venv
# macOS / Linux: source .venv/bin/activate
# Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest -q
```

Optional semantic diversity:

```bash
pip install -e ".[embeddings]"
```

### Tests

```bash
pytest -q                     # full suite (CI default)
pytest tests/e2e -q           # API TestClient + CLI journeys (no OpenAlex)
pytest -m e2e -q              # same via marker
pytest -m "not slow" -q       # full suite minus optional lit smoke
pytest -m slow -q             # optional OpenAlex (skips if offline)
```

CI runs ruff + pytest on every PR/push (`.github/workflows/ci.yml`).

## Guidelines

- Prefer small, focused PRs.
- Keep rankings value-explicit (`ValueProfile`); do not claim value-free scores.
- Never commit `.env`, API keys, PyPI tokens, or local venvs.
- Product docs live in `docs/`. Do not commit private design dumps under `research/` (gitignored).
- Add or update tests when changing gates, gap logic, MCP/tools, emotions, or CLI.
- Update [`docs/LIMITS.md`](docs/LIMITS.md) **before** marketing any new claim.
- Emotions / mixes are **annotation_only** — never claim the system feels.

## Where things live

| Concern | Location |
|---------|----------|
| Shared tool contracts (MCP / OpenAI / HTTP) | `src/artificial_emotions/agent_tools.py` |
| ValueProfile presets | `src/artificial_emotions/models.py` (`VALUE_PROFILE_PRESETS`) |
| Offline seeds | `src/artificial_emotions/seeds.py` |
| Domain packs (JSON) | `src/artificial_emotions/packs/*.json` + `packs.py` |
| Product docs | `docs/` — start at [`docs/INDEX.md`](docs/INDEX.md) |
| Examples / protocols | [`examples/README.md`](examples/README.md) |
| Stuck playbooks | [`docs/ROADMAP.md`](docs/ROADMAP.md) §0→§3→§2 |

## Adding a domain seed

Edit `src/artificial_emotions/seeds.py` (`SEED_QUESTIONS`).

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

## Adding a domain pack

Versioned packs live under `src/artificial_emotions/packs/` (`domain_pack.v1`). Enable with `CuriosityConfig(load_bundled_packs=True)` or `domain_pack_paths=[...]`.

Minimum shape:

```json
{
  "schema_version": "domain_pack.v1",
  "domain": "ai",
  "questions": [
    {
      "id": "ai-pack-01",
      "question": "…",
      "operationalization": "Measurable success criteria (≥20 chars)…",
      "why_it_matters": "…",
      "tags": ["…"]
    }
  ]
}
```

Same quality bar as seeds. Lint with `emotions pack check` (bundled packs) or
`emotions pack check --path your_pack.json`. Template sketch:
[`examples/pack_meta_template.json`](examples/pack_meta_template.json).

### Checklist before opening a seed/pack PR

- [ ] `pytest -q` green
- [ ] `emotions pack check` green (bundled, or `--path` your pack)
- [ ] Operationalization + why_it_matters present
- [ ] No secrets / no `.env`
- [ ] `docs/LIMITS.md` unchanged unless claims changed

## ValueProfile presets

Do not add a “neutral” or value-free profile. New presets must name stakeholders and weights explicitly in `VALUE_PROFILE_PRESETS`.

## Publishing (maintainers)

The package **is** on PyPI as `artificial-emotions` (last upload **1.0.0**; tag `v1.0.0`). Releases remain owner-gated. See [`docs/PUBLISHING.md`](docs/PUBLISHING.md). Do not put tokens in the repo.

## Docs / copy hygiene

When changing public behavior:

1. Update LIMITS if the claim surface changes.
2. Add a PROOFS one-liner if the behavior is demo-worthy.
3. Keep README status table accurate (version, PyPI, honesty).
4. Keep `examples/openai_tools.json` in sync with `agent_tools.py` (regenerate or edit both).
5. Host-side agent recipes (LangGraph, etc.) live in [`docs/PLUGINS.md`](docs/PLUGINS.md). Do **not** add those frameworks as package extras. Include a smoke note (`GET /v1/agent/tools`) — do not claim CI coverage of the host framework.
