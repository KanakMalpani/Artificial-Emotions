"""Stub-only tests for backtest/run_backtest.py on synthetic data. No network."""

from __future__ import annotations

import gzip
import json
import socket
import urllib.request
from collections import Counter

import pytest

from backtest import run_backtest as rb
from tests.backtest.conftest import NetworkBlocked


def test_socket_is_blocked():
    with pytest.raises(NetworkBlocked):
        socket.socket()
    with pytest.raises(NetworkBlocked):
        socket.create_connection(("example.com", 80))
    with pytest.raises(NetworkBlocked):
        urllib.request.urlopen("http://example.com", timeout=1)


def _doc(i, year, concepts, title="", seg="past", domains=("D1",), **kw):
    d = {
        "id": f"W{i}",
        "year": year,
        "title": title,
        "concepts": list(concepts),
        "seg": seg,
        "domains": list(domains),
        "swanson": False,
    }
    d.update(kw)
    return d


def test_frozen_constants_match_prereg():
    assert rb.RANDOM_SEEDS == list(range(100))
    assert rb.LLM_SEEDS == [101, 102, 103, 104, 105]
    assert rb.PERM_SEED == 20151231
    assert (rb.TOP_K, rb.POOL_SIZE, rb.PURSUED_MIN, rb.MAX_LINKS, rb.N_PERM) == (
        20,
        300,
        5,
        1000,
        10_000,
    )
    assert (rb.MARGIN, rb.P_THRESHOLD, rb.HIGH_CITE_PCT, rb.SWANSON_K) == (0.10, 0.05, 0.90, 20)
    assert rb.DOMAINS["D1"]["seeds"][3] == "Calorie restriction"  # Deviation 1


def test_load_docs_sorted_by_work_id(tmp_path):
    p = tmp_path / "a.jsonl.gz"
    with gzip.open(p, "wt") as fh:
        for i in (30, 4, 200):
            fh.write(json.dumps(_doc(i, 2010, ["X"])) + "\n")
    assert [d["id"] for d in rb.load_docs([p])] == ["W4", "W30", "W200"]


def test_pool_excludes_seed_stop_and_level0():
    docs = [_doc(i, 2010, ["Alpha", "Biology", "Medicine", f"C{i % 3}"]) for i in range(9)]
    pool = rb.candidate_pool(docs, ["Alpha"], level0_names={"medicine"})
    cs = {c for _, c in pool}
    assert cs == {"C0", "C1", "C2"}  # Alpha=seed, Biology=stop concept, Medicine=level-0


def test_unknowns_require_zero_past_cooccurrence_and_dedupe_unordered():
    docs = [_doc(1, 2010, ["A", "C1"]), _doc(2, 2010, ["C2"]), _doc(3, 2010, ["B"])]
    client = rb.LocalCorpusClient(documents=docs)
    pool = [("A", "C1"), ("A", "C2"), ("B", "A"), ("A", "B")]
    assert rb.unknowns(pool, client) == [("A", "C2"), ("B", "A")]


def test_random_sorts_before_sampling():
    unk = [(f"A{i}", f"C{i}") for i in range(50)]
    shuffled = list(reversed(unk))
    assert rb.random_top(unk, 7) == rb.random_top(shuffled, 7)
    assert len(rb.random_top(unk, 7)) == 20
    assert rb.random_top(unk, 7) != rb.random_top(unk, 8)


def test_citation_trend_formula_and_ties():
    docs = (
        [_doc(i, 2015, ["Hot"]) for i in range(9)]
        + [_doc(100, 2013, ["Hot"])]
        + [_doc(200 + i, 2013, ["Cold"]) for i in range(3)]
        + [_doc(300, 2014, ["Hot"])] * 50  # outside the 2013/2015 window: ignored
    )
    unk = [("A", "Cold"), ("A", "Hot"), ("A", "Flat"), ("B", "Flat")]
    top = rb.citation_trend_top(unk, docs)
    # growth(Hot)=(9+1)/(1+1)=5; Flat=1; Cold=(0+1)/(3+1)=0.25; A,B have growth 1.
    assert top == [("A", "Hot"), ("A", "Flat"), ("B", "Flat"), ("A", "Cold")]


