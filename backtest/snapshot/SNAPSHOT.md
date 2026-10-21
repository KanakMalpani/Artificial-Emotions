# AE SNAPSHOT (frozen)

**Re-freeze:** this commit supersedes `fe748db` (left in place, not rewritten). It adds the §8 PREREG hash and training cutoff and the §7.2 output hashes (`out.sha256`), per QA bot and Engineering Lead.

- Base commit: `78555c6` (branch `backtest/prereg`), metadata in `backtest/snapshot/ae-pull/`. QA bot verified it PASS and cleared it to freeze.
- Totals: 1,898 parts; 675,298,563,638 bytes; 464,765,485 records; 77,468,745 kept.
- `PULL_FINISHED` at 2026-10-22 03:58:06 IST (`pull.log`).

## Part 0058 quarantine and re-pull
At the 18:28 IST worker switch on 2026-10-21, the kill stopped 0058's download but not the old worker, which kept retrying while the new worker pulled the same part; both wrote the same files. The old 0058 files (and a partial from an interrupted first re-pull attempt) were moved to `.quarantine/` (see `quarantine_manifest.tsv`); nothing was deleted. The re-pull matches the original sha256, bytes and record count, passes `gzip -t`, has 45,142 lines = kept count, and is byte-identical to the quarantined output. QA bot rechecked it: PASS.

## raw.sha256 duplicate
`raw.sha256` has 1,899 lines covering 1,898 unique parts. Lines 173 and 1899 are an intended duplicate (same hash, same path, 0058) from the re-pull; both are kept. Uniqueness checks must count unique paths, not lines. See `ae-pull/raw.sha256.NOTES.md`.

## Known limit
The raw `.gz` files were deleted after filtering, so raw sha256 checks can only compare the hashes in `pull.log` against `raw.sha256`; the raw bytes cannot be re-hashed.

## Lesson for future pulls
On any worker switch, kill the whole process group and confirm no old worker, curl or filter process is alive before re-queuing parts.

## Pre-registration
- `backtest/PREREG.md` sha256: `fbefc77d21156fe2a8584999a1a03f790c71b841bede7a6295bd172b0aae931f` (from `backtest/FREEZE.sha256`).

## Model training cutoff (§8)
Model `grok-4.7-high` (Grok 4.7, reasoning effort high). Documented values, quoted from published sources, no estimate:
- Knowledge cutoff **May 2026**: xAI Grok 4.7 developer guide, https://docs.x.ai/developers/grok-4-7, and models page, https://docs.x.ai/developers/models.
- Pretraining data cutoff **June 2026**, with supplemental-training data generated as late as **August 2026**: Grok 4.7 model card, https://media.x.ai/v1/website/4p7card-5eccc980.pdf (§1.2).
- Training data collected no later than **August 2026**: Public Summary of Training Content for Grok 4.7 (V1, 21 Sep 2026), https://media.x.ai/v1/website/public-summary-of-training-content-for-grok-4.7-ccaa1b02.pdf.
The sources differ by measure; all are recorded as published. All postdate the 2015 cutoff and the 2016-2024 outcome window, so the LLM baseline stays labelled "contaminated upper-bound baseline". The training summary lists OpenAlex metadata among its datasets.

## Outputs
Filtered outputs live at `/workspace/oa/pull/out` on the box and are not in git (no `.gz` data is committed). `out.sha256` holds the sha256 of all 1,898 files there, exactly as stored, with paths relative to the base directory **`/workspace/oa/pull/out`**. Verify with `cd /workspace/oa/pull/out && sha256sum -c <repo>/backtest/snapshot/out.sha256` (expect 1898/1898 OK).

## Integrity
`SNAPSHOT.sha256` holds the sha256 of every file under `ae-pull/`, this file and `out.sha256`. Verification **must be run from `backtest/snapshot/`** (paths are relative to it; running from the repo root fails): `cd backtest/snapshot && sha256sum -c SNAPSHOT.sha256`.
