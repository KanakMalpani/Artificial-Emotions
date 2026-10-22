# AE backtest (pre-registered, not yet run)

Branch: `backtest/prereg`

> **Re-pull pending** (QA and Kanak approval). **No backtest has been run.** **No results exist.** **Do not cite this directory as evidence of AE performance.**

## What it tests

Artificial Emotions is a curiosity layer for research: given a domain and seeds, it ranks unknowns (gaps between concepts) with evidence and plans, without inventing answers. The product logic lives in `src/artificial_emotions/` (e.g. `discover_links()` in `discover.py`).

This backtest asks whether that engine, run offline on a frozen OpenAlex corpus with a 2015 publication cutoff, surfaces unknown (A, C) pairs that later show up in the literature (2016–2024 outcome window) more often than simple baselines.

Methods compared per [PREREG.md](PREREG.md):

- AE — `discover_links()` through `LocalCorpusClient` on past-domain JSONL corpora; top 20 unknowns per domain after pooling seeds.
- Random — uniform sample of 20 unknowns from the shared pool P_d, averaged over 100 seeds.
- Citation-trend — ranks unknowns by sqrt(growth(A)·growth(C)) using 2013–2015 doc counts only.
- [LLM-picked baseline (PREREG §4.3)](PREREG.md) — Appendix A prompt over P_d via Loop-Engineering's pinned cursor-agent shim (`grok-4.7-high`); median over five repeat calls; contaminated upper-bound baseline because training data postdates the cutoff.

Domains, outcome, and pass rule ([PREREG.md](PREREG.md) §2, §3, §5):

- Domains — three pack-defined domains (aging biology, materials/catalysis, climate adaptation) on one pinned OpenAlex release.
- Outcome — co-mentions in the future corpus (2016–2024): pursued (≥5 works) or highly cited (top-decile citation norm or fallback rule).
- Pass rule — relative to all three baselines in at least two of three domains, plus a pre-1986 Swanson rediscovery check. Full definitions, seeds, and INFRA-FAIL/ABORT rules are in PREREG.md only.

An unknown pair (A, C) is a seed concept A and a candidate concept C linked through a bridge B (Swanson ABC). P_d is the shared candidate pool of unknown (A, C) pairs for domain d (PREREG §3).

## Status

| Item | State |
|------|--------|
| Pre-reg | **frozen** |
| Attempt-1 data | **VOID** |
| Re-pull | **pending** |
| Run | **none** |
| Results | **none** |
| Citable | **no** |

Not in this directory: frozen filtered OpenAlex JSONL (gigabytes; box-local or future `/home/box/oa-repull/` tree); `backtest/results/`, `backtest/run.log`, or raw LLM replies from a completed run; any numeric hit rates, p-values, or PASS/FAIL labels. Until those exist under a verified snapshot, treat the branch as protocol plus incident recovery in progress, not as a study result.

### Data incident

Attempt-1 filtered outputs are void (box restart removed `/workspace/oa/pull/out`; git hashes cannot be verified against bytes on disk). See [repull/INCIDENT-attempt1-VOID.md](repull/INCIDENT-attempt1-VOID.md).

`filter_part.py` gzip headers use current mtime, so filtered `.jsonl.gz` file sha256 is not byte-stable; a byte match to attempt-1 `out.sha256` is not achievable. See [repull/WORKLOG.md](repull/WORKLOG.md).

[repull/DEVIATION-4.md](repull/DEVIATION-4.md) (DRAFT, pending Kanak) declares a new SNAPSHOT replacing attempt 1's; integrity is checked by decompressed-content sha256. Evidence is under [repull/evidence/](repull/evidence/).

Snapshot metadata in [snapshot/SNAPSHOT.md](snapshot/SNAPSHOT.md) still documents attempt-1 pull completion (2026-10-22); that record is intentionally not rewritten. Git manifests stay as the archival record, but `out.sha256` cannot be checked against on-disk bytes until data is re-pulled, re-verified, and re-frozen.

## Setup

Do not:

- Run `run_backtest.py` with `--confirm` — needs a QA-verified snapshot on disk (approved by QA and Kanak).
- Run `repull.sh` — production pull of 1898 parts; each push needs Kanak's DM approval (approved by QA and Kanak).
- Edit `FREEZE.sha256`, `SNAPSHOT.sha256`, `out.sha256`, or committed manifests — they are the frozen record; changes go via a new DEVIATION/SNAPSHOT (approved by QA and Kanak).

Install — from the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Tests (offline):

```bash
python -m pytest -q -p no:cacheprovider tests/backtest
ruff check
```

Integrity checks (read-only):

```bash
sha256sum -c backtest/FREEZE.sha256
(cd backtest/snapshot && sha256sum -c SNAPSHOT.sha256)
bash backtest/repull/dry_test.sh
```

`dry_test.sh` is offline; it writes only under `/home/box/oa-repull/dry-*` and does not start a full re-pull.

Harness help (does nothing without `--confirm`):

```bash
python backtest/run_backtest.py --help
```

