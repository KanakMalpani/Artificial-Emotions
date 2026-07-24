# Investigation design & falsifiers for provoke (research)

**Status:** Deepens [`EPISTEMIC_ELICITATION.md`](EPISTEMIC_ELICITATION.md) rubrics with experimental-design / information-gain literature.  
**Honesty:** Asking an LLM for a “falsifier” is cheap process quality — not a guarantee of severe tests (Mayo) or optimal EIG experiments.

*Generated: 2026-07-25 | Sources: BoxingGym, LeGIT, agentic science surveys | Confidence: High on LLM weakness at experimental design; Medium on rubric transfer.*

---

## 1. Executive summary

Provoke already asks for a first experiment and a falsifier. BoxingGym shows current LLMs **struggle** at experimental design and model discovery even when EIG is measurable in toy scientific environments. LeGIT shows LLMs can **augment** (not replace) numerical intervention targeting for causal discovery. Product stance: keep falsifier/experiment demands in injects; score them with rubrics; optionally later attach EIG-style worksheets only when a generative model exists ([`VOI_APPROXIMATIONS.md`](VOI_APPROXIMATIONS.md)).

---

## 2. Anchors

| Work | Claim | Use |
|------|-------|-----|
| **BoxingGym** ([2501.01540](https://arxiv.org/abs/2501.01540)) | 10 env benchmark; EIG for experiment value; LLMs (e.g. GPT-4o) struggle at design + discovery | Humility for “propose one experiment”; eval need |
| **LeGIT** ([2503.01139](https://arxiv.org/abs/2503.01139)) | LLM-guided intervention targeting helps causal discovery vs pure numerical early signals | Optional future: “suggest intervention variable” for causal-flavored domains |
| **Agentic Science surveys** ([2508.14111](https://arxiv.org/abs/2508.14111), [2510.09901](https://arxiv.org/abs/2510.09901)) | Hypothesis → design → execute → analyze loops | Curiosity sits at hypothesis/question stage |
| **Falsifiability ↔ learnability** (Balduzzi [1408.6618](https://arxiv.org/abs/1408.6618)) | Philosophical/learning link | Motivates demanding falsifiers in rubrics |
| Epistemic elicitation path | Surprise→curiosity→explore | Process, not design optimality |

---

## 3. Rubric upgrade (for `elicit_ab_protocol.json`)

Add optional items (0–2):

| ID | Prompt |
|----|--------|
| `experiment_operational` | States independent variable / observation with enough detail to attempt |
| `falsifier_asymmetric` | Names outcome that would **reduce** confidence in the leading hypothesis (not just “more data”) |
| `cost_aware` | Mentions cheap pilot vs expensive definitive study when `confusion_risk` |
| `eig_ish` (advanced) | Argues why this observation discriminates between ≥2 rival accounts |

Do not require `eig_ish` in default agent evals.

---

## 4. Productize next (sibling)

1. Extend elicit protocol JSON with the optional rubric rows above.  
2. In provoke inject, one line: “Prefer a discriminating observation over a vague ‘run more experiments.’”  
3. Eval report: % of agent outputs with non-empty falsifier string (string match / judge).  
4. BoxingGym is **not** a dependency — cite as external benchmark if claiming experimental-design skill.  
5. Lab closed-loop moonshot: only then compute real EIG.

---

## 5. Key citations

| Work | ID |
|------|-----|
| BoxingGym | arXiv 2501.01540 |
| LeGIT | arXiv 2503.01139 |
| Agentic Science survey | arXiv 2508.14111 |
| Autonomous agents for discovery (vision) | arXiv 2510.09901 |
| Balduzzi, Falsifiable ⇒ Learnable | arXiv 1408.6618 |
