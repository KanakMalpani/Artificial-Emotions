# AE SNAPSHOT (frozen)

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

## Outputs
Filtered outputs live at `/workspace/oa/pull/out` on the box and are not in git (no `.gz` data is committed).

## Integrity
`SNAPSHOT.sha256` holds the sha256 of every file under `ae-pull/` plus this file; verify from `backtest/snapshot/` with `sha256sum -c SNAPSHOT.sha256`.
