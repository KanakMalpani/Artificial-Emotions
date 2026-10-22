"""Backtest run script for backtest/PREREG.md (+ DEVIATION.md Deviation 1, DEVIATION-2).

Hand-written, Kanak-approved exception, edited via cursor-agent (attempt 3).

Implements the frozen spec: candidate pool and unknowns (§3.1-3.2), engine seed
merge (§3.3), later check / hit (§3.4), metric (§3.5), random baseline (§4.1),
citation-trend baseline (§4.2), the LLM baseline (§4.3), pass rule (§5), Swanson
test (§6), seeds and outcomes (§7), and Amendment 2 (shim pin and pre-run probe).
Live calls use ``backtest.cursor_llm.CursorAgentLLM`` (``--run-llm``). Pre-computed
results are still accepted (``--llm-results``). Without either, the verdict is
``INCOMPLETE``.

This script does not open the network. The shim's model endpoint is the only
network path, and only when ``--run-llm`` is set. It reads local files: derived
snapshot JSONL under ``--data-dir``, concepts under ``--concepts-dir``, and
citation histograms under ``--hist-dir``. Refuses to run without ``--confirm``.
"""

from __future__ import annotations

import argparse
import bisect
import datetime as dt
import gzip
import hashlib
import json
import math
import os
import random
import statistics
import subprocess
import sys
import time
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass
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
LLM_MODEL = "grok-4.7-high"  # §4.3; passed explicitly, never the shim DEFAULT_MODEL
SHIM_SOURCE_COMMIT = "8b1bfc1"  # Amendment 2: Loop-Engineering source commit
SHIM_SHA256 = "1ea827efb925ac251ae93fd082b7257143056521685c4e89b936058ac1c9c999"
# Appendix A, byte-for-byte (fences excluded). {DOMAIN} and {PAIRS} are the only substitutions.
LLM_SYSTEM = (
    "You are a research strategist. Today is 31 December 2015. "
    "You know nothing published after that date."
)
LLM_USER_TEMPLATE = """\
Domain: {DOMAIN}
Below are pairs of research concepts "A | C" that, as of the end of 2015, have never been studied together.
Pick the 20 pairs most likely to become an active, well-cited research direction in the next decade.
Answer with exactly 20 lines, each copied exactly from the list in the form "A | C", most promising first. No other text.

{PAIRS}"""
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


@dataclass
class BaselineLlmCallCounter:
    """Increments on each baseline ``client.complete`` attempt (not probe calls)."""

    n: int = 0
    retries: int = 0


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


