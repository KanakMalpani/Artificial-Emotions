# Deviation 3 (2026-10-22, IST; written 2026-10-22 03:14 IST, before the fixture change, before any ranking or LLM baseline run)

Test-fixture correction only. No matching code, no PREREG section and no DEVIATION-2 item changes. No results, rankings, pairs,
hits or LLM outputs have been seen. The result stays confirmatory.

**Problem.** `tests/backtest/test_run_backtest.py::test_section_3_4_matching_keeps_hyphens` asserts that
`TermIndex.co("omega 3", "A")` matches a doc built as `_doc(1, 2018, ["Omega 3 fatty acid", "A"], seg="future")` with an
empty title. That expectation contradicts the frozen rule, so the test was wrong, not the code.

**Why the test was wrong.** PREREG §3.4 says A and C each match a doc "by the same rule as `cooccurrence_count` (normalized
concept name, or a substring of the normalized title)". DEVIATION-2 item 7 pins `TermIndex` to exactly that rule (checked by
`test_fast_index_equals_cooccurrence_count`); DEVIATION-2 item 8 drops hyphens only for §6 Swanson target matching and says
§3.4 matching does not change. "omega 3" is not equal to the normalized concept name "omega 3 fatty acid" (substring of a
concept name is not a match) and the title is empty, so under the frozen rule it must not match. The code returns no match,
which is correct.

**Evidence.**
- Original fixture: `_doc(1, 2018, ["Omega 3 fatty acid", "A"], seg="future")`, empty title (as committed in `ba46363`'s
  parent state and recorded in `/workspace/ae-runscript-agent.log`, line 24, where the agent noted the fixture "had an empty
  title, so `"omega 3"` was not an exact concept name").
- Frozen rule: PREREG §3.4 (quoted above; PREREG sha256 fbefc77d…931f in FREEZE.sha256), DEVIATION-2 items 7-8.
- Failing gate with the original fixture restored: `backtest/logs/gate-20261022-084157-IST.log`
  (`AssertionError: assert (not set() and set())`, `co('omega 3', 'A') == set()`; 1 failed, 1266 passed).

**Fix (next commit, fixture only).** Give that doc a title in which "omega 3" really is a normalized title substring:
`title="omega 3 study"`. Kept unchanged: every "omega-3" no-match check (`cooccurrence_count("omega-3", "A") == 0`,
`not idx.co("omega-3", "A")`, `Checker ... co_mentions == 0`), and the positive case where "omega 3" matches through the real
title substring. No matching code, no §3.4 text and no other test expectation changes.

**Timing.** This file is committed on its own before the fixture change; the fixture commit follows it.

Re-freeze: `backtest/FREEZE.sha256` gains this file's hash (same pattern as Deviations 1 and 2).
