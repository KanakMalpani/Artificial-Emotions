"""Stub-only tests for backtest/run_backtest.py on synthetic data. No network."""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import re
import shutil
import socket
import sys
import urllib.request
from collections import Counter
from pathlib import Path

import pytest
from backtest.cursor_llm import InfraError

from backtest import run_backtest as rb
from tests.backtest.conftest import NetworkBlocked

_REPO = Path(__file__).resolve().parents[2]


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


def test_fast_index_equals_cooccurrence_count():
    import random as _r

    rng = _r.Random(3)
    vocab = ["mof", "graphene", "fish oil", "oil", "amorphous", "heat", "urban heat island", "x y"]
    docs = []
    for i in range(400):
        cs = rng.sample(vocab, rng.randint(0, 3))
        title = " ".join(
            rng.choice(vocab + ["the", "of", "Amorphous MOFs"]) for _ in range(rng.randint(0, 6))
        )
        docs.append(_doc(i, 2010, [c.title() for c in cs], title=title))
    client = rb.LocalCorpusClient(documents=docs)
    idx = rb.TermIndex(docs, vocab)
    for a in vocab:
        for c in vocab:
            assert len(idx.co(a, c)) == client.cooccurrence_count(a, c), (a, c)


def test_swanson_target_ignores_hyphens():
    assert rb.swanson_target_match("Omega 3 fatty acid")
    assert rb.swanson_target_match("Omega-3 fatty acid")
    assert rb.swanson_target_match("Fish oil")
    assert rb.swanson_target_match("Fatty acids, omega 3")
    assert not rb.swanson_target_match("Blood viscosity")


def test_section_3_4_matching_keeps_hyphens():
    docs = [_doc(1, 2018, ["Omega 3 fatty acid", "A"], title="omega 3 study", seg="future")]
    client = rb.LocalCorpusClient(documents=docs)
    assert client.cooccurrence_count("omega-3", "A") == 0
    idx = rb.TermIndex(docs, ["omega-3", "omega 3", "A"])
    assert not idx.co("omega-3", "A") and idx.co("omega 3", "A")
    ch = rb.Checker(docs, ["omega-3", "A"], {})
    assert ch.check(("omega-3", "A"))["co_mentions"] == 0


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _freeze_repo(root: Path, text: str = "frozen\n") -> Path:
    doc = root / "backtest" / "PREREG.md"
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_text(text, encoding="utf-8")
    freeze = root / "backtest" / "FREEZE.sha256"
    freeze.write_text(f"{_sha256(doc)}  backtest/PREREG.md\n", encoding="utf-8")
    return freeze


def _install_shim(root: Path, *, match: bool) -> Path:
    dest = root / "backtest" / "cursor_llm.py"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if match:
        shutil.copyfile(_REPO / "backtest" / "cursor_llm.py", dest)
    else:
        dest.write_text("not-the-pinned-shim\n", encoding="utf-8")
    return dest


def _write_sha(path: Path, entries: list[tuple[str, str]]) -> None:
    path.write_text("".join(f"{digest}  {rel}\n" for digest, rel in entries), encoding="utf-8")


def _hash_fixtures(root: Path, out: Path) -> Path:
    """Tiny SNAPSHOT.sha256 + out.sha256 that match files on disk."""
    snap = root / "backtest" / "snapshot"
    snap.mkdir(parents=True, exist_ok=True)
    marker = snap / "marker.txt"
    marker.write_text("marker\n", encoding="utf-8")
    out.mkdir(parents=True, exist_ok=True)
    part = out / "part.jsonl.gz"
    part.write_bytes(b"part-bytes")
    _write_sha(snap / "out.sha256", [(_sha256(part), "part.jsonl.gz")])
    _write_sha(snap / "SNAPSHOT.sha256", [(_sha256(marker), "marker.txt")])
    return snap


def _appendix_a() -> tuple[str, str]:
    text = (_REPO / "backtest" / "PREREG.md").read_text(encoding="utf-8")
    section = text.split("## Appendix A: LLM prompt (exact text)", 1)[1]
    blocks: list[str] = []
    pos = 0
    while len(blocks) < 2:
        start = section.find("```", pos)
        end = section.find("```", start + 3)
        blocks.append(section[start + 3 : end])
        pos = end + 3

    def unfence(body: str) -> str:
        if body.startswith("\n"):
            body = body[1:]
        if body.endswith("\n"):
            body = body[:-1]
        return body

    return unfence(blocks[0]), unfence(blocks[1])


