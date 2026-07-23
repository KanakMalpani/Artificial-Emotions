# Artificial Curiosity — Roadmap Summary

**Full playbook:** [`ROADMAP.md`](ROADMAP.md) · **Honesty:** [`LIMITS.md`](LIMITS.md) · **Version today:** `0.1.0`

> Agents: when stuck, open the full roadmap **§0 → §3 → §2**. This page is the executive skim only.

## North star

A **curiosity layer** for AI and research orgs: generate → verify → score → diversify → brief — ranked *unanswered* questions with explicit `ValueProfile`, gap evidence, and uncertainty. Decision aids, not oracles. Not Q&A, not an end-to-end AI Scientist.

## Now (v0.1) — do not rebuild

Pipeline + OpenAlex gap gate + multi-axis scores + MCP/HTTP/CLI/web + offline seeds. Limits: heuristic scoring, phrase-level gaps, keyword dual-use, no outcome calibration, no PyPI yet. Details: roadmap §1 + [`LIMITS.md`](LIMITS.md).

## Top next wedges (pick first unfinished)

1. Optional embedding diversity (Jaccard stays default)  
2. ValueProfile presets on API/CLI/MCP  
3. Separate `judge_model` from generator  
4. Multi-provider LLM smoke notes (no secrets)  
5. Expand F7/F13 adversarial tests  

Full queue with files / success tests / done-when: roadmap **§2**.

## Agent ops (one-liners)

| Need | Go to |
|------|--------|
| Stuck playbooks (gap, LLM, MCP, tests, demo…) | ROADMAP **§3** |
| Invariants / no-commit / no-secrets | ROADMAP **§4** |
| Session definition of done | ROADMAP **§5** |
| F1–F15 → code actions | ROADMAP **§8** |
| Plugins / MCP install | [`PLUGINS.md`](PLUGINS.md) |
| Why (optional) | [`research/`](../research/) |

## Phases

| Horizon | Versions | Intent |
|---------|----------|--------|
| **Near** | v0.2 | Embeddings optional, multi-provider proofs, presets, UX honesty, PyPI |
| **Mid** | v0.3→v1.0 | Eval harness, multi-literature, stronger dual-use, multi-judge → **credible v1** |
| **Long** | v1.x→v2+ | Flywheel, preference learning, domain packs, enterprise, AI-Scientist upstream |
| **Moonshots** | — | Approximate VOI, surprise search, lab closed-loop — not default backlog |

Phased **work-order checklists**: roadmap **§7**.

## Invariants (non-negotiable)

Explicit values · related ≠ answered · answerability/risk gates · anti-McNamara multi-axis · confidence bands · graceful offline degrade · update LIMITS before marketing · stay in this folder · no commit unless asked

## Proof rule

Do not claim “calibrated,” “works on every host,” “dual-use solved,” or “v1.0” until matching **proof gates** (roadmap §10) are met.
