# Neglectedness & cost proxies — research spike (WO-0.4.4)

**Status:** Spike → thin code landed in heuristic scorer (`scoring.py`).  
**Honesty:** These are **lexicon / literature-density proxies**, not funding databases, citation graphs, or true EVSI.

## What “neglectedness” should mean here

Relative underinvestment / understudy given stakes — **not** “sounds novel” and **not** inverse of impact (anti-McNamara / F3 / F6).

## Candidate signals (research → product)

| Signal | Ideal source | What we ship now | Risk |
|--------|--------------|------------------|------|
| Literature density in neighborhood | OpenAlex/S2 hit count + overlap | Density + strong-match pressure | Noisy topics inflate hits |
| Citation pressure | Mean cites in neighborhood | Soft damper on neglectedness | Popular adjacent work ≠ answered |
| Hot-topic / trend lexicon | Manual list | Down-weight transformers/LLM hype cues | Language games |
| Funding-heavy cues | Grants DBs (future) | Phrase cues only (`well-funded`, …) | Easy to game; keep small |
| Interdisciplinary seam | Multi-tag questions | Small boost when ≥3 tags | Tag spam |
| Investigation cost | Lab / clinical scale language | Cost proxy from pilot vs collider/RCT language (F14) | Not dollar estimates |

## Explicit non-claims

- Not OpenAlex concept citation rates as ground truth.
- Not NIH/NSF spend APIs (future optional adapter).
- Not calibrated VOI / dollar cost.

## Product rule

Keep axes visible in briefs/UI; never hide that neglectedness/cost are heuristics. Prefer LLM judges when configured; retain rationale keys `neglectedness_proxy` / `cost_proxy_method`.