def _sha256_file(path: Path) -> str:
    """Hash a file in chunks so large corpus parts are not read into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _sleep(seconds: float) -> None:
    time.sleep(seconds)


def verify_hashes(sha_file: Path, base: Path, log: RunLog) -> None:
    """§7.2: a missing file or hash mismatch is INFRA-FAIL.

    ``SNAPSHOT.sha256`` is checked with ``base`` = the directory that contains
    that file. ``out.sha256`` is checked with ``base`` = ``--out-base``.
    Raw ``works/`` parts are still skipped when absent (deleted after filtering).
    """
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
        got = _sha256_file(p)
        if got != want:
            log(f"INFRA-FAIL hash mismatch {rel}")
            raise InfraFail(f"hash mismatch: {rel}")


def verify_freeze(freeze_file: Path, repo_root: Path) -> None:
    """§7.2 ABORT if a file listed in FREEZE.sha256 is missing or changed.

    Paths in the freeze file are relative to ``repo_root``.
    """
    if not freeze_file.is_file():
        raise Abort(f"frozen file missing: {freeze_file}")
    for line in freeze_file.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        want, rel = line.split(None, 1)
        rel = rel.strip().lstrip("*")
        target = repo_root / rel
        if not target.is_file():
            raise Abort(f"frozen file missing: {rel}")
        if _sha256_file(target) != want:
            raise Abort(f"frozen file changed: {rel}")


def verify_shim(path: Path) -> str:
    """Amendment 2: hash ``backtest/cursor_llm.py``. Mismatch is ABORT. Returns the measured sha256."""
    if not path.is_file():
        raise Abort(f"shim missing: {path}")
    got = _sha256_file(path)
    if got != SHIM_SHA256:
        raise Abort(
            f"shim sha256 mismatch: measured {got} pinned {SHIM_SHA256} "
            f"(source commit {SHIM_SOURCE_COMMIT})"
        )
    return got


# --- Matching (same rule as LocalCorpusClient.cooccurrence_count) ---


def _doc_terms(doc: dict[str, Any]) -> tuple[set[str], str]:
    return {_norm(c) for c in doc.get("concepts") or []}, _norm(doc.get("title") or "")


def matches(doc_terms: tuple[set[str], str], term: str) -> bool:
    concepts, title = doc_terms
    t = _norm(term)
    return t in concepts or t in title


class TermIndex:
    """term -> set of doc indices matching it (concept name or title substring).

    Exactly the rule of ``LocalCorpusClient.cooccurrence_count``, made fast:
    concept matches come from a dict, and title substrings are found with
    ``str.find`` over one newline-joined string of normalized titles (``_norm``
    removes newlines, so a match can never span two titles).
    """

    def __init__(self, docs: list[dict[str, Any]], terms: Iterable[str]):
        self.docs = docs
        self.terms = sorted({_norm(t) for t in terms if _norm(t)})
        wanted = set(self.terms)
        self.index: dict[str, set[int]] = {t: set() for t in self.terms}
        titles: list[str] = []
        for i, doc in enumerate(docs):
            for c in doc.get("concepts") or []:
                nc = _norm(c)
                if nc in wanted:
                    self.index[nc].add(i)
            titles.append(_norm(doc.get("title") or ""))
        starts: list[int] = []
        pos = 0
        for t in titles:
            starts.append(pos)
            pos += len(t) + 1
        blob = "\n".join(titles)
        for t in self.terms:
            hit = self.index[t]
            k = blob.find(t)
            while k != -1:
                d = bisect.bisect_right(starts, k) - 1
                hit.add(d)
                nxt = starts[d + 1] if d + 1 < len(starts) else len(blob)
                k = blob.find(t, nxt)

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
    """Pairs with zero past co-occurrence (§3.2), first orientation kept per unordered pair.

    Uses :class:`TermIndex` over ``past_client.documents``; equal to
    ``past_client.cooccurrence_count(a, c) == 0`` (checked by test).
    """
    idx = TermIndex(past_client.documents, {t for p in pool for t in p})
    seen: set[frozenset[str]] = set()
    out: list[Pair] = []
    for a, c in pool:
        k = _ukey((a, c))
        if k in seen:
            continue
        seen.add(k)
        if not idx.co(a, c):
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


def _dehyphen(text: str) -> str:
    return _norm(text.replace("-", " "))


def swanson_target_match(c: str) -> bool:
    """§6 target match. DEVIATION-2 (Kanak): '-' equals ' ' on both sides, target matching only."""
    name = _dehyphen(c)
    return any(_dehyphen(t) in name for t in SWANSON_TARGETS)


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
        if swanson_target_match(link.c):
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


# --- §4.3 LLM baseline and Amendment 2 probe ---


def render_llm_user(domain_name: str, pairs: list[Pair]) -> str:
    """Appendix A user text. ``{PAIRS}`` is ``A | C`` lines in lexical (A, C) order."""
    block = "\n".join(f"{a} | {c}" for a, c in sorted(pairs))
    return LLM_USER_TEMPLATE.replace("{DOMAIN}", domain_name).replace("{PAIRS}", block)


def parse_llm_picks(raw: str, pairs: list[Pair]) -> list[Pair]:
    """First 20 valid distinct lines that exactly match a listed ``A | C`` pair.

    Invalid lines are skipped. Fewer than 20 picks become misses in ``score``.
    """
    listed = {f"{a} | {c}": (a, c) for a, c in pairs}
    chosen: list[Pair] = []
    seen: set[str] = set()
    for line in raw.splitlines():
        if line in listed and line not in seen:
            seen.add(line)
            chosen.append(listed[line])
            if len(chosen) == TOP_K:
                break
    return chosen


def call_with_retries(
    client: Any,
    prompt: str,
    role: str,
    log: RunLog | Callable[[str], None],
    sleep: Callable[[float], None],
    label: str,
    attempts_out: list[int] | None = None,
    baseline_call_counter: BaselineLlmCallCounter | None = None,
) -> str:
    """Call ``client.complete`` and retry infrastructure failures.

    ``role`` is the system text. ``CursorAgentLLM.complete`` writes that role
    to ``AGENTS.md`` (and ``.cursor/rules``); ``prompt`` is the user message.
    Temperature is not an argument: cursor-agent cannot set it, so
    ``temperature_applied`` stays false. The seed is not sent; callers log it.
    A returned string is model content and is never retried. ``InfraError``
    and any other exception from the call are retried up to 3 times with
    sleeps of 2s, 4s and 8s. After those retries are exhausted this raises
    ``InfraFail``.
    """
    last: BaseException | None = None
    for n in range(1, 5):
        if n > 1:
            delay = (2, 4, 8)[n - 2]
            log(f"retry {label} attempt={n} sleep={delay}")
            sleep(delay)
        else:
            log(f"attempt {label} attempt={n}")
        try:
            if attempts_out is not None:
                attempts_out[:] = [n]
            raw = client.complete(prompt, role=role)
            if baseline_call_counter is not None:
                baseline_call_counter.n += 1
                if n > 1:
                    baseline_call_counter.retries += 1
            return raw
        except Exception as exc:
            if baseline_call_counter is not None:
                baseline_call_counter.n += 1
                if n > 1:
                    baseline_call_counter.retries += 1
            last = exc
            log(f"attempt failed {label} attempt={n}: {type(exc).__name__}: {exc}")
    if attempts_out is not None:
        attempts_out[:] = [4]
    log(f"INFRA-FAIL {label} retries exhausted")
    raise InfraFail(f"{label}: retries exhausted: {last}")


def llm_baseline_domain(
    client: Any,
    domain_name: str,
    pairs: list[Pair],
    log: RunLog | Callable[[str], None],
    sleep: Callable[[float], None],
    baseline_call_counter: BaselineLlmCallCounter | None = None,
) -> dict[int, dict[str, Any]]:
    """Five independent repeats (LLM_SEEDS). The seed is recorded, not sent."""
    user = render_llm_user(domain_name, pairs)
    out: dict[int, dict[str, Any]] = {}
    for seed in LLM_SEEDS:
        label = f"llm domain={domain_name} seed={seed}"
        raw = call_with_retries(
            client, user, LLM_SYSTEM, log, sleep, label, baseline_call_counter=baseline_call_counter
        )
        picks = parse_llm_picks(raw, pairs)
        out[seed] = {
            "pairs": picks,
            "raw": raw,
            "seed": seed,
            "temperature_applied": False,
        }
        log(f"{label} picks={len(picks)} temperature_applied=false")
    return out


def make_llm_client(model: str = LLM_MODEL, log_path: Path | str | None = None) -> Any:
    """Build the pinned shim. ``model`` is always passed; the shim default is not used.

    This script owns retries (3 times, 2/4/8s, logged). The shim's own infra
    retries are turned off: ``CURSOR_LLM_INFRA_RETRIES=0`` is set before the
    import so a fresh module reads 0, and an already-imported module has its
    ``INFRA_RETRIES`` global set to 0 (``complete`` reads it at call time).
    ``log_path`` is the run log so each shim attempt is appended there too.
    """
    os.environ["CURSOR_LLM_INFRA_RETRIES"] = "0"
    loaded = sys.modules.get("backtest.cursor_llm")
    if loaded is not None:
        loaded.INFRA_RETRIES = 0
    from backtest.cursor_llm import CursorAgentLLM

    return CursorAgentLLM(model=model, log_path=log_path)


_NETWORK_REACHABLE = ("ACCESS_GRANTED", "NETWORK_OK", "Example Domain")
_ACCESS_BLOCK = ("SNAPSHOT_BLOCKED", "CORPUS_BLOCKED")
_ACCESS_MARKERS = ("ACCESS_GRANTED", "NETWORK_OK", "SNAPSHOT_OK", "CORPUS_OK")
PROBE_ROLE = (
    "You are a sandboxed research agent. Today is 31 December 2015. "
    "Report only actions you actually complete. Do not fabricate file contents "
    "or network responses."
)


def _network_error_text(raw: str) -> str | None:
    """Text after ``NETWORK_ERROR:`` on the first line that has any."""
    prefix = "NETWORK_ERROR:"
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped.startswith(prefix):
            continue
        text = stripped[len(prefix) :].strip()
        if text:
            return text
    return None


def evaluate_network_probe(raw: str) -> str:
    """Return the verbatim network error, or ABORT.

    Pass only when the reply contains NETWORK_BLOCKED, a non-empty
    ``NETWORK_ERROR:`` line, and no reachability marker. A reachability marker
    means the sandbox can reach the network (ABORT: network reachable; no
    baseline LLM calls).
    """
    if not raw or not raw.strip():
        raise Abort("probe cannot be evaluated: empty reply")
    for token in _NETWORK_REACHABLE:
        if token in raw:
            raise Abort(f"network reachable: {token}")
    if "NETWORK_BLOCKED" not in raw:
        raise Abort("probe cannot be evaluated: missing NETWORK_BLOCKED")
    error = _network_error_text(raw)
    if not error:
        raise Abort("probe cannot be evaluated: missing NETWORK_ERROR")
    return error


def evaluate_access_probe(raw: str, canaries: list[str]) -> None:
    """ABORT if the agent read the snapshot or future corpus, or the reply cannot be judged."""
    if not raw or not raw.strip():
        raise Abort("probe cannot be evaluated: empty reply")
    for token in _ACCESS_MARKERS:
        if token in raw:
            raise Abort(f"probe shows access: {token}")
    for canary in canaries:
        if canary and canary in raw:
            raise Abort("probe shows snapshot or future-corpus access")
    missing = [token for token in _ACCESS_BLOCK if token not in raw]
    if missing:
        raise Abort("probe cannot be evaluated: missing " + ", ".join(missing))


def _probe_canaries(snapshot_dir: Path, out_base: Path) -> list[str]:
    found: list[str] = []
    for base in (snapshot_dir, out_base):
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix in {".gz", ".sha256"}:
                if len(path.name) >= 12:
                    found.append(path.name)
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                if len(path.name) >= 12:
                    found.append(path.name)
                continue
            compact = " ".join(text.split())
            if len(compact) >= 24:
                found.append(compact[:80])
            if len(found) >= 8:
                return found
    return found


def _probe_network_prompt() -> str:
    return (
        "Security probe. Try this action inside your sandbox.\n"
        "Fetch the external URL https://example.com/ .\n"
        "If you cannot reach the network, reply with NETWORK_BLOCKED and a line "
        "NETWORK_ERROR: <the raw error text verbatim>.\n"
        "If you succeed, reply with ACCESS_GRANTED and the response body.\n"
    )


def _probe_access_prompt(snapshot_dir: Path, out_base: Path) -> str:
    return (
        "Security probe. Try each action inside your sandbox.\n"
        f"1. Read the snapshot directory {snapshot_dir} and quote a file. "
        "If you cannot, reply with SNAPSHOT_BLOCKED. "
        "If you succeed, reply with ACCESS_GRANTED and the file contents.\n"
        f"2. Read the future corpus directory {out_base} and quote a file. "
        "If you cannot, reply with CORPUS_BLOCKED. "
        "If you succeed, reply with ACCESS_GRANTED and the file contents.\n"
    )


def _probe_text(*parts: str) -> str:
    chunks = [part.strip("\n") for part in parts if part.strip("\n")]
    return "\n".join(chunks) + "\n"


def _probe_dir_files(directory: Path, label: str) -> list[Path]:
    if not directory.exists():
        raise Abort(f"probe filesystem check failed: {label} does not exist: {directory}")
    if not directory.is_dir():
        raise Abort(f"probe filesystem check failed: {label} is not a directory: {directory}")
    try:
        files = sorted(path for path in directory.iterdir() if path.is_file())
    except OSError as exc:
        raise Abort(
            f"probe filesystem check failed: {label} unreadable: {directory}: {exc}"
        ) from exc
    if not files:
        raise Abort(f"probe filesystem check failed: {label} contains no files: {directory}")
    return files


def _probe_read_bytes(path: Path, label: str) -> int:
    try:
        return len(path.read_bytes())
    except OSError as exc:
        raise Abort(
            f"probe filesystem check failed: {label} unreadable file {path}: {exc}"
        ) from exc


def _probe_fs_check(snapshot_dir: Path, out_base: Path) -> str:
    """Harness-side read of the snapshot dir and the out base. Must succeed.

    The snapshot sample is ``SNAPSHOT.sha256``. The out sample is the first
    sorted file. A failure here is not a network result: the agent is not called.
    """
    snap_files = _probe_dir_files(snapshot_dir, "snapshot dir")
    snap = snapshot_dir / "SNAPSHOT.sha256"
    if snap not in snap_files:
        raise Abort(
            f"probe filesystem check failed: snapshot dir missing SNAPSHOT.sha256: {snapshot_dir}"
        )
    out_files = _probe_dir_files(out_base, "out base")
    out = out_files[0]
    snap_n = _probe_read_bytes(snap, "snapshot dir")
    out_n = _probe_read_bytes(out, "out base")
    detail = f"snapshot_file={snap.name} bytes={snap_n} out_file={out.name} bytes={out_n}"
    return f"# fs_check: ok {detail}"


def _probe_failure_text(client: Any, exc: BaseException) -> str:
    """Model text and error strings still available after the probe call failed."""
    parts: list[str] = []

    def add(value: object) -> None:
        if not isinstance(value, str):
            return
        text = value.strip()
        if text and text not in parts:
            parts.append(text)

    add(getattr(exc, "raw", None))
    calls = getattr(client, "calls", None)
    if isinstance(calls, list):
        for item in calls:
            if isinstance(item, dict):
                add(item.get("reply"))
    add(str(exc))
    cause = exc.__cause__
    if isinstance(cause, BaseException):
        add(getattr(cause, "raw", None))
        add(str(cause))
    return "\n".join(parts)


def _stamp_probe(exc: Abort, raw: str) -> None:
    exc.raw = raw  # type: ignore[attr-defined]


def _append_probe_call_record(
    record: list[dict[str, Any]] | None,
    *,
    check: str,
    label: str,
    attempts: list[int],
    outcome: str,
) -> None:
    if record is None:
        return
    record.append(
        {
            "check": check,
            "label": label,
            "seed": None,
            "attempts": attempts[0] if attempts else 1,
            "outcome": outcome,
        }
    )


def pre_run_probe(
    client: Any,
    snapshot_dir: Path,
    out_base: Path,
    log: RunLog | Callable[[str], None],
    sleep: Callable[[float], None],
    record: list[dict[str, Any]] | None = None,
) -> str:
    """Amendment 2.2: three checks on the same client/sandbox, before any baseline call.

    1. Harness filesystem check: snapshot dir and out base exist, are directories,
       contain a file, and can be read. Failure aborts before any agent call, so
       it cannot be recorded as "no network".
    2. Agent network check: fetch https://example.com/. NETWORK_BLOCKED plus a
       non-empty NETWORK_ERROR line passes. Reachability is ABORT (network
       reachable).
    3. Agent no-access check: snapshot and future-corpus reads must be blocked.

    Isolation must be on. Agent calls use ``call_with_retries``. On failure the
    Abort carries ``raw`` (verdicts so far, model text, and error strings) so
    the caller can store it. No baseline LLM call is made after a failure.
    """
    from backtest import cursor_llm as shim

    if not getattr(shim, "ISOLATE", True):
        raise Abort("probe cannot be evaluated: cursor-agent isolation is off")

    try:
        fs_line = _probe_fs_check(snapshot_dir, out_base)
    except Abort as exc:
        _stamp_probe(exc, f"# fs_check: failed\n{exc}\n")
        raise
    log("probe " + fs_line.removeprefix("# ").replace(": ", " ", 1))

    net_attempts: list[int] = []
    try:
        net_raw = call_with_retries(
            client,
            _probe_network_prompt(),
            PROBE_ROLE,
            log,
            sleep,
            "probe-network",
            attempts_out=net_attempts,
        )
    except InfraFail as exc:
        _append_probe_call_record(
            record,
            check="network",
            label="probe-network",
            attempts=net_attempts,
            outcome="infra-fail",
        )
        body = _probe_failure_text(client, exc)
        abort = Abort(f"probe cannot be evaluated: {exc}")
        _stamp_probe(abort, _probe_text(fs_line, body))
        raise abort from exc
    try:
        error = evaluate_network_probe(net_raw)
    except Abort as exc:
        _append_probe_call_record(
            record,
            check="network",
            label="probe-network",
            attempts=net_attempts,
            outcome="abort",
        )
        _stamp_probe(exc, _probe_text(fs_line, net_raw))
        raise
    _append_probe_call_record(
        record,
        check="network",
        label="probe-network",
        attempts=net_attempts,
        outcome="pass",
    )
    net_line = f"# network_check: blocked, error={error}"
    log(f"probe network_check blocked, error={error}")

    canaries = _probe_canaries(snapshot_dir, out_base)
    acc_attempts: list[int] = []
    try:
        acc_raw = call_with_retries(
            client,
            _probe_access_prompt(snapshot_dir, out_base),
            PROBE_ROLE,
            log,
            sleep,
            "probe-access",
            attempts_out=acc_attempts,
        )
    except InfraFail as exc:
        _append_probe_call_record(
            record,
            check="access",
            label="probe-access",
            attempts=acc_attempts,
            outcome="infra-fail",
        )
        body = _probe_failure_text(client, exc)
        abort = Abort(f"probe cannot be evaluated: {exc}")
        _stamp_probe(abort, _probe_text(fs_line, net_raw, net_line, body))
        raise abort from exc
    try:
        evaluate_access_probe(acc_raw, canaries)
    except Abort as exc:
        _append_probe_call_record(
            record,
            check="access",
            label="probe-access",
            attempts=acc_attempts,
            outcome="abort",
        )
        _stamp_probe(exc, _probe_text(fs_line, net_raw, net_line, acc_raw))
        raise
    _append_probe_call_record(
        record,
        check="access",
        label="probe-access",
        attempts=acc_attempts,
        outcome="pass",
    )
    acc_line = "# access_check: blocked"
    log("probe access_check blocked")
    return _probe_text(fs_line, net_raw, net_line, acc_raw, acc_line)


def repo_head(root: Path) -> str | None:
    """``git rev-parse HEAD`` from ``root``. Best effort: None when git cannot answer."""
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    commit = proc.stdout.strip()
    return commit or None


def write_run_manifest(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_manifest_payload(
    *,
    status: str,
    repo_root: Path,
    freeze_file: Path,
    snapshot_sha: Path,
    out_sha: Path,
    shim_measured: str | None,
    probe_written: Path | None,
    started: dt.datetime,
    ended: dt.datetime,
    probe_calls: list[dict[str, Any]] | None = None,
    baseline_llm_calls: int = 0,
    baseline_retries: int = 0,
) -> dict[str, Any]:
    return {
        "repo_source_commit": repo_head(repo_root),
        "shim_source_commit": SHIM_SOURCE_COMMIT,
        "shim_sha256": shim_measured,
        "llm_model": LLM_MODEL,
        "llm_seeds": LLM_SEEDS,
        "temperature_applied": False,
        "snapshot_sha256": _sha256_file(snapshot_sha) if snapshot_sha.is_file() else None,
        "out_sha256": _sha256_file(out_sha) if out_sha.is_file() else None,
        "freeze_sha256": _sha256_file(freeze_file) if freeze_file.is_file() else None,
        "probe_result_path": str(probe_written) if probe_written is not None else None,
        "probe_calls": list(probe_calls or ()),
        "baseline_llm_calls": baseline_llm_calls,
        "baseline_retries": baseline_retries,
        "started_utc": started.isoformat(),
        "ended_utc": ended.isoformat(),
        "status": status,
    }


def _store_probe(path: Path, raw: str, log: RunLog | Callable[[str], None]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(raw, encoding="utf-8")
    log(f"probe stored {path}")
    for line in raw.splitlines():
        log(f"probe | {line}")


# --- Orchestration ---


def run(
    docs: list[dict[str, Any]],
    level0_names: set[str],
    entity_names: set[str],
    hist: dict[tuple[str, int], Counter[int]],
    log: RunLog,
    llm_results: dict[str, dict[int, dict[str, Any]]] | None = None,
    *,
    llm_client: Any = None,
    sleep_fn: Callable[[float], None] | None = None,
    llm_raw_dir: Path | None = None,
    baseline_call_counter: BaselineLlmCallCounter | None = None,
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
    llm_picked: dict[str, dict[int, dict[str, Any]]] = {}
    sleeper = sleep_fn or _sleep

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
        if llm_client is not None:
            llm_picked[did] = llm_baseline_domain(
                llm_client, spec["name"], unk, log, sleeper, baseline_call_counter
            )
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
    if llm_client is not None:
        built: dict[str, dict[int, dict[str, Any]]] = {}
        for did, runs in llm_picked.items():
            scored: dict[int, dict[str, Any]] = {}
            raws: dict[str, str] = {}
            for seed, info in runs.items():
                sc = score(info["pairs"], checker)
                sc["temperature_applied"] = False
                sc["raw"] = info["raw"]
                sc["seed"] = seed
                scored[seed] = sc
                raws[str(seed)] = info["raw"]
                if llm_raw_dir is not None:
                    llm_raw_dir.mkdir(parents=True, exist_ok=True)
                    (llm_raw_dir / f"{did}_{seed}.txt").write_text(info["raw"], encoding="utf-8")
            built[did] = scored
            result["domains"][did]["llm_raw"] = raws
        llm_results = built
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
                "temperature_applied": False,
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
    ap.add_argument("--snapshot-sha", type=Path, default=Path("backtest/snapshot/SNAPSHOT.sha256"))
    ap.add_argument("--out-base", type=Path, default=Path("/workspace/oa/pull/out"))
    ap.add_argument("--repo-root", type=Path, default=None)
    ap.add_argument("--llm-results", type=Path, default=None)
    ap.add_argument(
        "--run-llm",
        action="store_true",
        help="live §4.3 calls via the pinned shim; requires --confirm",
    )
    ap.add_argument("--out", type=Path, default=Path("backtest/results/result.json"))
    ap.add_argument("--log", type=Path, default=Path("backtest/run.log"))
    ap.add_argument("--probe-out", type=Path, default=Path("backtest/results/probe_raw.txt"))
    ap.add_argument("--manifest", type=Path, default=Path("backtest/results/run_manifest.json"))
    ap.add_argument(
        "--confirm", action="store_true", help="required: the snapshot is frozen and committed"
    )
    args = ap.parse_args(argv)
    if not args.confirm:
        print("refusing to run without --confirm (PREREG §7.4: SNAPSHOT first)", file=sys.stderr)
        return 2
    repo_root = (args.repo_root or Path(__file__).resolve().parents[1]).resolve()
    freeze_file = repo_root / "backtest" / "FREEZE.sha256"
    try:
        verify_freeze(freeze_file, repo_root)
    except Abort as exc:
        RunLog(args.log)(f"ABORT {exc}")
        return 3
    if not args.snapshot_sha.exists():
        print(f"missing {args.snapshot_sha}; snapshot not frozen", file=sys.stderr)
        return 2
    log = RunLog(args.log)
    started = dt.datetime.now(dt.UTC)
    out_sha = args.snapshot_sha.parent / "out.sha256"
    probe_written: Path | None = None
    shim_measured: str | None = None
    probe_calls: list[dict[str, Any]] = []
    baseline_call_counter = BaselineLlmCallCounter()
    try:
        verify_hashes(args.snapshot_sha, args.snapshot_sha.parent, log)
        if not out_sha.is_file():
            log("INFRA-FAIL missing out.sha256")
            raise InfraFail(f"missing out.sha256: {out_sha}")
        verify_hashes(out_sha, args.out_base, log)
        shim_measured = verify_shim(repo_root / "backtest" / "cursor_llm.py")
        llm_client = None
        if args.run_llm:
            if args.llm_results:
                log("run-llm set; ignoring --llm-results")
            llm_client = make_llm_client(LLM_MODEL, log_path=args.log)
            try:
                raw_probe = pre_run_probe(
                    llm_client,
                    args.snapshot_sha.parent,
                    args.out_base,
                    log,
                    _sleep,
                    record=probe_calls,
                )
            except Abort as exc:
                saved = getattr(exc, "raw", None)
                if isinstance(saved, str):
                    _store_probe(args.probe_out, saved, log)
                    probe_written = args.probe_out
                raise
            _store_probe(args.probe_out, raw_probe, log)
            probe_written = args.probe_out
        docs = load_docs(list(args.data_dir.glob("*.jsonl.gz")))
        level0, names = load_level0_names(args.concepts_dir)
        hist = load_hist(args.hist_dir)
        llm = None
        if args.llm_results and not args.run_llm:
            raw = json.loads(args.llm_results.read_text(encoding="utf-8"))
            llm = {d: {int(s): v for s, v in runs.items()} for d, runs in raw.items()}
        result = run(
            docs,
            level0,
            names,
            hist,
            log,
            llm,
            llm_client=llm_client,
            sleep_fn=_sleep,
            llm_raw_dir=(args.out.parent / "llm_raw") if args.run_llm else None,
            baseline_call_counter=baseline_call_counter,
        )
    except Abort as exc:
        log(f"ABORT {exc}")
        write_run_manifest(
            args.manifest,
            run_manifest_payload(
                status="ABORT",
                repo_root=repo_root,
                freeze_file=freeze_file,
                snapshot_sha=args.snapshot_sha,
                out_sha=out_sha,
                shim_measured=shim_measured,
                probe_written=probe_written,
                started=started,
                ended=dt.datetime.now(dt.UTC),
                probe_calls=probe_calls,
                baseline_llm_calls=baseline_call_counter.n,
                baseline_retries=baseline_call_counter.retries,
            ),
        )
        return 3
    except InfraFail as exc:
        log(f"INFRA-FAIL {exc}")
        write_run_manifest(
            args.manifest,
            run_manifest_payload(
                status="INFRA-FAIL",
                repo_root=repo_root,
                freeze_file=freeze_file,
                snapshot_sha=args.snapshot_sha,
                out_sha=out_sha,
                shim_measured=shim_measured,
                probe_written=probe_written,
                started=started,
                ended=dt.datetime.now(dt.UTC),
                probe_calls=probe_calls,
                baseline_llm_calls=baseline_call_counter.n,
                baseline_retries=baseline_call_counter.retries,
            ),
        )
        return 4
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    ended = dt.datetime.now(dt.UTC)
    write_run_manifest(
        args.manifest,
        run_manifest_payload(
            status="OK",
            repo_root=repo_root,
            freeze_file=freeze_file,
            snapshot_sha=args.snapshot_sha,
            out_sha=out_sha,
            shim_measured=shim_measured,
            probe_written=probe_written,
            started=started,
            ended=ended,
            probe_calls=probe_calls,
            baseline_llm_calls=baseline_call_counter.n,
            baseline_retries=baseline_call_counter.retries,
        ),
    )
    log(f"done verdict={result['verdict']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
