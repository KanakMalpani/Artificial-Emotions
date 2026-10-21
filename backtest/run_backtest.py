"""Backtest run script for backtest/PREREG.md (+ DEVIATION.md Deviation 1).

Hand-written, Kanak-approved exception, cursor-agent held for attempt 3.

Implements the frozen spec: candidate pool and unknowns (§3.1-3.2), engine seed
merge (§3.3), later check / hit (§3.4), metric (§3.5), random baseline (§4.1),
citation-trend baseline (§4.2), pass rule (§5), Swanson test (§6), seeds and
outcomes (§7). The LLM baseline (§4.3) is NOT implemented here: it is held, and
results are accepted only as a pre-computed JSON (``--llm-results``). Without
it the verdict is reported as ``INCOMPLETE``.

No network access. Reads only local files: the derived snapshot JSONL under
``--data-dir``, the concepts entity files under ``--concepts-dir``, and the
citation histograms under ``--hist-dir``. Refuses to run without ``--confirm``.
"""

from __future__ import annotations

import argparse
import datetime as dt
import gzip
import hashlib
import json
import math
import random
import statistics
import sys
from collections import Counter, defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from artificial_emotions.discover import _STOP_CONCEPTS, LocalCorpusClient, _norm, discover_links

# --- Frozen constants (PREREG §2, §3, §5, §7.1; DEVIATION.md Deviation 1) ---

DOMAINS: dict[str, dict[str, Any]] = {
    "D1": {
        "name": "Aging biology",
        "l0": "C86803240",
        # Deviation 1 (a): "Caloric restriction" -> "Calorie restriction" (C2778707264).
        "seeds": ["Senescence", "Autophagy", "Sirtuin", "Calorie restriction", "Telomere"],
    },
    "D2": {
        "name": "Materials / catalysis",
        "l0": "C192562407",
        "seeds": [
            "Catalysis",
            "Perovskite (structure)",
            "Graphene",
            "Metal-organic framework",
            "Electrocatalyst",
        ],
    },
    "D3": {
        "name": "Climate adaptation",
        "l0": "C39432304",
        "seeds": [
            "Climate change",
            "Drought tolerance",
            "Urban heat island",
            "Coral bleaching",
            "Sea level rise",
        ],
    },
}
MEDICINE_L0 = "C71924100"

MAX_LINKS = 1000  # §0: the only engine parameter changed from defaults.
POOL_SIZE = 300  # §3.1
TOP_K = 20  # §3.3
PURSUED_MIN = 5  # §3.4
HIGH_CITE_PCT = 0.90  # §3.4
MARGIN = 0.10  # §5
P_THRESHOLD = 0.05  # §5
N_PERM = 10_000  # §5
RANDOM_SEEDS = list(range(100))  # §7.1
LLM_SEEDS = [101, 102, 103, 104, 105]  # §7.1
PERM_SEED = 20151231  # §7.1
MIN_PAST_DOCS = 1000  # §7.2 ABORT
MIN_UNKNOWNS = 100  # §7.2 ABORT
SWANSON_K = 20  # §6
SWANSON_START = "Raynaud's phenomenon"  # §6
SWANSON_TARGETS = ("fish oil", "eicosapentaenoic", "omega-3", "fatty acids, omega-3")  # §6

Pair = tuple[str, str]


class Abort(RuntimeError):
    """PREREG §7.2 ABORT: no result; needs a deviation entry and a re-freeze."""


class InfraFail(RuntimeError):
    """PREREG §7.2 INFRA-FAIL: fix and redo without changing parameters."""


# --- Logging (§7.2: every INFRA-FAIL / retry logged with a timestamp) ---


class RunLog:
    def __init__(self, path: Path | None):
        self.path = path

    def __call__(self, msg: str) -> None:
        line = f"{dt.datetime.now(dt.UTC).isoformat()} {msg}"
        if self.path is not None:
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        print(line, file=sys.stderr)


# --- Loading ---


