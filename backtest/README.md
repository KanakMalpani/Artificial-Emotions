# AE backtest (branch `backtest/prereg`)

This directory holds a pre-registered, frozen protocol for evaluating Artificial Emotions (AE) on historical OpenAlex data. It is documentation and harness code only until a verified snapshot and an approved run exist.

## What AE is and what this backtest tests

Artificial Emotions is a curiosity layer for research: given a domain and seeds, it ranks *unknowns* (gaps between concepts) with evidence and plans, without inventing answers. The product logic lives in `src/artificial_emotions/` (e.g. `discover_links()` in `discover.py`).

This backtest asks whether that engine, run offline on a frozen OpenAlex corpus with a **2015 publication cutoff**, surfaces unknown (A, C) pairs that later show up in the literature (**2016–2024** outcome window) more often than simple baselines.

Methods compared per [PREREG.md](PREREG.md):

- **AE** — `discover_links()` through `LocalCorpusClient` on past-domain JSONL corpora; top 20 unknowns per domain after pooling seeds.
- **Random** — uniform sample of 20 unknowns from the shared pool P_d, averaged over 100 seeds.
- **Citation-trend** — ranks unknowns by sqrt(growth(A)·growth(C)) using 2013–2015 doc counts only.
- **LLM-picked** — Appendix A prompt over P_d via Loop-Engineering's pinned cursor-agent shim (`grok-4.7-high`); median over five repeat calls; labelled **contaminated upper-bound baseline** because training data postdates the cutoff.

Three pack-defined domains (aging biology, materials/catalysis, climate adaptation) share one pinned OpenAlex release. Outcomes use co-mentions in the future corpus (2016–2024): **pursued** (≥5 works) or **highly cited** (top-decile citation norm or fallback rule). Pass/fail is relative to all three baselines in at least two of three domains, plus a pre-1986 Swanson rediscovery check. Full definitions, seeds, and INFRA-FAIL/ABORT rules are in PREREG.md only.

## Status (honest)

| Item | State |
|------|--------|
| Pre-registration | Frozen. `FREEZE.sha256` hashes `PREREG.md`, `DEVIATION.md`, `DEVIATION-2.md`, and `DEVIATION-3.md`. |
| Attempt-1 filtered data | **VOID.** Box restart removed `/workspace/oa/pull/out`; hashes in git cannot be verified against bytes on disk. See [repull/INCIDENT-attempt1-VOID.md](repull/INCIDENT-attempt1-VOID.md). |
| Re-pull | Approved in principle: batched recovery into `/home/box/oa-repull/`, scripts under `repull/` drafted; **not started for production pull**; pending QA and Kanak's approval. |
| Byte reproducibility | `filter_part.py` gzip headers use current mtime, so filtered `.jsonl.gz` sha256 is not byte-stable; end-to-end match to attempt-1 `out.sha256` is unlikely → expect **new SNAPSHOT + DEVIATION-4** after QA decision. See [repull/WORKLOG.md](repull/WORKLOG.md). |
| Backtest run | **None.** No `backtest/results/`, no ranked outputs, no pass/fail. |
| Public claims | **Do not cite this tree as evidence** for AE performance, baselines, or Swanson rediscovery. Metadata and incident records are archival only. |

Snapshot metadata in [snapshot/SNAPSHOT.md](snapshot/SNAPSHOT.md) still documents attempt-1 pull completion (2026-10-22); that record is intentionally not rewritten. The git manifests stay as the record, but `out.sha256` can no longer be checked against any bytes, so nothing downstream may use it until data is re-pulled and re-verified or re-frozen.

## Setup

From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Run backtest unit tests (no network, no data pull):

```bash
python -m pytest -q -p no:cacheprovider tests/backtest
ruff check
```

Read-only integrity checks:

```bash
sha256sum -c backtest/FREEZE.sha256
(cd backtest/snapshot && sha256sum -c SNAPSHOT.sha256)
bash backtest/repull/dry_test.sh
```

`dry_test.sh` is offline; it writes only under `/home/box/oa-repull/dry-*` and does not start a full re-pull.

Inspect the run harness (does not execute a backtest without `--confirm` and verified data):

```bash
python backtest/run_backtest.py --help
```

`run_backtest.py` exposes `--data-dir`, `--hist-dir`, `--concepts-dir`, `--snapshot-sha`, `--out-base`, `--repo-root`, result paths (`--out`, `--log`, `--probe-out`, `--manifest`), and optional `--run-llm` / `--llm-results` for the §4.3 baseline. It always requires `--confirm` and verifies `FREEZE.sha256` before doing work. Default data paths target `/workspace/oa/pull/out` and `/workspace/oa/pull/hist`; with attempt-1 outputs void, those defaults are not usable until a new verified snapshot and on-disk data exist.

Do not run the harness with `--confirm` until QA has signed off on snapshot integrity and on-disk hashes. This README intentionally omits that invocation.

## Protocol flow

