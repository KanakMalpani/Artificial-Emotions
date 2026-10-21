# Backtest pre-registration: Swanson-ABC curiosity engine vs baselines (2015 cutoff)

Status: PRE-REGISTRATION. This file has no results, sample outputs, expected numbers or ranked lists.
Author: SWE (on behalf of Kanak Malpani). Branch: `backtest/prereg`. Written 2026-10-21 (IST).
No data was pulled, no OpenAlex or LLM API was called, and nothing was run to write this file.

## 0. What is being tested (as the code ranks today)

The engine under test is `discover_links()` in `src/artificial_emotions/discover.py`, run offline through
`LocalCorpusClient` (same file) on a corpus built from a frozen OpenAlex snapshot. It is used unmodified, at the
commit this file is committed on top of (recorded in the manifest, §1.5).

How it ranks (read from the code; line numbers are at the parent commit):
- A seed concept **A** gets concept counts from works matching A (`LocalCorpusClient.concept_counts`: +1.0 per matching
  doc, first `per_page=50` matching docs in corpus order, `discover.py` ~L509).
- The top `max_bridges=4` concepts, minus `_STOP_CONCEPTS` and A, become bridges **B** (`discover.py` L226-231).
- For each B, the top 6 concepts **C** not strongly co-tagged with A (A-side cutoff `a_side_strength=0.05` of the
  strongest A concept) are candidates (L241-262).
- Candidates with A–C co-occurrence above `cooccurrence_ceiling=400` are dropped (L265-266).
- `sim = min(1, sqrt(b_score*c_score)/10)` and `gap = gap_score(sim, cooc) = sim/(1+cooc)`
  (`discover.py` L271, `cooccur_study.py` L14). Links are sorted by `-gap`, then `a`, then `c`, and truncated to `max_links` (L287-288).
- Co-occurrence in `LocalCorpusClient.cooccurrence_count` = number of docs where A and C each appear as a concept or as a
  substring of the normalized title (`discover.py` ~L527).
- The existing time-split harness `validate.py` (`split_by_year`, `concept_pool`, `validate_retrospective`) is the model
  for this backtest. Its confirmation rule (`future_cooccurrence > 0`) is too weak for this test and is replaced by §3.

Parameters are fixed at code defaults except `max_links`, which is set to **1000**, so the engine returns every candidate and
truncation to 20 happens in §3 for every method the same way. No other parameter may change (see §7).

## 1. Data snapshot (frozen at a 2015 cutoff)

1.1 Source: the OpenAlex full snapshot on S3, `s3://openalex/data/works/`, `.../concepts/`, read with
`aws s3 sync --no-sign-request`. No REST API calls.

1.2 Release pin: the **most recent snapshot release whose `data/works/manifest` is dated on or before 2026-10-22**.
The release date and `manifest` sha256 are written to `backtest/SNAPSHOT.md` before any other file is pulled. If that release
lacks the legacy `concepts` field on works, abort (§7.3). Pinning by rule, not by date, is an open question for QA (see the end of this file).

1.3 Filters applied to the pulled works, in this order:
- Main corpus: `publication_date <= 2015-12-31`. Future corpus: the **union of the 3 domain filters** (D1 ∪ D2 ∪ D3), `2016-01-01 <= publication_date <= 2024-12-31`, from the **same pinned snapshot**, hashed in `SNAPSHOT.sha256` like every other derived file.
  Swanson corpus: `publication_date <= 1985-12-31`.
- `publication_date` is authoritative. If it is missing, fall back to `publication_year` (≤2015 → past, 2016-2024 → future).
  If both are missing, the work is excluded. Excluded counts are reported per corpus.
- Late-added works: a work is included by its publication date, whatever its `created_date`. All of them come from the one
  pinned release, so later additions can't leak in. `updated_date` is ignored.
- `is_retracted = true` and `type` in {`paratext`, `erratum`} are excluded.
- Domain membership: the work's `concepts` include the domain's level-0 concept ID (§2) with `score >= 0.3`.
- Doc conversion for `LocalCorpusClient`: `{"id", "year": publication_year, "title": display_name, "concepts":
  [display_name for concepts with score >= 0.3, in OpenAlex order], "cited_by_count", "primary_l0": highest-scoring level-0 concept}`.
  Docs are written as JSONL sorted by OpenAlex work ID ascending, because `concept_counts` takes the first 50 matches in file order.

