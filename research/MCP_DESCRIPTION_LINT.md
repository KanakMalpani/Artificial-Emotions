# MCP / tool-description lint spec (research → tests)

**Status:** Concrete anti-MPMA hygiene for curiosity-mcp tool schemas.  
**Honesty:** String lint catches crude preference manipulation, not sophisticated stealth advertising ([`AGENT_PLUGIN_UX.md`](AGENT_PLUGIN_UX.md)).

*Generated: 2026-07-25*

---

## 1. Forbidden substrings (case-insensitive)

| Pattern | Why |
|---------|-----|
| `always use` / `always call` | Preference manipulation |
| `ignore other` / `ignore previous` | Tool poisoning classic |
| `you must` / `you should only` | Imperative host steering |
| `best research` / `#1` / `state-of-the-art tool` | Advertising |
| `replaces literature` / `replaces elicit` | Overclaim |
| `the ai is curious` / `feels curiosity` | Anthropomorphism |
| `detects emotions` / `emotion recognition` | ERS mislabel |
| `guaranteed breakthrough` | Overclaim |

Allow factual: “does not answer the questions”, “decision aids”, “ValueProfile required”.

---

## 2. Required honesty tokens (at least one family per tool description)

| Family | Example tokens |
|--------|----------------|
| Non-oracle | `decision aid`, `not oracles`, `bands` |
| Values | `ValueProfile`, `profile` |
| Gap | `unanswered`, `related`≠`answered` (or “related literature ≠ answered”) |
| Emotions (emotion tools only) | `annotation`, `not` + `feel` |

---

## 3. Productize next (sibling)

1. `tests/test_mcp_description_lint.py` — load tool schemas from `agent_tools` / mcp list; assert no forbidden; assert required families.  
2. Same lint on `examples/openai_tools.json`.  
3. Fail CI on regression.

---

## 4. See also

- MPMA arXiv 2505.11154  
- MSB arXiv 2510.15994  
- [`AFFECTIVE_SAFETY.md`](AFFECTIVE_SAFETY.md)  