def _work_key(doc: dict[str, Any]) -> tuple[int, str]:
    wid = str(doc.get("id") or "")
    digits = wid.lstrip("Ww")
    return (int(digits) if digits.isdigit() else sys.maxsize, wid)


def load_docs(paths: Iterable[Path]) -> list[dict[str, Any]]:
    """Load derived JSONL(.gz) docs and sort by OpenAlex work ID ascending (§1.3)."""
    docs: list[dict[str, Any]] = []
    for p in sorted(paths):
        opener = gzip.open if p.suffix == ".gz" else open
        with opener(p, "rt", encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    docs.append(json.loads(line))
    docs.sort(key=_work_key)
    return docs


def load_level0_names(concepts_dir: Path) -> tuple[set[str], set[str]]:
    """Return (normalized level-0 names, normalized all display names) from the concepts entity files."""
    level0: set[str] = set()
    names: set[str] = set()
    for p in sorted(concepts_dir.glob("*.gz")):
        with gzip.open(p, "rt", encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                rec = json.loads(line)
                name = _norm(rec.get("display_name") or "")
                names.add(name)
                if rec.get("level") == 0:
                    level0.add(name)
    return level0, names


def load_hist(hist_dir: Path) -> dict[tuple[str, int], Counter[int]]:
    """Merge per-part citation histograms: (field, year) -> Counter(cited_by_count)."""
    out: dict[tuple[str, int], Counter[int]] = defaultdict(Counter)
    for p in sorted(hist_dir.glob("*.json")):
        data = json.loads(p.read_text(encoding="utf-8"))
        for key, n in (data.get("hist") or {}).items():
            fld, yr, cbc = key.split("|")
            out[(fld, int(yr))][int(cbc)] += int(n)
    return out


def verify_hashes(sha_file: Path, base: Path, log: RunLog) -> None:
    """§7.2: a hash mismatch against SNAPSHOT.sha256 is INFRA-FAIL."""
    for line in sha_file.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        want, rel = line.split(None, 1)
        p = base / rel.strip().lstrip("*")
        if not p.exists():
            if rel.strip().startswith("works/"):
                continue  # raw parts are deleted after filtering; only derived files are re-hashed
            log(f"INFRA-FAIL missing derived file {rel}")
            raise InfraFail(f"missing derived file: {rel}")
        got = hashlib.sha256(p.read_bytes()).hexdigest()
        if got != want:
            log(f"INFRA-FAIL hash mismatch {rel}")
            raise InfraFail(f"hash mismatch: {rel}")


# --- Matching (same rule as LocalCorpusClient.cooccurrence_count) ---


def _doc_terms(doc: dict[str, Any]) -> tuple[set[str], str]:
    return {_norm(c) for c in doc.get("concepts") or []}, _norm(doc.get("title") or "")


def matches(doc_terms: tuple[set[str], str], term: str) -> bool:
    concepts, title = doc_terms
    t = _norm(term)
    return t in concepts or t in title


class TermIndex:
    """term -> set of doc indices that match it, for a fixed list of terms."""

    def __init__(self, docs: list[dict[str, Any]], terms: Iterable[str]):
        self.docs = docs
        self.terms = sorted({_norm(t) for t in terms if _norm(t)})
        self.index: dict[str, set[int]] = {t: set() for t in self.terms}
        for i, doc in enumerate(docs):
            dt_ = _doc_terms(doc)
            for t in self.terms:
                if matches(dt_, t):
                    self.index[t].add(i)

    def co(self, a: str, c: str) -> set[int]:
        return self.index.get(_norm(a), set()) & self.index.get(_norm(c), set())


# --- §3.1 / §3.2 candidate pool and unknowns ---


def concept_frequencies(docs: list[dict[str, Any]]) -> Counter[str]:
    freq: Counter[str] = Counter()
    for doc in docs:
        for name in {str(c).strip() for c in doc.get("concepts") or [] if str(c).strip()}:
            freq[name] += 1
    return freq


def candidate_pool(
    past_docs: list[dict[str, Any]], seeds: list[str], level0_names: set[str]
) -> list[Pair]:
    freq = concept_frequencies(past_docs)
    top = [n for n, _ in sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))[:POOL_SIZE]]
    pool: list[Pair] = []
    for a in seeds:
        for c in top:
            nc = _norm(c)
            if nc == _norm(a) or nc in _STOP_CONCEPTS or nc in level0_names:
                continue
            pool.append((a, c))
    return pool