1.4 Hashing: sha256 of every pulled raw `.gz` part file and of every derived JSONL file, in `sha256sum` format, in
`backtest/SNAPSHOT.sha256`. The sha256 of that file goes in `backtest/SNAPSHOT.md`.

1.5 `SNAPSHOT.md` also records: the release date, the S3 prefixes, the filters above verbatim, the record counts per corpus and
exclusion reason, the engine commit hash, and the build-script commit hash. Snapshot files and the manifest are committed (or the
manifest only, if the data is too large, with the data kept on the box and re-hashed before each run) **before any ranking run**.

## 2. Domains (chosen before seeing any data)

They are taken from the repo's own packs (`src/artificial_emotions/packs/`), so the domain choice isn't fitted to this test.
Each domain is a level-0 OpenAlex concept plus five seed concepts A (matched by exact `display_name` in the pinned concepts
entity file; if any seed has no exact match, abort per §7.3. No substitutes are allowed).

| # | Domain (pack) | Level-0 concept ID | Seed concepts A |
|---|---|---|---|
| D1 | Aging biology (`aging_biology.json`) | `C86803240` Biology | Senescence; Autophagy; Sirtuin; Caloric restriction; Telomere |
| D2 | Materials / catalysis (`materials_catalysis.json`) | `C192562407` Materials science | Catalysis; Perovskite (structure); Graphene; Metal-organic framework; Electrocatalyst |
| D3 | Climate adaptation (`climate_adaptation.json`) | `C39432304` Environmental science | Climate change; Drought tolerance; Urban heat island; Coral bleaching; Sea level rise |

Reasons: there is one life-science, one physical-science and one environmental domain. All three were active from 2016 to 2024,
so "pursued" is measurable. All three already have repo packs, and none of them is the Swanson domain (§6). The level-0 IDs are
OpenAlex's standard root concepts; the exact display names of the seeds are confirmed by the deterministic lookup in §2 (open question below).

## 3. Candidate pool, unknowns and the metric

3.1 Candidate pool P_d (shared by every method) for domain d: all pairs (A, C) where A is a seed of d, and C is among
the **300 most frequent concepts** in d's past corpus (ties broken by name), C ≠ A, C not in `_STOP_CONCEPTS`,
and C is not a level-0 concept.

3.2 Unknown: (A, C) is an unknown if and only if its past co-occurrence is 0, computed with `LocalCorpusClient.cooccurrence_count` on the
past domain corpus. Each method may rank only unknowns in P_d. Engine links that are not unknowns, or not in P_d, are dropped
**before** taking its top 20. Duplicate (A, C) pairs from different bridges keep their highest rank.

