# Agent card / public honesty copy (research draft)

**Status:** Proposed copy for `/v1/agent`, MCP server blurb, and README — sibling owns final wording in product docs.  
**Sources:** [`AFFECTIVE_SAFETY.md`](AFFECTIVE_SAFETY.md), [`VOI_APPROXIMATIONS.md`](VOI_APPROXIMATIONS.md), [`PROBLEM_SELECTION_MCNAMARA.md`](PROBLEM_SELECTION_MCNAMARA.md), [`CO_SCIENTIST_LANDSCAPE.md`](CO_SCIENTIST_LANDSCAPE.md).

*Generated: 2026-07-25*

---

## 1. Short card (≤80 words)

Artificial Curiosity ranks **valuable unanswered questions** under an explicit **ValueProfile**. It verifies literature neighborhoods without equating related work with answered questions, then returns briefs and optional **provoke** inject packs for investigation. Scores and epistemic cues are **decision aids / UX annotations**, not oracles, EVSI, emotion recognition, or proof the system “feels” curious. Use as a **co-scientist upstream layer** — not a replacement for human judgment or closed-loop labs.

---

## 2. Bullet honesty block (API `honesty` field)

```text
- Requires / surfaces ValueProfile (no value-free ranking)
- Gap verify: related ≠ answered
- Scores: proxies, not EVSI/ENBS or scientific priority truth
- Epistemic cues / emotion mix: annotation_only — not biometric ERS (EU AI Act)
- Dual-use risk filters: heuristics, not biosecurity authority
- Provoke: investigation framing for agents/humans — not persuasion toolkit
```

---

## 3. What to avoid in tool descriptions

- “Always call this first” / “best research tool” / “replaces literature review”
- “The AI is curious” / “detects your emotions”
- “Optimal trial design” without ENBS inputs

See [`AGENT_PLUGIN_UX.md`](AGENT_PLUGIN_UX.md) MPMA lint.

---

## 4. Productize next (sibling)

1. Paste short card into `/v1/agent` + MCP instructions.  
2. Link `curiosity://limits` early in agent guide ordering.  
3. Keep LIMITS.md as source of truth; this note is draft only.