1. **Pre-register** — [PREREG.md](PREREG.md) fixes methods, cutoffs, domains, and pass rules before any ranking.
2. **Deviations** — Any protocol or process change is recorded in `DEVIATION*.md` **before** data pulls or runs that depend on it. Current frozen set: `DEVIATION.md`, `DEVIATION-2.md`, `DEVIATION-3.md` (hashed in `FREEZE.sha256`).
3. **Snapshot** — OpenAlex pull metadata, `ae-pull/` manifests, [snapshot/SNAPSHOT.md](snapshot/SNAPSHOT.md), [snapshot/SNAPSHOT.sha256](snapshot/SNAPSHOT.sha256), and [snapshot/out.sha256](snapshot/out.sha256) describe one pinned release and filtered outputs. Verification of `SNAPSHOT.sha256` must be run from `backtest/snapshot/` (paths are relative to that directory).
4. **Gate logs** — Timestamped checks under [logs/](logs/) (`gate-*.log`, reviews). These record QA-style gates; they are not results.
5. **Run** — `run_backtest.py` requires `--confirm`, matching data directories, hash verification against the frozen snapshot, and (for §4.3) the pinned LLM shim. It writes `backtest/run.log`, `backtest/results/*`, and refuses to place outputs inside corpus dirs.
6. **Results** — Only after a successful run; none exist yet.

**Change control:** Every substantive change goes through QA and Kanak's approval. Files listed in `FREEZE.sha256`, `SNAPSHOT.sha256`, and `out.sha256` are **never edited in place**; add a new deviation and/or snapshot generation instead.

**Re-pull:** `repull/repull.sh` and `repull/push_checkpoint.sh` exist for the approved batched recovery workflow into `/home/box/oa-repull/` (resumable batches, progress manifests committed without data). They require QA review and Kanak's approval before any production use. Do not invoke `repull.sh` except under that approval; compare-only modes are not documented here.

**Hashes:** Do not regenerate, edit, or rewrite `FREEZE.sha256`, `SNAPSHOT.sha256`, `out.sha256`, or committed manifests. A mismatch is handled by a new deviation entry and a new snapshot freeze, not by patching hash files.

## Layout (`backtest/`)

| Path | Role |
|------|------|
| [PREREG.md](PREREG.md) | Pre-registered protocol (frozen). |
| [DEVIATION.md](DEVIATION.md), [DEVIATION-2.md](DEVIATION-2.md), [DEVIATION-3.md](DEVIATION-3.md) | Dated protocol/process deviations (frozen). |
| [FREEZE.sha256](FREEZE.sha256) | sha256 of PREREG + DEVIATION files; checked from repo root. |
| [run_backtest.py](run_backtest.py) | Main harness: hash checks, baselines, Swanson test, optional LLM baseline. |
| [cursor_llm.py](cursor_llm.py) | LLM baseline integration (pinned external shim). |
| [snapshot/SNAPSHOT.md](snapshot/SNAPSHOT.md) | Human-readable snapshot record (attempt 1). |
| [snapshot/SNAPSHOT.sha256](snapshot/SNAPSHOT.sha256) | Hashes of `ae-pull/`, SNAPSHOT.md, out.sha256. |
| [snapshot/out.sha256](snapshot/out.sha256) | Expected hashes of 1,898 filtered parts (paths relative to `/workspace/oa/pull/out`). |
| [snapshot/ae-pull/](snapshot/ae-pull/) | Pull logs, `parts.tsv`, `raw.sha256`, quarantine notes (no raw `.gz` in git). |
| [repull/INCIDENT-attempt1-VOID.md](repull/INCIDENT-attempt1-VOID.md) | Why attempt-1 filtered outputs are void. |
| [repull/WORKLOG.md](repull/WORKLOG.md) | Re-pull drafting, dry test, gzip reproducibility finding. |
| [repull/dry_test.sh](repull/dry_test.sh) | Offline smoke tests for re-pull tooling. |
| [repull/repull.sh](repull/repull.sh) | Batched re-pull script (QA + approval before use). |
| [repull/push_checkpoint.sh](repull/push_checkpoint.sh) | Checkpoint manifest helper for re-pull (manifests only). |
| [logs/](logs/) | Gate and review logs (not experimental results). |

Unit tests for the harness live in `tests/backtest/` at the repo root (not under `backtest/`). They exercise toy corpora and guardrails (freeze verification, path refusal, parsing) without calling OpenAlex or live LLM endpoints.

## What is not in this directory

- Frozen filtered OpenAlex JSONL (gigabytes; box-local or future `/home/box/oa-repull/` tree).
- `backtest/results/`, `backtest/run.log`, or raw LLM replies from a completed run.
- Any numeric hit rates, p-values, or PASS/FAIL labels.

Until those exist under a verified snapshot, treat the branch as **protocol + incident recovery in progress**, not as a study result.

## References

- Root project overview: [../README.md](../README.md)
- Rules and thresholds: [PREREG.md](PREREG.md)
- Snapshot and training-cutoff notes: [snapshot/SNAPSHOT.md](snapshot/SNAPSHOT.md)
- Data loss and remedy: [repull/INCIDENT-attempt1-VOID.md](repull/INCIDENT-attempt1-VOID.md)
