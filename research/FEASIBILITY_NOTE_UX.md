# feasibility_note — display-only UX (research)

**Status:** Companion to sibling `feasibility_note` on briefs (`90fc51d`) and [`SFBENCH_CALIBRATION.md`](SFBENCH_CALIBRATION.md).  
**Honesty:** Not SFBench score; not folded into curiosity aggregate.

*Generated: 2026-07-25*

---

## 1. Recommended presentation

| Element | Guidance |
|---------|----------|
| Label | **Feasibility note** (not “Feasibility score”) |
| Placement | Below tractability/answerability tooltips |
| Empty | Hide row if blank |
| Tone | Hedge language: “may be hard because…”, “methods foothold:…” |
| Link | Tooltip: “Display only — not calibrated to SFBench” |

---

## 2. Anti-patterns

- Sorting or filtering top-n by feasibility_note  
- Showing a fake 1–5 star without calibration study  
- Overwriting answerability/tractability axes  

---

## 3. Productize next

1. Keep generator prompts from inventing numeric feasibility.  
2. Run offline calibration before any numeric field.  
3. Optional: critique_brief can append “feasibility theater” if ops claim synthesizability without measurement plan.

---

## 4. See also

[`ANSWERABILITY_FEASIBILITY.md`](ANSWERABILITY_FEASIBILITY.md) · [`DOMAIN_PACK_QUALITY.md`](DOMAIN_PACK_QUALITY.md)
