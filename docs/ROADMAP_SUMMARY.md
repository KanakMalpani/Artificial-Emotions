# Artificial Emotions — Roadmap Summary

**Full playbook:** [`ROADMAP.md`](ROADMAP.md) · **Honesty:** [`LIMITS.md`](LIMITS.md) · **Version today:** `0.4.0`

> Agents: when stuck, open the full roadmap **§0 → §3 → §2**. This page is the executive skim only.

## North star

A **curiosity layer** for AI and research orgs: generate → verify → score → diversify → brief — ranked *unanswered* questions with explicit `ValueProfile`, gap evidence, and uncertainty. Decision aids, not oracles. Not Q&A, not an end-to-end AI Scientist.

## Now (v0.4) — do not rebuild

Pipeline + OpenAlex/S2 gap gate + multi-axis scores + MCP/HTTP/CLI/web + offline seeds + domain packs + emotions surface (annotation only) + eval harness + preference JSONL + dual-use heuristic + multi-judge flags + neglectedness/cost proxies + optional HTTP API keys + structured errors / `/ready`. Limits: heuristic scoring, phrase-level gaps, dual-use residual risk, no outcome calibration, **not on PyPI yet**. Details: roadmap §1 + [`LIMITS.md`](LIMITS.md).

## Top next wedges (pick first unfinished)

1. Owner-gated **PyPI publish** (blocks calling v1.0)  
2. Live multi-provider LLM smoke with real keys (private notes; no secrets in repo)  
3. Preference *learning* / longitudinal calibration (v1.x)  
4. Optional deeper neglectedness / funding adapters (research spike)  

P2 W10–W15 and core WO-0.4 hardening are ✅. Full queue: roadmap **§2**.

## Agent ops (one-liners)

| Need | Go to |
|------|--------|
| Stuck playbooks (gap, LLM, MCP, tests, demo…) | ROADMAP **§3** |
| Invariants / no-commit / no-secrets | ROADMAP **§4** |
| Session definition of done | ROADMAP **§5** |
| F1–F15 → code actions | ROADMAP **§8** |
| Plugins / MCP install | [`PLUGINS.md`](PLUGINS.md) |
| Design invariants | [`DESIGN.md`](DESIGN.md) |

## Phases

| Horizon | Versions | Intent |
|---------|----------|--------|
| **Near** | v0.2 | ✅ Embeddings optional, multi-provider notes, presets, UX honesty, packaging prep |
| **Mid** | v0.3→v1.0 | ✅ Eval + multi-lit + dual-use + multi-judge; remaining: PyPI → **credible v1** |
| **Long** | v1.x→v2+ | Flywheel, preference learning, enterprise, AI-Scientist upstream |
| **Moonshots** | — | Approximate VOI, surprise search, lab closed-loop, epistemic emotion elicitation — not default backlog |

Phased **work-order checklists**: roadmap **§7**.

## Invariants (non-negotiable)

Explicit values · related ≠ answered · answerability/risk gates · anti-McNamara multi-axis · confidence bands · graceful offline degrade · update LIMITS before marketing · stay in this folder · no commit unless asked

## Proof rule

Do not claim “calibrated,” “works on every host,” “dual-use solved,” or “v1.0” until matching **proof gates** (roadmap §10) are met. PyPI remains the main open v1.0 gate.
