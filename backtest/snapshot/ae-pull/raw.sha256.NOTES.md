# raw.sha256 notes

- raw.sha256 has 1,899 lines covering 1,898 unique parts.
- Lines 173 and 1899 are an intended duplicate: both are `b503d057fb1caeaa312f1ee8c285ac49aef4c2e473cdd44ced771bba9db1dbc2  works/2025-11-06_part_0058.gz`. Line 1899 was appended by the 0058 re-pull (v7 work()) at 2026-10-22 04:07:54 IST; line 173 is the original and is untouched.
- Per QA bot's ruling, both lines are kept (deleting either would be a data edit). No comment was added inside raw.sha256 so `sha256sum -c` parsing is unaffected.
- Uniqueness checks must count unique paths (field 2), not lines, e.g. `awk '{print $2}' raw.sha256 | sort -u | wc -l` -> 1898.
- If a frozen copy of raw.sha256 is de-duplicated, that must not count as a deletion from this source record.
