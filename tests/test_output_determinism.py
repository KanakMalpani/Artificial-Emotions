"""The same inputs must produce byte-identical output.

Flag lists were built with ``list(set(...))``, so their order followed
PYTHONHASHSEED and every process emitted different JSON for an identical run.
That breaks diffing two runs, caching, and any golden-output test. These tests
run the real entry points in subprocesses with *different* hash seeds, which is
the only way to catch a regression of that kind in-process tests would miss.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

from artificial_curiosity.models import CuriosityConfig
from artificial_curiosity.pipeline import CuriosityEngine
from artificial_curiosity.scoring import dedupe_flags

_SPARK = """
import contextlib, io, json
from artificial_curiosity.cli import main
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    main(["spark", "--domain", "ai", "--n", "3", "--json"])
print(json.dumps(json.loads(buf.getvalue())["unknowns"], sort_keys=True))
"""


def _run_with_hash_seed(code: str, seed: str) -> str:
    env = {**os.environ, "PYTHONHASHSEED": seed}
    proc = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    return proc.stdout.strip()


@pytest.mark.e2e
def test_spark_json_is_identical_under_different_hash_seeds():
    outputs = {_run_with_hash_seed(_SPARK, seed) for seed in ("0", "1", "12345")}
    assert len(outputs) == 1, "spark JSON changed with PYTHONHASHSEED"


def test_engine_flag_order_is_stable_across_repeated_runs():
    cfg = CuriosityConfig(domain="ai", use_llm=False, use_literature=False, n_return=3)
    first = [list(r.flags) for r in CuriosityEngine(cfg).run()]
    for _ in range(3):
        assert [list(r.flags) for r in CuriosityEngine(cfg).run()] == first


def test_flags_survive_a_json_round_trip_in_order():
    cfg = CuriosityConfig(domain="ai", use_llm=False, use_literature=False, n_return=2)
    results = CuriosityEngine(cfg).run_dict()
    reparsed = json.loads(json.dumps(results))
    assert [r["flags"] for r in reparsed] == [r["flags"] for r in results]


def test_dedupe_flags_preserves_first_seen_order():
    assert dedupe_flags(["b", "a"], "c") == ["b", "a", "c"]
    assert dedupe_flags(["b", "a", "b"], "a", "c") == ["b", "a", "c"]
    assert dedupe_flags([]) == []
    assert dedupe_flags([], "only") == ["only"]


def test_dedupe_flags_does_not_mutate_its_input():
    original = ["a", "b"]
    dedupe_flags(original, "c")
    assert original == ["a", "b"]