class _StubLLM:
    def __init__(self, reply="not a pair\n", exc: BaseException | None = None):
        self.reply = reply
        self.exc = exc
        self.calls: list[dict] = []

    def complete(self, prompt, role="default", temperature=None):
        self.calls.append({"prompt": prompt, "role": role, "temperature": temperature})
        if self.exc is not None:
            raise self.exc
        if callable(self.reply):
            return self.reply(len(self.calls), prompt, role)
        return self.reply


def _main_args(root: Path, tmp: Path, *flags: str) -> list[str]:
    snap = root / "backtest" / "snapshot" / "SNAPSHOT.sha256"
    return [
        "--confirm",
        "--repo-root",
        str(root),
        "--snapshot-sha",
        str(snap),
        "--out-base",
        str(tmp / "out"),
        "--data-dir",
        str(tmp / "out"),
        "--concepts-dir",
        str(tmp / "concepts"),
        "--hist-dir",
        str(tmp / "hist"),
        "--out",
        str(tmp / "result.json"),
        "--log",
        str(tmp / "run.log"),
        "--probe-out",
        str(tmp / "probe_raw.txt"),
        "--manifest",
        str(tmp / "run_manifest.json"),
        *flags,
    ]


def test_verify_hashes_streams_in_chunks(tmp_path, monkeypatch):
    target = tmp_path / "f"
    target.write_bytes(b"abc")
    digest = hashlib.sha256(b"abc").hexdigest()
    (tmp_path / "S.sha256").write_text(f"{digest}  f\n")

    def boom(self, *args, **kwargs):
        raise AssertionError("read_bytes")

    monkeypatch.setattr(Path, "read_bytes", boom)
    rb.verify_hashes(tmp_path / "S.sha256", tmp_path, lambda _msg: None)


def test_default_snapshot_sha_path(tmp_path, monkeypatch, capsys):
    root = tmp_path / "repo"
    _freeze_repo(root)
    monkeypatch.chdir(tmp_path)
    code = rb.main(["--confirm", "--repo-root", str(root), "--log", str(tmp_path / "run.log")])
    err = capsys.readouterr().err
    assert code == 2
    assert "backtest/snapshot/SNAPSHOT.sha256" in err


def test_snapshot_sha256_mismatch_is_infra_fail(tmp_path):
    root = tmp_path / "repo"
    _freeze_repo(root)
    out = tmp_path / "out"
    snap = _hash_fixtures(root, out)
    _write_sha(snap / "SNAPSHOT.sha256", [("0" * 64, "marker.txt")])
    code = rb.main(_main_args(root, tmp_path))
    log = (tmp_path / "run.log").read_text(encoding="utf-8")
    assert code == 4
    assert "INFRA-FAIL" in log and "hash mismatch" in log


def test_out_sha256_mismatch_is_infra_fail(tmp_path):
    root = tmp_path / "repo"
    _freeze_repo(root)
    out = tmp_path / "out"
    snap = _hash_fixtures(root, out)
    _write_sha(snap / "out.sha256", [("0" * 64, "part.jsonl.gz")])
    code = rb.main(_main_args(root, tmp_path))
    log = (tmp_path / "run.log").read_text(encoding="utf-8")
    assert code == 4
    assert "INFRA-FAIL" in log and "part.jsonl.gz" in log and "hash mismatch" in log


def test_changed_frozen_file_aborts(tmp_path):
    root = tmp_path / "repo"
    freeze = _freeze_repo(root, text="original\n")
    (root / "backtest" / "PREREG.md").write_text("changed\n", encoding="utf-8")
    log = tmp_path / "run.log"
    code = rb.main(
        [
            "--confirm",
            "--repo-root",
            str(root),
            "--log",
            str(log),
            "--snapshot-sha",
            str(tmp_path / "nope"),
        ]
    )
    text = log.read_text(encoding="utf-8")
    assert code == 3 and "ABORT" in text and "changed" in text

    missing = root / "backtest" / "DEVIATION.md"
    assert not missing.exists()
    changed = root / "backtest" / "PREREG.md"
    freeze.write_text(
        f"{_sha256(changed)}  backtest/PREREG.md\n{'ab' * 32}  backtest/DEVIATION.md\n",
        encoding="utf-8",
    )
    code = rb.main(
        [
            "--confirm",
            "--repo-root",
            str(root),
            "--log",
            str(log),
            "--snapshot-sha",
            str(tmp_path / "nope"),
        ]
    )
    assert code == 3 and "missing" in log.read_text(encoding="utf-8")


