# Neglectedness signals — ITN / EA lens (addendum)

**Status:** Addendum to [`NEGLECTEDNESS_COST.md`](NEGLECTEDNESS_COST.md).  
**Honesty:** 80,000 Hours / GiveWell-style **ITN** (Importance, Tractability, Neglectedness) is a **prioritization heuristic for cause areas**, not a calibrated metric for arbitrary paper-level questions. Useful as vocabulary + product UX; dangerous if treated as ground truth.

*Generated: 2026-07-25 | Sources: Exa (80k Hours / Open Phil framing) + prior spike | Confidence: High on ITN definitions; Low on quantitative transfer to lit-density proxies.*

---

## 1. ITN in one table

| Axis | EA-ish meaning | Artificial Emotions cousin |
|------|----------------|------------------------------|
| **Importance** | Scale of problem / stakes if solved | `impact` / stakes language in profiles |
| **Tractability** | Marginal progress per resource | `tractability` / `answerability` + cost proxy |
| **Neglectedness** | How little attention/resources relative to importance | `neglectedness` axis (lexicon + lit density) |

Classic caution from the EA community: neglectedness is **not** “nobody works on it” alone — it’s underinvestment **relative to importance**. A tiny unimportant topic can be “neglected” and still low priority. Our scorer must keep **impact × neglectedness** visible (anti-McNamara / F3 / F6).

---

## 2. Signals ranked by honesty for *this* codebase

| Signal | Honesty | Notes |
|--------|---------|-------|
| Neighborhood lit hit count / density | Medium | Already in spike; noisy for hot synonyms |
| Citation pressure damper | Medium | Popular adjacent ≠ answered |
| Hot-topic lexicon downweight | Low–Med | Easy to game; keep small |
| Interdisciplinary seam (≥3 tags) | Low–Med | Proxy for “between stools” neglect |
| Funding DB spend (NIH/NSF/OpenAlex concepts) | High if wired | Not shipped; future adapter |
| Expert “who else works on this?” | High | Human/agent label via prefs |
| Pure “few Google hits” | Low | Marketing SEO ≠ research neglect |

LitGapFinder-style `sim × 1/(1+cooccur)` is a **structural** neglectedness cousin (underexplored *links*), distinct from funding neglectedness — document both if used.

---

## 3. Productize next (sibling)

1. Brief template: show **impact and neglectedness side-by-side** with one-line “ITN-inspired; not EA scores.”  
2. Pref event label `reason=neglectedness` for flywheel ([`PREFERENCE_CALIBRATION.md`](PREFERENCE_CALIBRATION.md)).  
3. Optional research metric: log co-occurrence gap score beside neglectedness — correlation study only.  
4. Do **not** brand outputs as “80,000 Hours scores.”

---

## 4. Pointers

- [`NEGLECTEDNESS_COST.md`](NEGLECTEDNESS_COST.md) — shipped proxy table  
- [`VOI_APPROXIMATIONS.md`](VOI_APPROXIMATIONS.md) — when real decision models exist, ENBS > ITN slogans  
- [`GAP_VERIFICATION_COMPETITORS.md`](GAP_VERIFICATION_COMPETITORS.md) — LitGapFinder structural gaps  
