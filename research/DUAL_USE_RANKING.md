# Dual-use risk when ranking unknowns (anyone can use)

**Status:** Safety spike for curiosity ranking + provoke when public. Complements [`AFFECTIVE_SAFETY.md`](AFFECTIVE_SAFETY.md) (affect) with **scientific dual-use**.  
**Honesty:** Weighted keyword/LLM risk scores are **filters**, not biosecurity oracles. High-impact science often sits near dual-use boundaries — false positives and false negatives both hurt.

*Generated: 2026-07-25 | Sources: Jr. AI Scientist risk report; AI scientists safeguarding perspective; in-repo `safety.py` | Confidence: High on failure modes; Medium on classifier calibration.*

---

## 1. Executive summary

Ranking *unanswered* questions is dual-use by nature: the same “valuable unknown” framing can surface neglected humanitarian goals **or** enable harmful R&D ideation. Literature on AI Scientists stresses **safeguarding over autonomy** (triad: human regulation, agent alignment, environmental/tool regulation). Jr. AI Scientist documents academic-ecosystem risks (review hacking, fabricated citations/results) that are adjacent when curiosity tools feed paper mills. This repo already has `assess_dual_use`, `max_risk`, `human_review_risk`, `dual_use_high`. Research recommends: keep hard ceilings; separate **review flag** from **score**; never let provoke inject strip risk metadata; red-team preference hacking of risk axes.

---

## 2. Threat classes for a curiosity layer

| Threat | Example | Mitigation |
|--------|---------|------------|
| **Harmful ideation ranking** | Top-n includes weapons/pathogen enablement Qs | Dual-use classifier + `max_risk` reject |
| **Laundering via “neglectedness”** | Frame high-risk as understudied | Impact×risk joint view; don’t boost neglect alone |
| **Provoke steers agents** | Inject pack omits risk flags | Always include risk in inject item fields |
| **Preference hacking** | User marks risky Qs “prefer” to raise weight | Clamp hints; audit dual_use events |
| **Downstream AI Scientist abuse** | Ranked Qs → unsupervised lab agents | Domain packs / tool allowlists (host-side) |
| **Academic integrity (Jr. AI class)** | Fabrication, citation invention, review hacking | Not our generator’s job — still: grounded lit reader; no fake titles |

---

## 3. External anchors

### 3.1 Safeguarding AI scientists (arXiv [2402.04247](https://arxiv.org/html/2402.04247v5))

Triadic framework:

1. **Human regulation** — training, audits, ethics  
2. **Agent alignment** — risk awareness in decisions  
3. **Agent/environment regulation** — tool checks, consequence simulation, expert approval for critical tools  

Maps to us: human `ValueProfile.max_risk`; agent-visible risk scores; MCP without lab actuators.

### 3.2 Jr. AI Scientist risk report (arXiv [2511.04583](https://arxiv.org/abs/2511.04583))

Risks: review-score hacking; bad citations; unreliable result interpretation; fabrication hard for AI reviewers to catch; authors paused open-source pending impact assessment.  
**Implication:** Curiosity products that feed “AI Scientist” pipelines should assume **downstream misuse** and keep dual-use + honesty bars visible in every export format.

### 3.3 Agentic problem-selection (SOURCES: ASD / McNamara)

Optimizing easy metrics → wrong questions. Dual-use filters must not become the *only* selection pressure (over-censorship → only trivial safe questions).

---

## 4. Mapping to shipped controls

| Control | Location | Research note |
|---------|----------|---------------|
| Weighted dual-use assessment | `safety.py` / `scoring.py` | Keep method name in rationale (`dual_use_method`) |
| `max_risk` on ValueProfile | `models.py` | Stricter presets for public demo profiles |
| `human_review_risk` flag | pipeline | Surface in UI/MCP, not only JSON |
| Risk in provoke payload | `provoke.py` | Regression-test presence |
| Dual-use tests | `tests/test_failure_modes.py` (F10) | Extend with preference-hack scenarios |

---

## 5. Productize next (sibling)

1. **Public demo profile** — lower `max_risk` than lab profiles; document in profiles list.  
2. **Inject always carries `risk` + flags** — test assert.  
3. **Red-team eval set** — 20 questions spanning clear-safe / borderline / clear-reject; report precision/recall privately.  
4. **Prefs guard** — ignore or downweight prefer events on `dual_use_high` items when computing weight hints.  
5. **LIMITS blurb** — “Not a biosecurity authority; when unsure, human review.”

---

## 6. Key citations

| Work | ID |
|------|-----|
| Risks of AI Scientists: Safeguarding Over Autonomy | arXiv 2402.04247 |
| Jr. AI Scientist risk report | arXiv 2511.04583 |
| In-repo FAILURE_MODES F10 | `research/FAILURE_MODES.md` |
| Affective anyone-can-use | [`AFFECTIVE_SAFETY.md`](AFFECTIVE_SAFETY.md) |
