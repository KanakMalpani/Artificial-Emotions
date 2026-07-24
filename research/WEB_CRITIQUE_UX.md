# Critique form button — web UX honesty (research)

**Status:** Companion to sibling web “Critique” on result cards (`b3c42a0`) and [`CRITIC_DEBATE_JUDGES.md`](CRITIC_DEBATE_JUDGES.md).  
**Honesty:** Form critic ≠ quality oracle; issues are heuristic regex/LLM-free flags.

*Generated: 2026-07-25*

---

## 1. Recommended copy (near button)

- Button: **Critique form** (not “Improve rank” / “Fix science”).  
- Empty state: “No form issues flagged — still may be low-value under this profile.”  
- Issue list: show `code` + `detail`; severity badge `info`/`warn` only.  
- Footer: “Does not change scores or ranks.”

---

## 2. Behaviors to avoid

| Anti-pattern | Why |
|--------------|-----|
| Auto-rerank when issues found | Violates form-critic split |
| Hiding dual-use when sprawl flagged | Safety first |
| “AI verified this question” | Overclaim |
| Running unbounded LLM debate on click | Cost/latency; HeurekaBench critic is optional second pass |

---

## 3. Productize next

1. Ensure API/MCP `critique_brief` returns same payload as web.  
2. Eval: % top-n with `sprawl_*` before/after ops edits (human).  
3. Optional: one-click “suggest tighter ops” — **draft only**, user applies.  
4. Map `invalid_form` VERITAS cousin when sprawl warn present ([`VERITAS_EPISTEMIC_LABELS.md`](VERITAS_EPISTEMIC_LABELS.md)).

---

## 4. See also

[`INVESTIGATION_DESIGN.md`](INVESTIGATION_DESIGN.md) · `critique.py`