def _ukey(pair: Pair) -> frozenset[str]:
    return frozenset((_norm(pair[0]), _norm(pair[1])))


def unknowns(pool: list[Pair], past_client: LocalCorpusClient) -> list[Pair]:
    seen: set[frozenset[str]] = set()
    out: list[Pair] = []
    for a, c in pool:
        k = _ukey((a, c))
        if k in seen:
            continue
        seen.add(k)
        if past_client.cooccurrence_count(a, c) == 0:
            out.append((a, c))
    return out


# --- §3.3 engine with seed merge ---


def engine_top(
    seeds: list[str], past_client: LocalCorpusClient, unknown_set: list[Pair]
) -> list[Pair]:
    allowed = {_ukey(p): p for p in unknown_set}
    best: dict[frozenset[str], tuple[float, int, Pair]] = {}
    for order, a in enumerate(seeds):
        for link in discover_links(a, client=past_client, max_links=MAX_LINKS):
            k = _ukey((link.a, link.c))
            if k not in allowed:
                continue
            cur = best.get(k)
            if cur is None or link.gap > cur[0]:
                best[k] = (float(link.gap), order, allowed[k])
    ranked = sorted(best.values(), key=lambda v: (-v[0], v[1], v[2][0], v[2][1]))
    return [p for _, _, p in ranked[:TOP_K]]


# --- §4.1 random, §4.2 citation-trend ---


def random_top(unknown_set: list[Pair], seed: int) -> list[Pair]:
    ordered = sorted(unknown_set)
    return random.Random(seed).sample(ordered, min(TOP_K, len(ordered)))


def citation_trend_top(unknown_set: list[Pair], past_docs: list[dict[str, Any]]) -> list[Pair]:
    terms = {t for p in unknown_set for t in p}
    by_year = {y: [d for d in past_docs if d.get("year") == y] for y in (2013, 2015)}
    idx = {y: TermIndex(by_year[y], terms) for y in by_year}

    def growth(x: str) -> float:
        n15 = len(idx[2015].index.get(_norm(x), ()))
        n13 = len(idx[2013].index.get(_norm(x), ()))
        return (n15 + 1) / (n13 + 1)

    scored = [(math.sqrt(growth(a) * growth(c)), (a, c)) for a, c in unknown_set]
    scored.sort(key=lambda v: (-v[0], v[1]))
    return [p for _, p in scored[:TOP_K]]


# --- §3.4 later check ---


def p90_thresholds(hist: dict[tuple[str, int], Counter[int]]) -> dict[tuple[str, int], int]:
    """90th percentile of cited_by_count per (field, year), nearest-rank method."""
    out: dict[tuple[str, int], int] = {}
    for key, counter in hist.items():
        total = sum(counter.values())
        if total == 0:
            continue
        rank = math.ceil(HIGH_CITE_PCT * total)
        acc = 0
        for cbc in sorted(counter):
            acc += counter[cbc]
            if acc >= rank:
                out[key] = cbc
                break
    return out


