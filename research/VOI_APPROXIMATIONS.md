# Approximate VOI — research spike (moonshot)

**Status:** Literature spike for ROADMAP §7.6 *Approximate VOI at scale*.  
**Honesty:** Full Bayesian VOI/EVSI requires a **decision model + utilities + cost of sampling**. This product has **proxy axes**, not dollar EVSI. Do not rename scores to “EVSI.”

*Generated: 2026-07-25 | Sources: ISPOR / ConVOI / arXiv EVSI methods | Confidence: High on health-econ methods; Low on direct port to open-ended science questions.*

---

## 1. Executive summary

ISPOR VOI Task Force and ConVOI make clear: **EVPI / EVPPI / EVSI / ENBS** prioritize research when you already have a health-economic decision model and PSA draws. Modern approximations (moment matching, Gaussian approximation, nonparametric regression, TGA for nonlinear models) make EVSI tractable in minutes–hours instead of weeks — **inside that paradigm**. Artificial Emotions ranks open scientific unknowns **without** a shared net-benefit function. The honest bridge is: (a) keep multi-axis proxies + ValueProfile; (b) optionally offer a **structured VOI template** for domains that *do* have decision models (clinical/policy packs); (c) never claim general EVSI for arbitrary AI/climate questions.

---

## 2. Standard VOI objects (glossary)

| Acronym | Meaning | Needs |
|---------|---------|-------|
| **EVPI** | Expected value of perfect information | Max value of resolving all uncertainty |
| **EVPPI** | Expected value of partial perfect information | Value of learning a parameter subset perfectly |
| **EVSI** | Expected value of sample information | Value of a *finite* study design |
| **ENBS** | Expected net benefit of sampling | EVSI − study cost (implementation-adjusted variants exist) |

Canonical intros: ISPOR VOI Task Force reports (introduction + analytical methods). White Rose / eprints link already in [`SOURCES.md`](SOURCES.md).

---

## 3. Why “approx VOI at scale” is hard *here*

| Health-econ VOI | Open scientific curiosity |
|-----------------|---------------------------|
| Finite action set (treat A vs B) | Open-ended question space |
| Shared utility (QALY, net monetary benefit) | Contested values → `ValueProfile` |
| PSA over model parameters | No universal generative decision model |
| Study design = sample size / endpoints | “Study” = experiment / lit review / field trial — heterogeneous |
| EVSI in currency or health units | Our scores are unitless proxies |

**Conclusion:** Porting Heath/Jalal/Strong EVSI estimators wholesale is a **domain adapter**, not a core scorer replacement.

**Addendum:** Contested beliefs → credal / rule-specific VOI; lab packs as clusters — [`VOI_IMPRECISE.md`](VOI_IMPRECISE.md). Sibling `fill_voi_worksheet` prefills metadata only (not EVSI).

---

## 4. Approximation methods worth knowing (for future adapters)

| Method family | Idea | Cite |
|---------------|------|------|
| Nested Monte Carlo | Gold standard; weeks on complex models | Classic |
| Moment matching | Match preposterior mean of incremental net benefit using PSA | Heath et al. arXiv [1611.01373](https://arxiv.org/abs/1611.01373), [1804.09590](https://arxiv.org/abs/1804.09590) |
| ConVOI comparison | Four practical approx methods; skills/inputs guide | Kunst et al. [1910.03368](https://arxiv.org/abs/1910.03368); MDM journal guidance |
| Gaussian approximation (GA) | Metamodel + GA Bayesian update; good across sample sizes | Jalal line; PMC8608426 |
| TGA (Taylor + GA) | Fixes GA bias on **nonlinear** net benefit | Li, Jalal, Heath [2401.17393](https://arxiv.org/abs/2401.17393) |
| Implementation-adjusted EVSI | Study value ≠ instant perfect uptake | Heath [2105.05901](https://arxiv.org/abs/2105.05901) |
| EVSI for **model validation** | Value of external validation sample for risk models | Sadatsafavi et al. [2401.01849](https://arxiv.org/abs/2401.01849) |

Practical takeaway from ConVOI: all serious methods start from **PSA output**; analyst needs regression and/or likelihood/Bayesian skills; pick method by model cost and whether many sample sizes are compared.

---

## 5. Honest mapping to current axes

| Proxy axis today | Rough VOI analogy | Failure if overclaimed |
|------------------|-------------------|------------------------|
| Impact / stakes | Scale of decision loss if wrong | Not calibrated NMB |
| Surprise | Distance from prior / related lit | Not EVPI |
| Neglectedness | Under-studied relative to stakes | Not 1/EVSI |
| Answerability / tractability | Cheap study → higher ENBS-ish | Not study-cost model |
| Cost proxy | Lexicon for expensive programs | Not ENBS |
| Risk / dual-use | Constraint / veto — outside classic VOI | Keep separate |

[`NEGLECTEDNESS_COST.md`](NEGLECTEDNESS_COST.md) remains the right home for lexicon/density proxies.

---

## 6. Product paths (ranked by honesty)

### Path A — Stay proxy (default)

Document axes as **decision aids** under ValueProfile; cite ISPOR as inspiration, not implementation. **Ship nothing VOI-branded.**

### Path B — Optional “VOI worksheet” export (near-term research→product)

For ranked questions in clinical/policy domains, emit a **blank structured sheet**:

```text
decision_problem, options[], uncertain_parameters[],
utility_units, current_recommendation,
proposed_study {design, n, endpoints, cost},
notes: "Fill PSA externally; compute EVSI with ConVOI tooling"
```

No fake numbers. Sibling could add `examples/voi_worksheet_template.json`.

### Path C — Domain adapter (moonshot)

Pack + optional plugin: user supplies PSA CSV + study design → call R/`voi` / custom GA → attach `evsi_estimate` metadata on one question. **Out of core Python path** until a real user brings a model.

### Path D — Forbidden

Publishing `scores.voi` as if EVSI; marketing “optimal trial design” without ENBS inputs.

---

## 7. Productize next (sibling)

1. **LIMITS one-liner** (if not present): scores are not EVSI/ENBS.  
2. **`examples/voi_worksheet_template.json`** — empty schema for Path B.  
3. **Profile note** — `funder_10y` / clinical presets: link to worksheet, not auto-EVSI.  
4. **Do not** add EVSI dependencies to core package.  
5. Prefer improving **answerability × cost proxy transparency** over fake currency.

---

## 8. Key citations

| Work | ID |
|------|-----|
| ISPOR VOI Task Force (intro) | ispor.org HEOR good practices |
| ISPOR VOI analytical methods | Report 2 |
| Heath et al. moment matching | arXiv 1611.01373 |
| Heath et al. sample-size sweep | arXiv 1804.09590 |
| Kunst et al. ConVOI methods guide | arXiv 1910.03368 |
| Heath et al. case studies | arXiv 1905.12013 |
| Li, Jalal, Heath TGA | arXiv 2401.17393 |
| Sadatsafavi et al. EVSI for validation | arXiv 2401.01849 |
| Jalal GA approach | PMC8608426 |
