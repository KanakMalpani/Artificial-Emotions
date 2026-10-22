# AE re-pull WORKLOG

## 2026-10-22 14:46 IST: batch re-pull script drafted (for QA, NOT started)
- DEVIATION (process): cursor-agent `grok-4.7-high` (non-fast) ran 15 min against the full spec and timed out (exit 124) with no files written
  (log: /workspace/repull-agent/agent.log). Per Engineering Lead's standing rule, repull.sh, push_checkpoint.sh and dry_test.sh were hand-written.
- Dry test: 8 tests + T0 probe, fails=0. Output kept in /home/box/oa-repull/dry-20261022-144431/ (dry_test.stdout, logs, quarantine). Deleted nothing.
- FINDING for QA: filter_part.py writes gzip with the current time in the header (gzip.open default mtime), so its .jsonl.gz output
  is NOT byte-reproducible: same input gives the same decompressed bytes but different file sha256 (T0). Attempt-1 originals are gone,
  so the end check against out.sha256 is expected to MISMATCH on effectively every part, which by the approved rule means
  new SNAPSHOT + DEVIATION-4. Not changed here (filter_part.py stays byte-identical). Decision needed from QA/EL/Kanak before the pull.
- venv: /home/box/oa-repull/venv, orjson 3.13.0 (attempt 1's /workspace/oa/venv was lost; its orjson version is unknown).

## 2026-10-22 14:48 IST: dry_test T7 fix
- Run /home/box/oa-repull/dry-20261022-144656 had fails=1 (T7): the test set hash char 1 to 'f' and that hash already began with 'f', so nothing changed. Test bug, not a repull.sh bug.
  Fixed to always flip char 1 (0<->other). Then 5/5 runs fails=0 (dry-20261022-144758 .. -144817). Failing run dir kept.