class Checker:
    def __init__(
        self,
        future_docs: list[dict[str, Any]],
        terms: Iterable[str],
        p90: dict[tuple[str, int], int],
    ):
        self.docs = future_docs
        self.idx = TermIndex(future_docs, terms)
        self.p90 = p90
        self.judged_primary = 0
        self.judged_fallback = 0
        self.judged_none = 0

    def _top10(self, doc: dict[str, Any]) -> bool:
        cnp, top10 = doc.get("cnp"), doc.get("top10")
        if cnp is not None or top10 is not None:
            self.judged_primary += 1
            return bool(top10) or (cnp is not None and float(cnp) >= HIGH_CITE_PCT)
        thr = self.p90.get((str(doc.get("field") or ""), int(doc.get("year") or 0)))
        if thr is None:
            self.judged_none += 1
            return False
        self.judged_fallback += 1
        return int(doc.get("cited_by_count") or 0) >= thr

    def check(self, pair: Pair) -> dict[str, Any]:
        ids = sorted(self.idx.co(*pair))
        ids = [i for i in ids if 2016 <= int(self.docs[i].get("year") or 0) <= 2024]
        pursued = len(ids) >= PURSUED_MIN
        high = any(self._top10(self.docs[i]) for i in ids)
        return {
            "a": pair[0],
            "c": pair[1],
            "co_mentions": len(ids),
            "pursued": pursued,
            "highly_cited": high,
            "hit": pursued or high,
        }


def score(top: list[Pair], checker: Checker) -> dict[str, Any]:
    rows = [checker.check(p) for p in top]
    hits = [r["hit"] for r in rows] + [False] * (TOP_K - len(rows))  # §3.3 missing slots = misses
    return {
        "items": rows,
        "returned": len(rows),
        "labels": hits,
        "hit_rate": sum(hits) / TOP_K,
        "pursued_rate": sum(r["pursued"] for r in rows) / TOP_K,
        "highly_cited_rate": sum(r["highly_cited"] for r in rows) / TOP_K,
    }


# --- §5 statistics ---


def p_vs_random(engine_rate: float, random_rates: list[float]) -> float:
    return (1 + sum(r >= engine_rate for r in random_rates)) / (1 + len(random_rates))


def permutation_p(
    engine_labels: list[bool], other_labels: list[bool], seed: int = PERM_SEED
) -> float:
    n = len(engine_labels)
    observed = (sum(engine_labels) - sum(other_labels)) / n
    pooled = [int(x) for x in engine_labels] + [int(x) for x in other_labels]
    rng = random.Random(seed)
    ge = 0
    for _ in range(N_PERM):
        rng.shuffle(pooled)
        diff = (sum(pooled[:n]) - sum(pooled[n:])) / n
        if diff >= observed:
            ge += 1
    return (1 + ge) / (1 + N_PERM)


def beats(diff: float, p: float) -> bool:
    return diff >= MARGIN - 1e-12 and p < P_THRESHOLD


def llm_median(llm_runs: dict[int, dict[str, Any]]) -> tuple[int, dict[str, Any]]:
    """§4.3: median hit rate over LLM_SEEDS; ties -> lowest seed."""
    rates = sorted(llm_runs[s]["hit_rate"] for s in LLM_SEEDS)
    med = statistics.median_low(rates)
    seed = min(s for s in LLM_SEEDS if llm_runs[s]["hit_rate"] == med)
    return seed, llm_runs[seed]


# --- §6 Swanson ---


def swanson(swanson_docs: list[dict[str, Any]], entity_names: set[str]) -> dict[str, Any]:
    start = SWANSON_START
    if _norm(start) not in entity_names:
        cands = sorted({n for n in entity_names if "raynaud" in n})
        counts = {
            n: sum(1 for d in swanson_docs if n in {_norm(c) for c in d.get("concepts") or []})
            for n in cands
        }
        if not counts:
            raise Abort("no concept display name contains 'Raynaud'")
        start = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
    client = LocalCorpusClient(documents=swanson_docs)
    links = discover_links(start, client=client, max_links=MAX_LINKS)
    rank, bridge, target = None, None, None
    for i, link in enumerate(links, 1):
        if any(t in _norm(link.c) for t in SWANSON_TARGETS):
            rank, bridge, target = i, link.b, link.c
            break
    return {
        "start": start,
        "n_docs": len(swanson_docs),
        "n_links": len(links),
        "target_rank": rank,
        "target_c": target,
        "bridge": bridge,
        "pass": rank is not None and rank <= SWANSON_K,
    }