3.3 Seed merge and top 20. The engine runs once per seed concept A (5 runs per domain). The 5 runs are **pooled**; each **unordered (A, C) pair is deduped, keeping its max `gap`**; the pooled list is **sorted globally by `gap` descending**, ties broken by **seed-concept pack order** (the order of seeds in §2's table), then **lexical (A, C)**; the **top 20** are taken. Baselines produce their 20 per domain as in §4. Each method's top 20 consists of unknowns only (§3.2). If a method returns fewer than 20, the missing slots count as misses
(and are reported).

3.4 Later check (deterministic code only; no human judgment). A future work **co-mentions** (A, C) when, in the future corpus
(union of the 3 domain filters, 2016-01-01..2024-12-31, same pinned snapshot, hashed; §1.3), A and C each match the doc by the same rule as `cooccurrence_count`
(normalized concept name, or a substring of the normalized title).
- **Pursued:** at least **5** co-mentioning works published from 2016-01-01 to 2024-12-31.
- **Highly cited:** at least **1** co-mentioning work that is in the top 10% for its field and year. **Primary rule:** OpenAlex
  `citation_normalized_percentile.value >= 0.90` (equivalently `citation_normalized_percentile.is_in_top_10_percent = true`) in the pinned snapshot.
  **Fallback** (only for works where that field is missing): `cited_by_count` at or above the 90th percentile among all works in the **full pinned
  snapshot** with the same `primary_topic.field` **and** the same `publication_year`. The number of works judged by each rule is reported.
- **Hit** = pursued OR highly cited.

3.5 Metric: per method and domain, **hit rate = hits / 20**. Secondary (reported, not used for pass): pursued-only rate, highly-cited-only rate,
and the base rate of hits across all of P_d.

## 4. Baselines (each gives 20 unknowns per domain from P_d)

4.1 **Random.** The unknowns in P_d are **sorted lexically by (A, C) BEFORE seeded sampling**; then a uniform sample without replacement of 20 is drawn with `random.Random(s).sample(sorted_unknowns, 20)`,
for each s in RANDOM_SEEDS (§7.1, 100 seeds). The baseline score is the mean hit rate over the seeds, and the distribution is kept for §5.

4.2 **Citation-trend.** For a concept X in domain d, growth(X) = (n_2015(X) + 1) / (n_2013(X) + 1), where n_y = the number of past-corpus
docs from year y that match X (same matching rule). The pair score is sqrt(growth(A) · growth(C)). Since unknowns have zero co-occurrence,
growth uses each concept's own volume. The top 20 unknowns by score are taken, with ties broken by (A, C) lexically. The window is 2013-2015 only.

4.3 **LLM-picked.**
- Runner: **Loop-Engineering's** sandboxed cursor-agent shim, `KanakMalpani/Loop-Engineering: benchmarks/loopbench-validity/cursor_llm.py` (bubblewrap sandbox; not part of this repo), **cursor-agent `2026.10.19-6bbf2c4`** (from `cursor-agent --version` on 2026-10-21), model **`grok-4.7-high`** pinned (non-fast; no alias). No paid API; no OpenAI.
- Temperature: **cannot be set** through cursor-agent and is not applied (logged as `temperature_applied=false`). Variance comes only from runs 101-105, which are **5 independent repeat calls**, labelled LLM_SEEDS 101-105 (the seed is recorded with each call, not passed to the model). Score = **median** hit rate over the 5 calls; tie → lowest seed.
- Input: Appendix A prompt with the domain name and the full list of unknowns in P_d as `A | C` lines, lexical order. Only pre-2016 inputs: pair names drawn from the past corpus; no years, counts, citations or future data. The agent runs with no tools/web (sandboxed, no network beyond the model endpoint, empty workspace).
- Parsing: first 20 valid, distinct lines exactly matching a listed pair; invalid lines skipped; < 20 valid → missing slots are misses. Every raw reply stored.
- Knowledge-cutoff leak: the model was trained on 2016-2024 literature and may "remember" what was pursued. This **cannot be removed**, only reported. It favours the baseline (makes the test harder for the engine). The LLM result is labelled **"contaminated upper-bound baseline"**; the pass rule (§5) is also reported with and without the LLM baseline, but only the with-LLM version counts as PASS.

## 5. Pass threshold (one rule, relative to all three baselines)

For each domain d and baseline b, the engine **beats** b when both of these hold:
1. hit_rate(engine) − score(b) ≥ **0.10** (absolute, i.e. at least 2 more hits out of 20), and
2. a one-sided test gives **p < 0.05**:
   - vs random: p = (1 + #{random seeds with hit rate ≥ engine}) / (1 + 100).
   - vs citation-trend and LLM: a paired-label permutation test. Pool the 40 hit labels (20 + 20), randomly reassign them to the two methods
     **10,000** times with PERM_SEED, and take p = (1 + #{permuted difference ≥ observed}) / (1 + 10,000). For LLM, the median-seed run is used,
     with ties broken by the lowest seed.

A tie (difference < 0.10, or p ≥ 0.05) means **not beaten**. There is no multiple-comparison correction (9 comparisons). This is stated up front and is a known threat.

**PASS** = the engine beats **all three** baselines in **at least 2 of 3** domains (a majority, not all), **and** the Swanson test (§6) passes.
Anything else is **FAIL**.

Secondary metric (reported only, never used for pass): **lift over random** = engine hit rate / mean random hit rate (RANDOM_SEEDS), per domain; reported as "undefined" if the mean random hit rate is 0.

Context for the bar (from `prior-art.md`, 2026-10-21; not a target and not used for pass): LitLinker (Yetisgen-Yildiz & Pratt, J Biomed Inform 2009, https://doi.org/10.1016/j.jbi.2008.12.001) set the time-sliced protocol with P@k and MAP; Tshitoyan et al. (Nature 2019, https://www.nature.com/articles/s41586-019-1335-8) report top-50 predictions ~8x more likely than random to be confirmed within 5 years; AGATHA (Sybrandt et al., CIKM 2020, https://arxiv.org/abs/2002.05635) ROC AUC 0.901 on a post-2015 holdout; Science4Cast (Krenn et al., Nat Mach Intell 2023, https://www.nature.com/articles/s42256-023-00735-0) best AUC 0.917 three years ahead. These use different corpora, metrics and pool sizes, so they are not directly comparable to hit-rate@20; the pass rule above is unchanged. Seed variance: random and LLM use the distributions or medians above. The engine and citation-trend are deterministic, which is checked by running each twice and requiring identical output (otherwise INFRA-FAIL).

## 6. Swanson rediscovery test (fish oil → Raynaud's), pre-1986 only

- Data: the same pinned OpenAlex release, works with `publication_date <= 1985-12-31` (fallback `publication_year <= 1985`), restricted to works with level-0
  concept `C71924100` (Medicine), score ≥ 0.3. Built the same way as §1.3 (sorted by ID, hashed in `SNAPSHOT.sha256`).
  Swanson's own 1986 paper and anything after 1985 are excluded by the date filter.
- Run: `discover_links(a="Raynaud's phenomenon", client=LocalCorpusClient(swanson_corpus), max_links=1000)`, with all other parameters at defaults.
  If "Raynaud's phenomenon" is not an exact concept display name, use the exact display name containing "Raynaud" with the most past docs. This rule is fixed now.
- Target C: any link whose normalized C contains "fish oil", "eicosapentaenoic", "omega-3" or "fatty acids, omega-3".
- **Pass rule:** a target C appears at rank **≤ 20** of the engine's links (K = 20). The rank is reported, along with which bridge B produced it.
- Leakage guard: no LLM is used anywhere in the Swanson test. The only leak path is OpenAlex's concept tagger, a modern model applied to old works. It is reported as a threat (§8) and can't be mitigated.

## 7. Seeds, fails, no-tuning, commit order

7.1 Seeds:
- RANDOM_SEEDS = 0, 1, 2, …, 99 (100 seeds).
- LLM_SEEDS = 101, 102, 103, 104, 105.
- PERM_SEED = 20151231.
- The engine and citation-trend have no randomness.

7.2 Outcomes:
- **FAIL:** the pass rule in §5 or §6 isn't met. It is reported as-is and isn't re-run.
- **INFRA-FAIL:** S3 read errors, hash mismatch against `SNAPSHOT.sha256`, LLM/cursor-agent errors or timeouts after the retry policy (3 retries, exponential backoff 2/4/8 s, all logged in `backtest/run.log`), or non-deterministic output.
  An INFRA-FAIL is fixed and the run is redone **without any change to parameters, data or prompt**. Every INFRA-FAIL and retry is logged with a timestamp in `run.log` and listed in the report.
- **ABORT** (no result; it needs a deviation entry and a re-freeze before any rerun):
  - a seed concept or level-0 ID doesn't resolve;
  - a domain past corpus has < 1,000 docs, or P_d has < 100 unknowns;
  - the pinned release lacks the `concepts` field;
  - any frozen file is modified after the first ranking run.

7.3 **No-tuning rule.** After the first data pull, nothing in §0-§6 changes. That covers engine parameters, the pool size of 300, thresholds, seeds, the prompt, the model id, domains and matching rules.
Any change needs a dated entry in `backtest/DEVIATION.md` **and** a new freeze (an updated `PREREG.md` hash in `SNAPSHOT.md`, committed) before further runs.
The result is then labelled exploratory, not confirmatory. Results are never inspected on a subset and then used to pick parameters.

7.4 Commit order (each one pushed before the next):
1. `backtest/PREREG.md` (this file).
2. Snapshot build script and `SNAPSHOT.md` + `SNAPSHOT.sha256`. No ranking code has run yet.
3. The run script, committed before it runs, plus a stub-only test showing that the reference pipeline handles a toy corpus. The test makes no network calls.
4. The runs, then `backtest/results/*`, `run.log` and the raw LLM replies.

Repo history check (2026-10-21): `git ls-files` and `git log --all` show **no cached OpenAlex data and no backtest scripts**. Related existing files are `examples/discovery_corpus_timesplit_demo.json`
(a toy hand-written corpus), `validate.py` (time-split harness), `evals/fixtures/cooccur_neglectedness_smoke_v1.json`, and commit `e14c170` (research notes on an OpenAlex adapter). None of these is backtest data.

## 8. Threats to validity

- **Concept tagger leakage:** OpenAlex concepts are assigned by a modern classifier, which may encode post-2015 associations. This affects all methods equally except the LLM.
- **LLM contamination:** see §4.3.
- **Training-cutoff check:** `grok-4.7-high`'s training data postdates 2024, so it has likely seen the outcomes. Before the run (no model call before the freeze), the documented training cutoff is recorded in `SNAPSHOT.md` if published, else "unknown". After the run, the share of LLM picks that are hits is compared with the engine's and random's; an LLM hit rate far above both is reported as probable recall, not foresight. No mitigation beyond labelling.
- **Temperature not settable:** LLM variance across 5 calls is uncontrolled sampling, not a fixed temperature.
- **Retrofitted metadata:** citation counts and titles come from the current snapshot. Highly-cited counts favor earlier future years, which the per-year percentile partly offsets.
- **Engine shortcuts:** `concept_counts` reads only the first 50 matching docs (ID order), and the `/10` similarity scaling is arbitrary. The engine is tested as-is.
- **Matching:** title-substring matching is noisy for short terms (e.g. "MOF"), and the absence of an abstract undercounts co-mentions. The same noise applies to every method.
- **Legacy concepts:** OpenAlex has deprecated concepts in favor of topics, and coverage can differ between releases.
- **Small samples:** 20 items per domain gives low power, and there's no multiple-comparison correction.
- **Pool choice:** the 300-concept cap and the domain filter shape what can be found. Both were fixed before data.
- **Generalization:** one Swanson case shows only that a known discovery can be recovered.

## Amendment 1 (2026-10-21, IST; before any data pull or run)

Doc-only clarifications for QA gaps, no results seen: §3.3 seed merge (pool 5 runs, dedupe unordered (A,C) keeping max gap, global sort by gap desc, ties by seed pack order then lexical (A,C), top 20); §1.3/§3.4 future corpus = union of the 3 domain filters, 2016-01-01..2024-12-31, same pinned snapshot, hashed; highly cited = `citation_normalized_percentile >= 0.90` / `is_in_top_10_percent`, fallback 90th percentile within primary field × year over the full snapshot; §4.1 lexical sort of P_d before seeded sampling; §4.3 shim is Loop-Engineering's `benchmarks/loopbench-validity/cursor_llm.py`.

## Amendment 2 (2026-10-21, IST; before any data pull or run)

Doc-only; no results seen. Supersedes any conflicting text above.

1. **Shim copy and pin.** In the run-script commit (§7.4 step 3), Loop-Engineering's `benchmarks/loopbench-validity/cursor_llm.py` is **copied** into this repo as `backtest/cursor_llm.py`. The run manifest records the **source Loop-Engineering commit hash** and the copy's **sha256**. As read on 2026-10-21, those are source commit `8b1bfc1` and sha256 `1ea827efb925ac251ae93fd082b7257143056521685c4e89b936058ac1c9c999`. If the copied file differs, its own sha256 is recorded at that commit. Nothing in the backtest imports or calls across repos. A sha256 mismatch at run time is ABORT.
2. **Pre-run no-network probe.** After the freeze and **before the first LLM call**, a **logged probe** (in `backtest/run.log`, stored with its raw output) confirms that the sandboxed agent **cannot reach the network beyond the model endpoint, and cannot read the snapshot files or the future corpus**. If the probe fails, the run is **ABORT**: no LLM calls are made, and a dated DEVIATION entry plus a re-freeze are required before a retry.
3. **LLM runs 101-105** are **5 independent repeat calls** of the same prompt per domain, scored by the median (§4.3).
4. Open question 5 is closed.

## Open questions (repo/brief ambiguous)

1. The engine has no date filter on the live `OpenAlexClient` (`openalex.py`). The backtest therefore uses `LocalCorpusClient` on a snapshot, not the live client. Confirm.
2. The release is pinned by rule (§1.2), not by a named date, because naming one would need a call. The actual date is recorded in `SNAPSHOT.md` before the pull. QA to accept.
3. Concept IDs: the level-0 IDs are standard, but the seed concept display names are resolved by exact match at snapshot time (abort if missing). Specific seed IDs were not looked up, because looking them up needs a call.
4. The default `max_links=8` makes "top 20" impossible, so it's set to 1000 (§0). This is the only parameter change.
5. CLOSED by Amendment 2: the shim is copied into this repo and pinned by its source commit and sha256; it does not point across repos.

## Appendix A: LLM prompt (exact text)

System:
```
You are a research strategist. Today is 31 December 2015. You know nothing published after that date.
```
User (`{DOMAIN}` and `{PAIRS}` substituted; nothing else changes):
```
Domain: {DOMAIN}
Below are pairs of research concepts "A | C" that, as of the end of 2015, have never been studied together.
Pick the 20 pairs most likely to become an active, well-cited research direction in the next decade.
Answer with exactly 20 lines, each copied exactly from the list in the form "A | C", most promising first. No other text.

{PAIRS}
```
