"""CONTRIBUTING pack lint (`emotions pack check`) — operationalization + why_it_matters."""

from __future__ import annotations

import json
from pathlib import Path

from artificial_emotions.cli import main
from artificial_emotions.packs import (
    check_pack_data,
    check_packs,
    questions_from_pack,
)

_GOOD_Q = {
    "id": "lint-ok-01",
    "question": "Which biomarkers predict remaining healthspan under caloric restriction?",
    "operationalization": (
        "Rank candidates by held-out AUROC ≥ 0.7 for remaining healthspan "
        "across ≥2 intervention classes with pre-registered endpoints."
    ),
    "why_it_matters": (
        "Longevity trials need transferable interim endpoints shorter than full lifespan."
    ),
    "tags": ["aging", "biomarkers"],
}


def _pack(*questions: dict, **meta: object) -> dict:
    body: dict = {
        "schema_version": "domain_pack.v1",
        "name": "lint_fixture",
        "domain": "biology",
        "questions": list(questions),
    }
    body.update(meta)
    return body


def test_bundled_packs_pass_contributing_bar():
    report = check_packs()
    assert report["ok"] is True
    assert report["n_errors"] == 0
    assert report["n_packs"] >= 6
    assert report["n_questions"] >= 6
    ids = {q_id for pack in report["packs"] for q_id in pack.get("question_ids") or []}
    assert "align-pack-01" in ids
    assert "clim-pack-01" in ids
    assert "affect-pack-01" in ids
    assert "aging-pack-01" in ids
    assert "matcat-pack-01" in ids
    honesty = str(report.get("honesty") or "").lower()
    assert "contributing" in honesty
    assert "operationalization" in honesty
    assert "why_it_matters" in honesty or "why it matters" in honesty


def test_missing_operationalization_fails():
    raw = dict(_GOOD_Q)
    raw.pop("operationalization")
    result = check_pack_data(_pack(raw))
    assert result["ok"] is False
    codes = {i["code"] for i in result["issues"]}
    assert "missing_operationalization" in codes


def test_short_operationalization_fails():
    raw = dict(_GOOD_Q, operationalization="too short")
    result = check_pack_data(_pack(raw))
    assert result["ok"] is False
    codes = {i["code"] for i in result["issues"]}
    assert "operationalization_too_short" in codes


def test_missing_why_it_matters_fails():
    raw = dict(_GOOD_Q)
    raw.pop("why_it_matters")
    result = check_pack_data(_pack(raw))
    assert result["ok"] is False
    codes = {i["code"] for i in result["issues"]}
    assert "missing_why_it_matters" in codes


def test_placeholder_why_it_matters_fails():
    for why in ("Pack-provided unknown.", "sounds interesting", "TBD", "…"):
        raw = dict(_GOOD_Q, why_it_matters=why)
        result = check_pack_data(_pack(raw))
        assert result["ok"] is False, why
        codes = {i["code"] for i in result["issues"]}
        assert "why_it_matters_placeholder" in codes or "why_it_matters_too_short" in codes


def test_multiple_questions_fail_one_primary_unknown():
    raw = dict(
        _GOOD_Q,
        question="What is X? And also, what is Y?",
    )
    result = check_pack_data(_pack(raw))
    assert result["ok"] is False
    codes = {i["code"] for i in result["issues"]}
    assert "multiple_unknowns" in codes


def test_loader_still_defaults_missing_why():
    """Lint is stricter than the runtime loader — ranking can still ingest thin packs."""
    qs = questions_from_pack(
        _pack(
            {
                "question": "What signals predict goal misgeneralization early?",
                "operationalization": (
                    "AUROC > 0.8 across three controlled environments for early warning."
                ),
                "tags": ["alignment"],
            }
        )
    )
    assert len(qs) == 1
    assert qs[0].why_it_matters


def test_unsupported_schema_fails():
    result = check_pack_data(_pack(_GOOD_Q, schema_version="emotion_catalog.v1"))
    assert result["ok"] is False
    codes = {i["code"] for i in result["issues"]}
    assert "unsupported_schema" in codes


def test_check_packs_path_missing_file(tmp_path: Path):
    missing = tmp_path / "nope.json"
    report = check_packs(paths=[missing])
    assert report["ok"] is False
    codes = {i["code"] for pack in report["packs"] for i in pack["issues"]}
    assert "missing_file" in codes


def test_check_packs_path_bad_pack(tmp_path: Path):
    path = tmp_path / "thin.json"
    path.write_text(json.dumps(_pack({**_GOOD_Q, "why_it_matters": ""})), encoding="utf-8")
    report = check_packs(paths=[path])
    assert report["ok"] is False
    assert report["n_errors"] >= 1


def test_cli_pack_check_bundled_json(capsys):
    assert main(["emotions", "pack", "check", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["n_errors"] == 0
    assert payload["n_packs"] >= 6
    assert payload["report"] == "pack_contributing_lint"


def test_cli_pack_check_failing_path(tmp_path: Path, capsys):
    path = tmp_path / "bad.json"
    path.write_text(
        json.dumps(_pack({**_GOOD_Q, "operationalization": "short"})),
        encoding="utf-8",
    )
    assert main(["emotions", "pack", "check", "--path", str(path), "--json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False


def test_cli_pack_load_still_works(capsys):
    assert main(["emotions", "pack", "--json"]) == 0
    pack = json.loads(capsys.readouterr().out)
    assert pack["name"] == "affective_science"
    assert pack["count"] >= 8


def test_cli_pack_check_human_text(capsys):
    assert main(["emotions", "pack", "check"]) == 0
    out = capsys.readouterr().out.lower()
    assert "contributing" in out
    assert "ok" in out


def test_contributing_documents_pack_check():
    root = Path(__file__).resolve().parents[1]
    text = (root / "CONTRIBUTING.md").read_text(encoding="utf-8")
    collapsed = " ".join(text.lower().split())
    assert "emotions pack check" in collapsed
    assert "operationalization" in collapsed
    assert "why_it_matters" in collapsed