# --- Orchestration ---


def run(
    docs: list[dict[str, Any]],
    level0_names: set[str],
    entity_names: set[str],
    hist: dict[tuple[str, int], Counter[int]],
    log: RunLog,
    llm_results: dict[str, dict[int, dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    for spec in DOMAINS.values():
        for s in spec["seeds"]:
            if _norm(s) not in entity_names:
                raise Abort(f"seed concept does not resolve: {s}")

    future = [d for d in docs if d.get("seg") == "future"]
    p90 = p90_thresholds(hist)
    result: dict[str, Any] = {"domains": {}, "constants": _constants()}
    pending_checks: dict[str, dict[str, list[Pair]]] = {}
    term_set: set[str] = set()

    for did, spec in DOMAINS.items():
        past = [d for d in docs if d.get("seg") == "past" and did in (d.get("domains") or [])]
        if len(past) < MIN_PAST_DOCS:
            raise Abort(f"{did}: past corpus has {len(past)} docs (< {MIN_PAST_DOCS})")
        client = LocalCorpusClient(documents=past)
        pool = candidate_pool(past, spec["seeds"], level0_names)
        unk = unknowns(pool, client)
        if len(unk) < MIN_UNKNOWNS:
            raise Abort(f"{did}: {len(unk)} unknowns (< {MIN_UNKNOWNS})")
        eng = engine_top(spec["seeds"], client, unk)
        if engine_top(spec["seeds"], client, unk) != eng:
            log(f"INFRA-FAIL {did} engine non-deterministic")
            raise InfraFail(f"{did}: engine output not deterministic")
        ct = citation_trend_top(unk, past)
        if citation_trend_top(unk, past) != ct:
            log(f"INFRA-FAIL {did} citation-trend non-deterministic")
            raise InfraFail(f"{did}: citation-trend output not deterministic")
        rnd = {s: random_top(unk, s) for s in RANDOM_SEEDS}
        pending_checks[did] = {"engine": eng, "citation_trend": ct, "pool": unk}
        pending_checks[did].update({f"random_{s}": v for s, v in rnd.items()})
        term_set.update(t for p in unk for t in p)
        result["domains"][did] = {
            "n_past_docs": len(past),
            "n_pool": len(pool),
            "n_unknowns": len(unk),
        }
        log(f"{did} past={len(past)} pool={len(pool)} unknowns={len(unk)}")

    checker = Checker(future, term_set, p90)
    domain_beats_all: list[bool] = []
    domain_beats_no_llm: list[bool] = []
    for did, lists in pending_checks.items():
        r = result["domains"][did]
        eng = score(lists["engine"], checker)
        ct = score(lists["citation_trend"], checker)
        rnd_rates = [score(lists[f"random_{s}"], checker)["hit_rate"] for s in RANDOM_SEEDS]
        base_rows = [checker.check(p) for p in lists["pool"]]
        r["engine"] = eng
        r["citation_trend"] = ct
        r["random"] = {"mean_hit_rate": statistics.fmean(rnd_rates), "hit_rates": rnd_rates}
        r["pool_base_rate"] = sum(x["hit"] for x in base_rows) / len(base_rows)
        mean_rnd = r["random"]["mean_hit_rate"]
        r["lift_over_random"] = (eng["hit_rate"] / mean_rnd) if mean_rnd > 0 else "undefined"

        cmp: dict[str, Any] = {}
        diff = eng["hit_rate"] - mean_rnd
        p = p_vs_random(eng["hit_rate"], rnd_rates)
        cmp["random"] = {"diff": diff, "p": p, "beaten": beats(diff, p)}
        diff = eng["hit_rate"] - ct["hit_rate"]
        p = permutation_p(eng["labels"], ct["labels"])
        cmp["citation_trend"] = {"diff": diff, "p": p, "beaten": beats(diff, p)}
        llm_dom = (llm_results or {}).get(did)
        if llm_dom:
            seed, run_ = llm_median(llm_dom)
            diff = eng["hit_rate"] - run_["hit_rate"]
            p = permutation_p(eng["labels"], run_["labels"])
            cmp["llm"] = {
                "seed": seed,
                "diff": diff,
                "p": p,
                "beaten": beats(diff, p),
                "label": "contaminated upper-bound baseline",
            }
        else:
            cmp["llm"] = {"status": "held / not run"}
        r["comparisons"] = cmp
        no_llm = cmp["random"]["beaten"] and cmp["citation_trend"]["beaten"]
        domain_beats_no_llm.append(no_llm)
        domain_beats_all.append(no_llm and bool(cmp["llm"].get("beaten")))

    sw_docs = [d for d in docs if d.get("swanson")]
    result["swanson"] = swanson(sw_docs, entity_names)
    result["highly_cited_judged"] = {
        "primary": checker.judged_primary,
        "fallback": checker.judged_fallback,
        "no_threshold": checker.judged_none,
    }
    sw_pass = result["swanson"]["pass"]
    result["verdict_without_llm"] = "PASS" if sum(domain_beats_no_llm) >= 2 and sw_pass else "FAIL"
    if llm_results is None:
        result["verdict"] = "INCOMPLETE (LLM baseline held)"
    else:
        result["verdict"] = "PASS" if sum(domain_beats_all) >= 2 and sw_pass else "FAIL"
    return result


def _constants() -> dict[str, Any]:
    return {
        "max_links": MAX_LINKS,
        "pool_size": POOL_SIZE,
        "top_k": TOP_K,
        "pursued_min": PURSUED_MIN,
        "high_cite_pct": HIGH_CITE_PCT,
        "margin": MARGIN,
        "p_threshold": P_THRESHOLD,
        "n_perm": N_PERM,
        "random_seeds": RANDOM_SEEDS,
        "llm_seeds": LLM_SEEDS,
        "perm_seed": PERM_SEED,
        "swanson_k": SWANSON_K,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-dir", type=Path, default=Path("/workspace/oa/pull/out"))
    ap.add_argument("--hist-dir", type=Path, default=Path("/workspace/oa/pull/hist"))
    ap.add_argument("--concepts-dir", type=Path, default=Path("/workspace/oa/concepts"))
    ap.add_argument("--snapshot-sha", type=Path, default=Path("backtest/SNAPSHOT.sha256"))
    ap.add_argument("--hash-base", type=Path, default=Path("/workspace/oa/pull"))
    ap.add_argument("--llm-results", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=Path("backtest/results/result.json"))
    ap.add_argument("--log", type=Path, default=Path("backtest/run.log"))
    ap.add_argument(
        "--confirm", action="store_true", help="required: the snapshot is frozen and committed"
    )
    args = ap.parse_args(argv)
    if not args.confirm:
        print("refusing to run without --confirm (PREREG §7.4: SNAPSHOT first)", file=sys.stderr)
        return 2
    if not args.snapshot_sha.exists():
        print(f"missing {args.snapshot_sha}; snapshot not frozen", file=sys.stderr)
        return 2
    log = RunLog(args.log)
    try:
        verify_hashes(args.snapshot_sha, args.hash_base, log)
        docs = load_docs(list(args.data_dir.glob("*.jsonl.gz")))
        level0, names = load_level0_names(args.concepts_dir)
        hist = load_hist(args.hist_dir)
        llm = None
        if args.llm_results:
            raw = json.loads(args.llm_results.read_text(encoding="utf-8"))
            llm = {d: {int(s): v for s, v in runs.items()} for d, runs in raw.items()}
        result = run(docs, level0, names, hist, log, llm)
    except Abort as exc:
        log(f"ABORT {exc}")
        return 3
    except InfraFail as exc:
        log(f"INFRA-FAIL {exc}")
        return 4
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    log(f"done verdict={result['verdict']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