See `python backtest/run_backtest.py --help` for flags (`--data-dir`, `--hist-dir`, `--confirm`, snapshot verification, result paths, optional LLM baseline). Default data paths target `/workspace/oa/pull/out` and `/workspace/oa/pull/hist`; with attempt-1 outputs void, those defaults are not usable until a new verified snapshot and on-disk data exist.

## Protocol flow

1. Pre-register — [PREREG.md](PREREG.md) fixes methods, cutoffs, domains, and pass rules before any ranking.
2. Deviations — Any protocol or process change is recorded in `DEVIATION*.md` before data pulls or runs that depend on it. Current frozen set: `DEVIATION.md`, `DEVIATION-2.md`, `DEVIATION-3.md` (hashed in `FREEZE.sha256`).
3. Snapshot — OpenAlex pull metadata, `ae-pull/` manifests, [snapshot/SNAPSHOT.md](snapshot/SNAPSHOT.md), [snapshot/SNAPSHOT.sha256](snapshot/SNAPSHOT.sha256), and [snapshot/out.sha256](snapshot/out.sha256) describe one pinned release and filtered outputs. Verification of `SNAPSHOT.sha256` must be run from `backtest/snapshot/` (paths are relative to that directory).
4. Gate logs — Timestamped checks under [logs/](logs/) (`gate-*.log`, reviews). These record QA-style gates; they are not results.
5. Run — `run_backtest.py` requires `--confirm`, matching data directories, hash verification against the frozen snapshot, and (for the [LLM-picked baseline (PREREG §4.3)](PREREG.md)) the pinned LLM shim. It writes `backtest/run.log`, `backtest/results/*`, and refuses to place outputs inside corpus dirs.
6. Results — Only after a successful run; none exist yet.

Re-pull: `repull/repull.sh` and `repull/push_checkpoint.sh` support batched recovery into `/home/box/oa-repull/` (resumable batches, progress manifests committed without data). Use only under QA review and Kanak's approval.

## Layout (`backtest/`)

| Path | Role | Frozen |
|------|------|--------|
| [PREREG.md](PREREG.md) | Pre-registered protocol. | yes |
| [DEVIATION.md](DEVIATION.md), [DEVIATION-2.md](DEVIATION-2.md), [DEVIATION-3.md](DEVIATION-3.md) | Dated protocol/process deviations. | yes |
| [repull/DEVIATION-4.md](repull/DEVIATION-4.md) | Draft deviation for attempt-2 snapshot and content-sha integrity (pending Kanak). | no |
| [FREEZE.sha256](FREEZE.sha256) | sha256 of PREREG + DEVIATION files; checked from repo root. | yes |
| [run_backtest.py](run_backtest.py) | Main harness: hash checks, baselines, Swanson test, optional LLM baseline. | no |
| [cursor_llm.py](cursor_llm.py) | LLM baseline integration (pinned external shim). | no |
| [snapshot/SNAPSHOT.md](snapshot/SNAPSHOT.md) | Human-readable snapshot record (attempt 1). | yes |
| [snapshot/SNAPSHOT.sha256](snapshot/SNAPSHOT.sha256) | Hashes of `ae-pull/`, SNAPSHOT.md, out.sha256. | yes |
| [snapshot/out.sha256](snapshot/out.sha256) | Expected hashes of 1,898 filtered parts (paths relative to `/workspace/oa/pull/out`). | yes |
| [snapshot/ae-pull/](snapshot/ae-pull/) | Pull logs, `parts.tsv`, `raw.sha256`, quarantine notes (no raw `.gz` in git). | yes |
| [repull/INCIDENT-attempt1-VOID.md](repull/INCIDENT-attempt1-VOID.md) | Why attempt-1 filtered outputs are void. | no |
| [repull/WORKLOG.md](repull/WORKLOG.md) | Re-pull drafting, dry test, gzip reproducibility finding. | no |
| [repull/evidence/](repull/evidence/) | Logs supporting DEVIATION-4 (e.g. gzip MTIME). | no |
| [repull/baselines/](repull/baselines/) | Attempt-1 baseline manifests for re-pull comparison. | no |
| [repull/dry_test.sh](repull/dry_test.sh) | Offline smoke tests for re-pull tooling. | no |
| [repull/repull.sh](repull/repull.sh) | Batched re-pull script (QA + approval before use). | no |
| [repull/push_checkpoint.sh](repull/push_checkpoint.sh) | Checkpoint manifest helper for re-pull (manifests only). | no |
| [logs/](logs/) | Gate and review logs (not experimental results). | no |

Unit tests for the harness live in `tests/backtest/` at the repo root (not under `backtest/`). They exercise toy corpora and guardrails (freeze verification, path refusal, parsing) without calling OpenAlex or live LLM endpoints.

## References

- Root project overview: [../README.md](../README.md)
- Rules and thresholds: [PREREG.md](PREREG.md)
- Snapshot and training-cutoff notes: [snapshot/SNAPSHOT.md](snapshot/SNAPSHOT.md)
- Data loss and remedy: [repull/INCIDENT-attempt1-VOID.md](repull/INCIDENT-attempt1-VOID.md)
