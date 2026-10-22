# Deviation 4 (DRAFT, pending Kanak's approval)

Written 2026-10-22 (IST), **before any part of the re-pull is pulled**. Ruled by Engineering Lead, pending Kanak.
Not yet frozen; not listed in `backtest/FREEZE.sha256`. Context: [INCIDENT-attempt1-VOID.md](INCIDENT-attempt1-VOID.md).

## 1. Decision
The attempt-2 re-pull (`repull.sh`, into `/home/box/oa-repull/`) produces a **new SNAPSHOT that replaces attempt 1's**.
Attempt 1's files (`backtest/snapshot/*`, including `out.sha256`) stay in git unchanged as the record. `out.sha256` and
`/workspace/oa/pull/filter_part.py` (sha256 `d2b867c834a9019c1daffa2ced920b9a53b0b9dafb8e147ff43a319f00ee93d5`) are not edited.

## 2. Why: filtered files are not byte-reproducible
`filter_part.py` writes its output with Python's `gzip.open(...)`, which stores the current time in the gzip header MTIME field
(bytes at 0-based offsets 4-7). Running it again on identical input gives identical decompressed content but a different file sha256.
Attempt 1's output files were lost, so a byte-exact match to `out.sha256` is not achievable; declaring that now, before pulling,
avoids a post-hoc deviation.

Evidence ([evidence/gzip-mtime-20261022-145048-IST.log](evidence/gzip-mtime-20261022-145048-IST.log), run 2026-10-22 14:50 IST,
unchanged filter, input `updated_date=2016-07-22/part_0000.gz`, raw sha256 equal to attempt 1's `raw.sha256` line):
- Two runs 3 s apart, same output filename: file sha256 `81cc7567…d43b` vs `f7464996…2b86`; decompressed-content sha256 both
  `e8817919…dfd17`; records 7/7, kept 2/2 (= attempt 1's pull.log).
- `cmp -l` shows one differing byte at cmp offset 5 (1-based) = 0-based offset 4, inside the MTIME field; result line:
  "only 0-based offsets 4-7 (gzip MTIME) differ".
- A first pair written under different names also differed at offset 10 (the gzip FNAME field); in the real pull names are identical.
- The hist JSON (no gzip) was byte-identical across runs and equal to attempt 1's hist file for that part (`68a484c4…60bd`).
- Attempt 1's `out.sha256` line for that part (`c5fc1a5c…1827`) differs from both runs, as expected.

## 3. Integrity rule for attempt 2
- The progress manifest (`progress.tsv`, append-only) records per part: raw sha256, bytes, records, kept, **file sha256**,
  **decompressed-content sha256**, hist sha256, batch, IST time.
- On resume a part is done only if file sha, content sha and hist sha re-hash to the manifest and bytes/records match `parts.tsv`.
- The new SNAPSHOT candidate is `final/new-out.sha256` (file sha) plus `final/new-content.sha256` (content sha); integrity of the
  new SNAPSHOT is checked against the content sha, which is immune to the gzip header.

## 4. Baselines from attempt 1 (searched; nothing invented)
Searched: `backtest/snapshot/` (SNAPSHOT.md, ae-pull/*), `/workspace/oa/pull/` (pull.log, raw.sha256, parts.tsv, infra_fail.txt,
monitor files, done/, hist/, .quarantine/), and WORKLOG notes.
- **Decompressed-content sha256: none exists anywhere for attempt 1.** No baseline for the content sha; it starts with attempt 2.
- Raw input sha256: frozen `ae-pull/raw.sha256` (in git, SNAPSHOT-hashed). Coverage **1898/1898**.
- bytes / records / kept: frozen `ae-pull/pull.log`, last `ok` line per part after the 2026-10-21 17:24:59 IST RESTART line.
  Coverage **1898/1898**; totals reproduce SNAPSHOT.md (675,298,563,638 bytes; 464,765,485 records; 77,468,745 kept).
  `kept` equals the line count of the decompressed output.
- hist JSON sha256: the 1,898 surviving box files `/workspace/oa/pull/hist/*.json`, hashed 2026-10-22 ~14:49 IST into
  `baselines/attempt1-hist.sha256`. Coverage **1898/1898**. Weaker provenance: these files were never in git or any frozen
  manifest and their mtimes were reset to 06:12 IST by the restart; 0058's hist was rewritten by the double worker (SNAPSHOT.md).
- `done/` markers are empty files (no counts or hashes).

`repull.sh` end check compares every part against all three baselines and reports coverage. Any mismatch, integrity failure or
missing part exits 21 (STOP for QA). With all baselines matching, file-sha mismatches against `out.sha256` exit 20 and the new
SNAPSHOT candidate is written; a full byte match (not expected) would keep attempt 1's SNAPSHOT.

## 5. Not changed
PREREG, DEVIATION 1-3, FREEZE.sha256, SNAPSHOT files, out.sha256, filter_part.py, run_backtest.py.