def test_engine_merge_keeps_max_gap_and_tiebreaks(monkeypatch):
    L = rb.discover_links.__globals__["ABCLink"]

    def fake(a, client, max_links):
        assert max_links == 1000
        g = {
            "S1": [("S1", "X", 0.5), ("S1", "Y", 0.2)],
            "S2": [("S2", "X", 0.9), ("S2", "Z", 0.5), ("S2", "S1", 0.4)],
        }[a]
        return [
            L(a=x, b="B", c=c, bridge_strength=1, c_strength=1, cooccurrence=0, gap=v)
            for x, c, v in g
        ]

    monkeypatch.setattr(rb, "discover_links", fake)
    unk = [("S1", "X"), ("S1", "Y"), ("S2", "X"), ("S2", "Z"), ("S1", "S2")]
    top = rb.engine_top(["S1", "S2"], past_client=None, unknown_set=unk)
    # (S2,X)=0.9; (S1,X)=0.5 ties (S2,Z)=0.5 -> seed order S1 first; (S2,S1) is unordered dup of (S1,S2)
    assert top == [("S2", "X"), ("S1", "X"), ("S2", "Z"), ("S1", "S2"), ("S1", "Y")]


def test_checker_pursued_highly_cited_and_fallback():
    fut = [_doc(i, 2018, ["A", "C"], seg="future", cnp=0.5) for i in range(5)]
    fut += [_doc(10, 2019, ["A"], title="study of d", seg="future", cnp=0.95)]
    fut += [_doc(11, 2020, ["A", "E"], seg="future", field="f1", cited_by_count=50)]
    fut += [_doc(12, 2030, ["A", "G"], seg="future", cnp=0.99)]  # outside window
    hist = {("f1", 2020): Counter({0: 9, 50: 1})}
    ch = rb.Checker(fut, ["A", "C", "D", "E", "G"], rb.p90_thresholds(hist))
    assert ch.check(("A", "C"))["pursued"] and not ch.check(("A", "C"))["highly_cited"]
    r = ch.check(("A", "D"))  # title substring match
    assert r["highly_cited"] and not r["pursued"] and r["hit"]
    assert ch.check(("A", "E"))["highly_cited"]  # fallback: p90 of [0]*9+[50] = 0 -> 50 >= 0
    assert not ch.check(("A", "G"))["hit"]
    assert ch.judged_fallback >= 1


def test_p90_nearest_rank():
    assert rb.p90_thresholds({("f", 2016): Counter(range(1, 11))}) == {("f", 2016): 9}


def test_score_counts_missing_slots_as_misses():
    fut = [_doc(i, 2018, ["A", "C"], seg="future", cnp=0.95) for i in range(1)]
    ch = rb.Checker(fut, ["A", "C"], {})
    s = rb.score([("A", "C")], ch)
    assert s["returned"] == 1 and s["hit_rate"] == 1 / 20 and len(s["labels"]) == 20


def test_stats():
    assert rb.p_vs_random(0.5, [0.1] * 100) == pytest.approx(1 / 101)
    assert rb.p_vs_random(0.1, [0.1] * 100) == 1.0
    eng, oth = [True] * 12 + [False] * 8, [False] * 20
    p = rb.permutation_p(eng, oth)
    assert p < 0.05 and p == rb.permutation_p(eng, oth)  # deterministic with PERM_SEED
    assert rb.permutation_p([True] * 2 + [False] * 18, [True] * 2 + [False] * 18) > 0.05
    assert rb.beats(0.10, 0.01) and not rb.beats(0.05, 0.001) and not rb.beats(0.2, 0.05)


def test_llm_median_tie_lowest_seed():
    runs = {s: {"hit_rate": r} for s, r in zip(rb.LLM_SEEDS, [0.3, 0.1, 0.2, 0.2, 0.4])}
    assert rb.llm_median(runs)[0] == 103


