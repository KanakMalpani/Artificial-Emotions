# Funding & bibliometric neglectedness signals (adapter research)

**Status:** Addendum to [`NEGLECTEDNESS_COST.md`](NEGLECTEDNESS_COST.md) + [`NEGLECTEDNESS_ITN.md`](NEGLECTEDNESS_ITN.md).  
**Honesty:** OpenAlex is a **superset** of Scopus for many analyses but metadata (affiliations, funders, references) is incomplete/uneven — especially outside Scopus/WoS-overlap papers (Alperin et al. 2024; Alonso-Alvarez & van Eck). Do not treat concept hit counts as EA neglectedness.

*Generated: 2026-07-25 | Sources: Academia OpenAlex coverage papers; grant-design econ | Confidence: Medium on adapter feasibility.*

---

## 1. Executive summary

Next neglectedness upgrades should prefer **optional adapters** that expose: (a) neighborhood paper counts (already), (b) optional OpenAlex **concept** / topic density, (c) optional **funder** field presence rates — all as **rationale keys**, not silent score rewrites. Coverage bias (Africa metadata, retraction field incidents historically) means always show provenance and caveats.

---

## 2. What OpenAlex can (and cannot) give us

| Signal | Feasibility via OpenAlex | Caveat |
|--------|--------------------------|--------|
| Works count in query neighborhood | High (already) | Synonym inflation |
| Citation counts on neighborhood | Medium | Field-normalized cites needed for fairness |
| Concept / topic IDs on works | Medium | Concept quality varies |
| Funder names on works | Low–Med | Metadata completeness lower than pubs/authors |
| Country / institution coverage | Medium | Better than proprietary for Global South coverage *counts*; accuracy uneven |
| Retraction status | Use carefully | Past `is_retracted` consolidation bugs (Hauschke 2024) — pin API fields |

Alperin et al. ([2404.17663](https://arxiv.org/abs/2404.17663)): OpenAlex ⊇ Scopus for many uses; still need accuracy research.  
Alonso-Alvarez & van Eck ([2409.01120](https://arxiv.org/abs/2409.01120)): African research — high coverage, weaker affiliation/ref/funder metadata.

---

## 3. Funding dynamics ≠ topic neglectedness

Bi-national grant studies (e.g. GIF [2510.02743](https://arxiv.org/abs/2510.02743)): funding **spikes collaboration during awards** but often doesn’t create lasting networks — so “well-funded recently” ≠ “crowded forever.”  
Grant design literature ([2410.12356](https://arxiv.org/abs/2410.12356)): allocation vs management stages; lotteries/staged grants — relevant if we ever estimate ENBS ([`VOI_APPROXIMATIONS.md`](VOI_APPROXIMATIONS.md)).

**Product rule:** Phrase cues like `well-funded` remain weak; prefer countable funder metadata when available, labeled `funding_metadata_sparse=true` when missing.

---

## 4. Productize next (sibling)

1. **Rationale keys only:** `openalex_hit_n`, `mean_cited_by` (if cheap), `funder_field_missing_rate` — ✅ largely shipped in `scoring.py` / `openalex.py`.  
2. **No new default weight** until fixture correlation with human neglectedness labels.  
3. **LIMITS:** OpenAlex metadata incompleteness one-liner — see [`LIMITS_PATCHES.md`](LIMITS_PATCHES.md).  
4. Optional research script: LitGap co-occurrence vs neglectedness — ✅ helpers (`04eeebf`); run study offline.  
5. Keep NIH/NSF APIs as separate future adapters — not blocking.  
6. Next wedge: correlation notebook results → decide whether any funder key becomes a *display badge* only.

---

## 5. Key citations

| Work | ID |
|------|-----|
| Alperin et al., OpenAlex suitability | arXiv 2404.17663 |
| Alonso-Alvarez & van Eck, African coverage | arXiv 2409.01120 |
| Hauschke & Nazarovets, retraction field | arXiv 2403.13339 |
| GIF bi-national funding dynamics | arXiv 2510.02743 |
| Designing scientific grants | arXiv 2410.12356 |
