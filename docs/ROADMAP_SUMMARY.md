# Artificial Emotions — Roadmap Summary

**Full playbook:** [`ROADMAP.md`](ROADMAP.md) · **Honesty:** [`LIMITS.md`](LIMITS.md) · **Version today:** `0.4.1`

> Agents: when stuck, open the full roadmap **§0 → §3 → §2**. This page is the executive skim only.

## North star

A **curiosity layer** for AI and research orgs: generate → verify → score → diversify → brief — ranked *unanswered* questions with explicit `ValueProfile`, gap evidence, and uncertainty. Decision aids, not oracles. Not Q&A, not an end-to-end AI Scientist.

## Now (v0.4) — do not rebuild

Pipeline + OpenAlex/S2 gap gate + multi-axis scores + MCP/HTTP/CLI/web + offline seeds + domain packs + emotions surface (annotation only) + eval harness + preference JSONL + dual-use heuristic + multi-judge flags + neglectedness/cost proxies + optional HTTP API keys + structured errors / `/ready`. Limits: heuristic scoring, phrase-level gaps, dual-use residual risk, no outcome calibration. Details: roadmap §1 + [`LIMITS.md`](LIMITS.md).

## Top next wedges (pick first unfinished)

1. **P0 honesty loop** — keep LIMITS/PROOFS true; green suite (roadmap §2 W-P0a / W-P0b)  
2. Optional later: enact `drop_dual_use` / `forbid_similar_jump` in explore (not default; user must ask)  
3. v1.x calibration / preference learning (longitudinal; not an install gate)  

P1 W1–W9 and P2 W10–W15 are ✅, including PyPI (`artificial-emotions` **0.4.1**). Do **not** call v1.0 until roadmap **§10**. LIMITS still: heuristic scores, phrase-level gaps, dual-use residual, local HTTP. Full queue: roadmap **§2**.

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
| **Mid** | v0.3→v1.0 | ✅ Eval + multi-lit + dual-use + multi-judge + PyPI 0.4.1; remaining: honesty / proof gates (do not call v1.0 until ROADMAP §10) |
| **Long** | v1.x→v2+ | Flywheel, preference learning, enterprise, AI-Scientist upstream |
| **Moonshots** | — | Approximate VOI, surprise search, lab closed-loop, epistemic emotion elicitation — not default backlog |

Phased **work-order checklists**: roadmap **§7**.

## Invariants (non-negotiable)

Explicit values · related ≠ answered · answerability/risk gates · anti-McNamara multi-axis · confidence bands · graceful offline degrade · update LIMITS before marketing · stay in this folder · no commit unless asked

## Proof rule

Do not claim “calibrated,” “works on every host,” “dual-use solved,” or “v1.0” until matching **proof gates** (roadmap §10) are met. Remaining v1.0 bar is honesty / LIMITS (heuristic scores, phrase-level gaps, dual-use residual, local HTTP), not PyPI install.