def test_swanson_toy_corpus_rediscovers_fish_oil():
    sw = [
        _doc(1, 1979, ["Fish oil", "Blood viscosity"]),
        _doc(2, 1982, ["Fish oil", "Erythrocyte deformability"]),
        _doc(3, 1976, ["Blood viscosity", "Raynaud disease"]),
        _doc(4, 1980, ["Erythrocyte deformability", "Raynaud disease"]),
        _doc(5, 1978, ["Blood viscosity", "Vasospasm", "Raynaud disease"]),
    ]
    out = rb.swanson(sw, entity_names={"raynaud disease", "raynaud's disease"})
    assert out["start"] == "raynaud disease"  # most docs among names containing "raynaud"
    assert out["pass"] and out["target_c"] == "Fish oil" and out["target_rank"] <= 20


def _synthetic_corpus():
    docs, i = [], 0
    seeds = {d: s["seeds"] for d, s in rb.DOMAINS.items()}
    for did, ss in seeds.items():
        others = [f"{did} topic {k}" for k in range(30)]
        for n in range(1100):
            i += 1
            a = ss[n % 5]
            c = others[n % 30]
            b = others[(n * 7) % 30]
            concepts = [a, b] if n % 3 else [c, b]
            docs.append(_doc(i, 2005 + n % 11, concepts, domains=(did,)))
        for n in range(200):
            i += 1
            docs.append(
                _doc(
                    i,
                    2016 + n % 9,
                    [ss[n % 5], others[(n + 1) % 30]],
                    seg="future",
                    domains=(did,),
                    cnp=0.95 if n % 4 == 0 else 0.1,
                )
            )
    docs.append(_doc(i + 1, 1980, ["Fish oil", "Blood viscosity"], domains=(), swanson=True))
    docs.append(
        _doc(i + 2, 1980, ["Blood viscosity", "Raynaud's phenomenon"], domains=(), swanson=True)
    )
    return docs


def test_full_pipeline_on_toy_corpus(monkeypatch):
    monkeypatch.setattr(rb, "N_PERM", 200)
    monkeypatch.setattr(rb, "MIN_UNKNOWNS", 10)
    docs = _synthetic_corpus()
    names = {rb._norm(s) for d in rb.DOMAINS.values() for s in d["seeds"]} | {
        "raynaud's phenomenon"
    }
    logs = []
    res = rb.run(docs, level0_names=set(), entity_names=names, hist={}, log=logs.append)
    assert res["verdict"] == "INCOMPLETE (LLM baseline held)"
    assert res["verdict_without_llm"] in {"PASS", "FAIL"}
    for d in rb.DOMAINS:
        r = res["domains"][d]
        assert len(r["random"]["hit_rates"]) == 100
        assert set(r["comparisons"]) == {"random", "citation_trend", "llm"}
        assert r["engine"]["returned"] <= 20


def test_abort_on_small_corpus_and_unresolved_seed():
    with pytest.raises(rb.Abort):
        rb.run([], level0_names=set(), entity_names=set(), hist={}, log=print)
    names = {rb._norm(s) for d in rb.DOMAINS.values() for s in d["seeds"]}
    with pytest.raises(rb.Abort, match="past corpus"):
        rb.run([], level0_names=set(), entity_names=names, hist={}, log=print)


def test_main_refuses_without_confirm(tmp_path):
    assert rb.main(["--out", str(tmp_path / "r.json")]) == 2
    assert rb.main(["--confirm", "--snapshot-sha", str(tmp_path / "missing")]) == 2


def test_verify_hashes_mismatch_is_infra_fail(tmp_path):
    (tmp_path / "f").write_text("x")
    (tmp_path / "S.sha256").write_text("0" * 64 + "  f\n")
    with pytest.raises(rb.InfraFail):
        rb.verify_hashes(tmp_path / "S.sha256", tmp_path, print)


def test_verify_hashes_missing_derived_file_is_infra_fail_but_raw_part_is_skipped(tmp_path):
    (tmp_path / "S.sha256").write_text("0" * 64 + "  works/part_0000.gz\n")
    rb.verify_hashes(tmp_path / "S.sha256", tmp_path, print)
    (tmp_path / "S.sha256").write_text("0" * 64 + "  out/x.jsonl.gz\n")
    with pytest.raises(rb.InfraFail):
        rb.verify_hashes(tmp_path / "S.sha256", tmp_path, print)
