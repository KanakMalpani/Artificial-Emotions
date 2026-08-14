# Artificial Emotions — Roadmap Summary

**Full playbook:** [`ROADMAP.md`](ROADMAP.md) · **Honesty:** [`LIMITS.md`](LIMITS.md) · **Version today:** `1.0.0` (last PyPI upload `0.4.1`; tag `v1.0.0` pending)

> Agents: when stuck, open the full roadmap **§0 → §3 → §2**. This page is the executive skim only.

## North star

A **curiosity layer** for AI and research orgs: generate → verify → score → diversify → brief — ranked *unanswered* questions with explicit `ValueProfile`, gap evidence, and uncertainty. Decision aids, not oracles. Not Q&A, not an end-to-end AI Scientist.

## Now (v1.0.0) — do not rebuild

Pipeline + OpenAlex/S2 gap gate + multi-axis scores + MCP/HTTP/CLI + offline seeds + domain packs + emotions surface (annotation only) + eval harness + preference JSONL + dual-use heuristic + multi-judge flags + neglectedness/cost proxies + optional HTTP API keys + structured errors / `/ready`. Frozen `/v1` is additive-only. Limits: heuristic scoring, phrase-level gaps, dual-use residual risk, no outcome calibration, local HTTP (not production). Details: roadmap §1 + [`LIMITS.md`](LIMITS.md).

This cut is **1.0.0** because roadmap **§7.4** is the trust bar and LIMITS is the contract — not because those slogans became true.

## Top next wedges (pick first unfinished)

1. **P0 honesty loop** — keep LIMITS/PROOFS true; green suite (roadmap §2 W-P0a / W-P0b)  
2. **v1.1 calibration proof** — W-cal scaffolding shipped; scores still **not calibrated**. No accuracy %. Proof remains §10.  
3. **v1.1 production HTTP** — local-v1 shipped; **not** TLS, WAF, multi-tenant, or SLOs.  

Shipped leftovers (do not re-implement): ✅ **W-explore**, ✅ **W-rules**, ✅ **W-cal** scaffolding.

P1 W1–W9 and P2 W10–W15 are ✅, including last PyPI upload (`artificial-emotions` **0.4.1**). Product on `main` is **1.0.0** pending tag. LIMITS still: heuristic scores, phrase-level gaps, dual-use residual, local HTTP. Full queue: roadmap **§2**.

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
| **Mid** | v0.3→v1.0 | ✅ Eval + multi-lit + dual-use + multi-judge + §7.4 trust bar — this cut is **1.0.0** (last PyPI upload 0.4.1) |
| **Long** | v1.x→v2+ | **v1.1:** calibration proof + production HTTP; flywheel scaffolding shipped; enterprise local-v1 shipped (multi-tenant/SLOs remain §10) |
| **Moonshots** | — | Approximate VOI honesty stub (`evsi: null` / `not_evsi`); lab closed-loop dry-run stub (`emotions loop --outcomes`; not experiment execution); surprise search and elicitation remain research — not default backlog |

Phased **work-order checklists**: roadmap **§7**.

## Invariants (non-negotiable)

Explicit values · related ≠ answered · answerability/risk gates · anti-McNamara multi-axis · confidence bands · graceful offline degrade · update LIMITS before marketing · stay in this folder · no commit unless asked

## Proof rule

Do not claim “calibrated,” “works on every host,” “dual-use solved,” “VOI/EVSI,” “lab closed-loop,” or “production-ready HTTP” until matching **proof gates** (roadmap §10) are met. **1.0.0** is allowed because §7.4 is the trust bar and LIMITS is the contract — not because those slogans became true. Remaining work is P0 + v1.1 (calibration proof, production HTTP), not a second v1.0 gate. §7.6 stubs shipped; moonshots remain moonshots.
