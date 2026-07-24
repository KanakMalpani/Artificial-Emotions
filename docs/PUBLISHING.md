# Publishing to PyPI

Package name: **`artificial-curiosity`** · Version: see `pyproject.toml` (currently **`0.4.0`**).

**Status:** not on PyPI yet — do not document `pip install artificial-curiosity` as a public path until `https://pypi.org/project/artificial-curiosity/` resolves.

Never store PyPI tokens in the repo or commit `.env` / credentials. For HTTP demos, unset `CURIOSITY_API_KEY` is fine on localhost only — set a key before any non-local bind.

## Preferred: Trusted Publishing (OIDC)

Once configured, GitHub Actions can publish without a long-lived API token.

1. On [PyPI](https://pypi.org/manage/account/publishing/), add a **Trusted Publisher** for this project:
   - Owner: `KanakMalpani`
   - Repository: `Artificial-Curiosity`
   - Workflow: `publish.yml`
   - Environment: leave blank (or match a GitHub Environment if you add one later)
2. In `.github/workflows/publish.yml`, enable OIDC by setting job `permissions.id-token: write` and remove the `password:` input from `pypa/gh-action-pypi-publish` (or keep token as fallback only while migrating).
3. Create a GitHub Release / tag `v*` matching `pyproject.toml` (e.g. `v0.4.0`).

## Current path: API token (repository secret)

The publish workflow uploads with `secrets.PYPI_API_TOKEN` via [pypa/gh-action-pypi-publish](https://github.com/pypa/gh-action-pypi-publish).

1. Create a PyPI API token (project-scoped preferred once the project exists).
2. Add it as a GitHub Actions **repository secret** named `PYPI_API_TOKEN` (Settings → Secrets and variables → Actions).
3. Trigger publish (see below). Do not paste the token into issues, PRs, or chat logs.

## Triggers

| Event | Behavior |
|-------|----------|
| GitHub Release published | Build + upload to PyPI |
| Push tag `v*` (e.g. `v0.4.0`) | Build + upload to PyPI |
| `workflow_dispatch` with dry-run | Build only |
| `workflow_dispatch` with dry-run off | Build + upload |
| Pull request (packaging paths) | Build only (no upload) |

## Local build smoke (no upload)

```bash
pip install build
python -m build
pip install dist/artificial_curiosity-*.whl
python -c "import artificial_curiosity; print(artificial_curiosity.__version__)"
```

## First-time project creation

If `https://pypi.org/project/artificial-curiosity/` does not exist yet, the first successful upload (with a user or project token that can create projects) registers it. After that, prefer a project-scoped token or Trusted Publishing.

## Checklist before tagging

- [ ] `version` in `pyproject.toml` and `__version__` in `src/artificial_curiosity/__init__.py` match
- [ ] Tag is `v` + that version (e.g. `v0.4.0`)
- [ ] `pytest -q` green
- [ ] `docs/LIMITS.md` / ROADMAP updated only after a successful publish

## Troubleshooting

### Actions job fails in ~2s with zero steps

Annotation typically says:

> The job was not started because recent account payments have failed or your spending limit needs to be increased.

Fix in GitHub → Settings → Billing & plans (update payment method / raise Actions spending limit), wait a few minutes, then re-run:

```bash
gh run rerun <run-id> --failed
# or
gh workflow run publish.yml -f dry_run=false
```

Until Actions can start runners, PyPI upload via this workflow cannot complete. Local `python -m build` still works for smoke; do not claim PyPI publish until `https://pypi.org/project/artificial-curiosity/` resolves.