def test_shim_sha_mismatch_aborts(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    _freeze_repo(root)
    _hash_fixtures(root, tmp_path / "out")
    _install_shim(root, match=False)
    probe_called = False
    llm_called = False

    def factory(model=None, log_path=None):
        nonlocal llm_called
        llm_called = True
        raise AssertionError("LLM factory called")

    def probe(*_args, **_kwargs):
        nonlocal probe_called
        probe_called = True
        raise AssertionError("probe called")

    monkeypatch.setattr(rb, "make_llm_client", factory)
    monkeypatch.setattr(rb, "pre_run_probe", probe)
    code = rb.main(_main_args(root, tmp_path, "--run-llm"))
    assert code == 3
    assert not probe_called and not llm_called
    assert "ABORT" in (tmp_path / "run.log").read_text(encoding="utf-8")


def test_probe_failure_aborts_with_zero_llm_calls(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    _freeze_repo(root)
    _hash_fixtures(root, tmp_path / "out")
    _install_shim(root, match=True)
    stub = _StubLLM()

    def factory(model=None, log_path=None):
        assert model == rb.LLM_MODEL
        assert log_path == tmp_path / "run.log"
        return stub

    def probe(client, snapshot_dir, out_base, log, sleep):
        assert client is stub
        raise rb.Abort("probe shows network access")

    monkeypatch.setattr(rb, "make_llm_client", factory)
    monkeypatch.setattr(rb, "pre_run_probe", probe)
    code = rb.main(_main_args(root, tmp_path, "--run-llm"))
    assert code == 3
    assert stub.calls == []
    assert "ABORT" in (tmp_path / "run.log").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("reply", "exc", "needle"),
    [
        ("I tried nothing", None, "I tried nothing"),
        (None, InfraError("cursor-agent exited 1 with no output"), "retries exhausted"),
    ],
)
def test_probe_failure_writes_raw_file(tmp_path, monkeypatch, reply, exc, needle):
    root = tmp_path / "repo"
    _freeze_repo(root)
    _hash_fixtures(root, tmp_path / "out")
    _install_shim(root, match=True)
    stub = _StubLLM(reply=reply or "", exc=exc)

    def factory(model=None, log_path=None):
        assert log_path == tmp_path / "run.log"
        return stub

    monkeypatch.setattr(rb, "make_llm_client", factory)
    monkeypatch.setattr(rb, "_sleep", lambda _seconds: None)
    code = rb.main(_main_args(root, tmp_path, "--run-llm"))
    assert code == 3
    assert len(stub.calls) == (4 if exc is not None else 1)
    raw_path = tmp_path / "probe_raw.txt"
    assert raw_path.is_file()
    body = raw_path.read_text(encoding="utf-8")
    assert needle in body
    assert "local_network_fetch=not_attempted" in body
    log = (tmp_path / "run.log").read_text(encoding="utf-8")
    assert "probe stored" in log
    assert needle in log
    assert "ABORT" in log
    assert not (tmp_path / "result.json").exists()


def test_make_llm_client_zero_inner_retries_and_log_path(tmp_path, monkeypatch):
    import backtest.cursor_llm as shim

    sandbox = tmp_path / "sandbox"
    monkeypatch.setattr(shim, "SANDBOX", sandbox)
    monkeypatch.setattr(shim, "INFRA_RETRIES", 2)
    monkeypatch.setenv("CURSOR_LLM_INFRA_RETRIES", "2")
    monkeypatch.setenv("CURSOR_LLM_SANDBOX", str(sandbox))
    log_path = tmp_path / "run.log"

    client = rb.make_llm_client(rb.LLM_MODEL, log_path=log_path)
    assert os.environ["CURSOR_LLM_INFRA_RETRIES"] == "0"
    assert shim.INFRA_RETRIES == 0
    assert client.model == rb.LLM_MODEL
    assert client.log_path == log_path

    monkeypatch.setenv("CURSOR_LLM_INFRA_RETRIES", "7")
    saved = sys.modules.pop("backtest.cursor_llm")
    try:
        fresh = rb.make_llm_client(log_path=log_path)
        loaded = sys.modules["backtest.cursor_llm"]
        assert loaded is not saved
        assert loaded.INFRA_RETRIES == 0
        assert fresh.log_path == log_path
        assert os.environ["CURSOR_LLM_INFRA_RETRIES"] == "0"
    finally:
        sys.modules["backtest.cursor_llm"] = saved
        import backtest

        backtest.cursor_llm = saved


def test_llm_retry_backoff_then_infra_fail(tmp_path):
    sleeps: list[float] = []
    calls = {"n": 0}

    class Boom:
        def complete(self, prompt, role="default", temperature=None):
            calls["n"] += 1
            raise InfraError("cursor-agent down")

    log_path = tmp_path / "run.log"
    with pytest.raises(rb.InfraFail):
        rb.call_with_retries(
            Boom(),
            "prompt",
            rb.LLM_SYSTEM,
            rb.RunLog(log_path),
            sleeps.append,
            "llm seed=101",
        )
    assert sleeps == [2, 4, 8]
    assert calls["n"] == 4
    text = log_path.read_text(encoding="utf-8")
    assert "INFRA-FAIL" in text
    for line in text.splitlines():
        assert re.match(r"\d{4}-\d{2}-\d{2}T", line)
    assert "sleep=2" in text and "sleep=4" in text and "sleep=8" in text


def test_llm_model_content_is_not_retried(tmp_path):
    stub = _StubLLM(reply="garbage line\n")
    slept = False

    def sleep(_seconds):
        nonlocal slept
        slept = True

    out = rb.call_with_retries(
        stub, "prompt", rb.LLM_SYSTEM, lambda _m: None, sleep, "llm seed=101"
    )
    assert out == "garbage line\n"
    assert len(stub.calls) == 1 and not slept
    assert stub.calls[0]["temperature"] is None


def test_llm_prompt_byte_equal_to_appendix_a():
    system, user = _appendix_a()
    assert rb.LLM_SYSTEM == system
    assert rb.LLM_USER_TEMPLATE == user
    rendered = rb.render_llm_user("Aging biology", [("B", "A"), ("A", "C"), ("A", "B")])
    expect = user.replace("{DOMAIN}", "Aging biology").replace("{PAIRS}", "A | B\nA | C\nB | A")
    assert rendered == expect
    assert rb.SHIM_SOURCE_COMMIT == "8b1bfc1"
    assert rb.SHIM_SHA256 == "1ea827efb925ac251ae93fd082b7257143056521685c4e89b936058ac1c9c999"
    assert rb.LLM_MODEL == "grok-4.7-high"


def test_llm_baseline_median_of_five():
    pairs = [(f"A{i:02d}", f"C{i:02d}") for i in range(25)]
    ordered = sorted(pairs)
    plans = {
        1: ordered[:0],
        2: ordered[:4],
        3: ordered[:10],
        4: ordered[:10],
        5: ordered[:2],
    }

    def reply(n, prompt, role):
        assert role == rb.LLM_SYSTEM
        assert prompt == rb.render_llm_user("Aging biology", pairs)
        for seed in rb.LLM_SEEDS:
            assert str(seed) not in prompt
        chosen = plans[n]
        lines = [f"{a} | {c}" for a, c in chosen]
        junk = "NOT A PAIR\n"
        if lines:
            junk += lines[0] + "\n"
        return junk + "\n".join(lines)

    stub = _StubLLM(reply=reply)
    runs = rb.llm_baseline_domain(
        stub, "Aging biology", pairs, log=lambda _m: None, sleep=lambda _s: None
    )
    assert list(runs) == rb.LLM_SEEDS
    assert all(info["temperature_applied"] is False for info in runs.values())
    fut = []
    i = 0
    for a, c in ordered[:10]:
        for _k in range(5):
            i += 1
            fut.append(_doc(i, 2018, [a, c], seg="future", cnp=0.99))
    checker = rb.Checker(fut, [t for pair in pairs for t in pair], {})
    scored = {seed: rb.score(info["pairs"], checker) for seed, info in runs.items()}
    assert scored[102]["returned"] == 4 and scored[102]["hit_rate"] == pytest.approx(0.2)
    assert rb.llm_median(scored)[0] == 102
    assert len(stub.calls) == 5


def test_toy_run_through_main_with_stub_llm_and_probe(tmp_path, monkeypatch):
    monkeypatch.setattr(rb, "N_PERM", 30)
    monkeypatch.setattr(rb, "MIN_UNKNOWNS", 10)
    root = tmp_path / "repo"
    freeze = _freeze_repo(root)
    out = tmp_path / "out"
    snap = _hash_fixtures(root, out)
    corpus = out / "corpus.jsonl.gz"
    with gzip.open(corpus, "wt", encoding="utf-8") as fh:
        for doc in _synthetic_corpus():
            fh.write(json.dumps(doc) + "\n")
    (out / "part.jsonl.gz").unlink()
    _write_sha(snap / "out.sha256", [(_sha256(corpus), "corpus.jsonl.gz")])
    concepts = tmp_path / "concepts"
    concepts.mkdir()
    names = [s for spec in rb.DOMAINS.values() for s in spec["seeds"]]
    names.append("Raynaud's phenomenon")
    with gzip.open(concepts / "concepts.jsonl.gz", "wt", encoding="utf-8") as fh:
        for name in names:
            fh.write(json.dumps({"display_name": name, "level": 1}) + "\n")
    (tmp_path / "hist").mkdir()
    _install_shim(root, match=True)
    stub = _StubLLM(reply="not a pair\n")
    seen = {}

    def factory(model=None, log_path=None):
        seen["model"] = model
        seen["log_path"] = log_path
        return stub

    def probe(client, snapshot_dir, out_base, log, sleep):
        assert client is stub
        return "NETWORK_BLOCKED\nSNAPSHOT_BLOCKED\nCORPUS_BLOCKED\n"

    monkeypatch.setattr(rb, "make_llm_client", factory)
    monkeypatch.setattr(rb, "pre_run_probe", probe)
    code = rb.main(_main_args(root, tmp_path, "--run-llm"))
    assert code == 0, (tmp_path / "run.log").read_text(encoding="utf-8")
    assert seen["model"] == rb.LLM_MODEL
    assert seen["log_path"] == tmp_path / "run.log"
    assert len(stub.calls) == len(rb.DOMAINS) * len(rb.LLM_SEEDS)
    assert all(call["role"] == rb.LLM_SYSTEM for call in stub.calls)
    assert all(call["temperature"] is None for call in stub.calls)
    result = json.loads((tmp_path / "result.json").read_text(encoding="utf-8"))
    assert result["verdict"] in {"PASS", "FAIL"}
    for did in rb.DOMAINS:
        raws = result["domains"][did]["llm_raw"]
        assert set(raws) == {str(s) for s in rb.LLM_SEEDS}
        assert result["domains"][did]["comparisons"]["llm"]["temperature_applied"] is False
        for seed in rb.LLM_SEEDS:
            stored = tmp_path / "llm_raw" / f"{did}_{seed}.txt"
            assert stored.read_text(encoding="utf-8") == "not a pair\n"
    probe_path = tmp_path / "probe_raw.txt"
    assert "NETWORK_BLOCKED" in probe_path.read_text(encoding="utf-8")
    assert "probe" in (tmp_path / "run.log").read_text(encoding="utf-8")
    manifest = json.loads((tmp_path / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["shim_source_commit"] == rb.SHIM_SOURCE_COMMIT
    assert manifest["shim_sha256"] == rb.SHIM_SHA256
    assert manifest["shim_sha256"] == _sha256(root / "backtest" / "cursor_llm.py")
    assert manifest["llm_model"] == rb.LLM_MODEL
    assert manifest["llm_seeds"] == rb.LLM_SEEDS
    assert manifest["temperature_applied"] is False
    assert manifest["probe_result_path"] == str(probe_path)
    assert manifest["snapshot_sha256"] == _sha256(snap / "SNAPSHOT.sha256")
    assert manifest["out_sha256"] == _sha256(snap / "out.sha256")
    assert manifest["freeze_sha256"] == _sha256(freeze)
    assert manifest["repo_source_commit"] is None or re.fullmatch(
        r"[0-9a-f]{7,40}", manifest["repo_source_commit"] or ""
    )
    assert manifest["started_utc"] <= manifest["ended_utc"]
    assert manifest["started_utc"].endswith("+00:00")


def test_evaluate_probe_rejects_access_and_unevaluable():
    ok = "NETWORK_BLOCKED\nSNAPSHOT_BLOCKED\nCORPUS_BLOCKED\n"
    rb.evaluate_probe(ok, ["CANARY-TEXT-12345678901234567890"])
    with pytest.raises(rb.Abort, match="access"):
        rb.evaluate_probe(ok + "ACCESS_GRANTED\n", [])
    with pytest.raises(rb.Abort, match="access"):
        rb.evaluate_probe(
            ok + "CANARY-TEXT-12345678901234567890", ["CANARY-TEXT-12345678901234567890"]
        )
    with pytest.raises(rb.Abort, match="evaluated"):
        rb.evaluate_probe("I tried nothing", [])
    with pytest.raises(rb.Abort, match="evaluated"):
        rb.evaluate_probe("", [])
