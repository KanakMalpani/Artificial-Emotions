# Deviation 2 (2026-10-21, IST; before the SNAPSHOT freeze and before any ranking run)

Doc-only record of how the hand-written run script (`backtest/run_backtest.py`, hand-written, Kanak-approved exception,
cursor-agent held for attempt 3) reads parts of PREREG.md that do not pin one reading. No results, rankings, pairs or hits have
been seen. The result stays confirmatory. The omega-3 / "Omega 3 fatty acid" target-string question (PREREG §6) is **not** part of
this deviation: it is pending Kanak. If it is not decided by the SNAPSHOT freeze, PREREG §6 stands as written and the hyphenated
`"omega-3"` does not match "Omega 3 fatty acid".

1. **§3.1 "most frequent concepts":** frequency = number of past-corpus works in domain d carrying the concept (score ≥ 0.3,
   counted once per work); ties by name.
2. **§6 "most past docs" for the Raynaud start:** number of Swanson-corpus works (≤ 1985, Medicine) tagged with that concept
   name; ties by name.
3. **§3.4 fallback percentile:** nearest-rank 90th percentile of `cited_by_count` per (primary_topic.field, publication_year),
   i.e. the smallest count with at least 90% of works at or below it; a work is highly cited by fallback if its count ≥ that value.
   Built from per-part histograms over the full pinned snapshot, 2016-2024, retracted works excluded.
4. **§5 permutation seeding:** every comparison starts a fresh `random.Random(20151231)` (each p-value is reproducible on its own).
5. **§3.2/§3.3 unordered pairs:** when both members of a pair are seeds, the first orientation in pool order (seed pack order,
   then concept frequency order) is the one kept; the seed-order tie-break in §3.3 uses the seed whose engine run gave the max gap.
6. **§6 `max_links=1000`:** applied to the Swanson run as written in §6 (consistent with §0).
7. **Fast matching (no rule change):** co-occurrence and co-mention use an index (`TermIndex`) that applies exactly the
   `LocalCorpusClient.cooccurrence_count` rule (normalized concept name, or substring of the normalized title). Equality with
   `cooccurrence_count` is checked by `tests/backtest/test_run_backtest.py::test_fast_index_equals_cooccurrence_count`.
   The engine itself (`discover_links`) still runs unchanged on `LocalCorpusClient`.

**Timing check, 2026-10-21 ~12:23 IST — timing-only, no outputs inspected.** The fast version (load, pool, unknowns, index) was run
once at nice 19 on one real derived part file (`/workspace/oa/pull/out/2025-10-10_part_*`, the largest present). Only the elapsed time and the
record count were printed: **2.4 s, 39,458 records**. Nothing else was printed or saved.

Gate run (pinned deps, real pydantic, stand-in inactive): `backtest/logs/gate-20261021-122159-IST.log` (backtest tests 20 passed;
full suite 1239 passed; ruff 0.15.22 check and format clean).
