# Answerability vs tractability vs feasibility (research)

**Status:** Axis hygiene for scoring / ValueProfile.  
**Honesty:** Heuristic `answerability` ≠ SFBench expert feasibility; `tractability` ≠ lab synthesizability.

*Generated: 2026-07-25 | SFBench arXiv [2606.29630](https://arxiv.org/abs/2606.29630)*

---

## 1. Distinctions we should keep

| Axis | Intended meaning here | Common confusion |
|------|----------------------|------------------|
| **Answerability** | Can this question be operationalized / scoped enough to pursue *as asked*? (F9 anti-program-sprawl) | Not “will the answer be yes” |
| **Tractability** | Is progress plausible given methods language (measure/experiment/dataset)? | Not dollar cost (that’s `cost_proxy`) |
| **Cost proxy** | Investigation expense language (RCT/collider vs pilot) | Not ENBS |
| **Feasibility (lit)** | Expert judgment that a *claim/idea* can be realized (SFBench 1–5) | Separate object — don’t rename axes |

---

## 2. SFBench (SciFy Scientific Feasibility Benchmark)

- 197 **de novo** materials-science claims (reduces train contamination)  
- Expert 5-point feasibility + open-ended explanations  
- Task: assess feasibility of scientific claims — complex, not MCQ  

**Borrow:** Expert explanations as rubric language for judge prompts (“why feasible / infeasible”).  
**Don’t:** Claim our `tractability` matches SFBench scores without calibration study.

---

## 3. Mapping to `heuristic_score` today

Answerability drops for: hard keywords, non-interrogative form, short operationalization, multi-`?`, sprawling “and”, many enabling questions.  
Tractability bumps for measure/experiment/dataset; drops for “quantum gravity”/“consciousness” lexicon.  

**Productize:** Document this in LIMITS/ARCHITECTURE; optional SFBench-inspired judge rubric field `feasibility_note` separate from axes.

---

## 4. Productize next (sibling)

1. Rename clarity in UI tooltips: Answerability = “scoped enough”; Tractability = “methods foothold.”  
2. Optional LLM judge dimension `feasibility_1to5` — **not** folded into aggregate until calibrated.  
3. Confusion_risk cues already bridge low answerability → elicit enabling questions.  

---

## 5. Key citations

| Work | ID |
|------|-----|
| SFBench | arXiv 2606.29630 |
| FeasibilityQA (commonsense) | arXiv 2210.07471 |
| In-repo scoring | `scoring.py` F9/F14 |
| Investigation design | [`INVESTIGATION_DESIGN.md`](INVESTIGATION_DESIGN.md) |
