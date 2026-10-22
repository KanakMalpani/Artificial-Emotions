# INCIDENT: AE OpenAlex pull, attempt 1 outputs VOID

Status: draft for QA review. Committed before any re-pull code, per QA bot.

## What happened
- Attempt 1 is the pull frozen in `backtest/snapshot/` (SNAPSHOT.md, base `78555c6`): 1,898 parts,
  `PULL_FINISHED` 2026-10-22 03:58:06 IST, 0058 re-pull verified 04:08:05 IST.
- Its filtered outputs lived only on the box at `/workspace/oa/pull/out` (not in git, by design).
- The box came back up at 2026-10-22 06:11:55 IST (`uptime -s`). Every file under `/workspace/oa/`
  now has mtime 2026-10-22 06:12 IST, and `/workspace/oa/pull/out/` and `/workspace/oa/venv/`
  are absent. `done/` (1,898 markers), `hist/` (1,898 files), `pull.log`, `raw.sha256`,
  `parts.tsv`, `filter_part.py` and `.quarantine/` survived.
- Raw `.gz` files were deleted after filtering by design (SNAPSHOT.md "Known limit").

## Consequence
- `out.sha256` (1,898 lines) can no longer be verified: the files it hashes do not exist.
- Attempt 1's outputs are therefore VOID as evidence. The SNAPSHOT metadata, `out.sha256`,
  `raw.sha256` and `pull.log` stay in git unchanged as the record. Nothing is edited or deleted.
- Root cause of the loss is not established beyond the restart (the same class of event as the
  2026-10-21 ~13:18 IST reboot, logged in `pull.log` line 82). No process deleted `out/` that we know of.

## Remedy (approved by Kanak via Engineering Lead, 2026-10-22)
- Re-pull in batches into `/home/box/oa-repull/` (outside `/workspace`), resumable, with an
  append-only progress manifest committed every 5 batches (manifests only, no data).
- The unchanged `filter_part.py` (sha256 `d2b867c8…93d5`) is reused.
- End check over all 1,898 parts: byte-exact to `out.sha256` keeps the SNAPSHOT; any mismatch
  means a new SNAPSHOT plus DEVIATION-4. `out.sha256` is never edited.

## Lesson
Box-local outputs that a frozen hash refers to must live outside `/workspace` and be re-verified
after every restart before anything downstream relies on them.
