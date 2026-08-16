"""Optional swallows log via soft_fail; expected skips still skip; bugs still raise."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from artificial_emotions import transfer as transfer_mod
from artificial_emotions.discover import LocalCorpusClient, discover_links
from artificial_emotions.emotions import mix_emotions
from artificial_emotions.packs import check_packs, load_domain_packs
from artificial_emotions.transfer import discover_transfers
from tests.test_discover import StubClient
from tests.test_transfer import CORPUS

_PACK_Q = {
    "id": "soft-pack-01",
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


def _write_pack(path: Path, *, questions: list[dict] | None = None, **meta: object) -> None:
    body: dict = {
        "schema_version": "domain_pack.v1",
        "name": "soft_fail_fixture",
        "domain": "biology",
        "questions": questions if questions is not None else [_PACK_Q],
    }
    body.update(meta)
    path.write_text(json.dumps(body), encoding="utf-8")


def test_load_domain_packs_skips_corrupt_json_and_logs(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
):
    _write_pack(tmp_path / "ok.json")
    (tmp_path / "bad.json").write_text("{not json\n", encoding="utf-8")
    with caplog.at_level("WARNING", logger="artificial_emotions.packs"):
        qs = load_domain_packs(packs_dir=tmp_path)
    assert [q.id for q in qs] == ["soft-pack-01"]
    assert any("unreadable domain pack" in rec.message for rec in caplog.records)


def test_load_domain_packs_skips_missing_optional_file(tmp_path: Path):
    missing = tmp_path / "no-such-pack.json"
    _write_pack(tmp_path / "ok.json")
    qs = load_domain_packs(paths=[missing], packs_dir=tmp_path)
    assert [q.id for q in qs] == ["soft-pack-01"]


def test_load_domain_packs_propagates_unexpected_load_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    _write_pack(tmp_path / "ok.json")

    def boom(_path: Path) -> dict:
        raise RuntimeError("loader bug")

    monkeypatch.setattr("artificial_emotions.packs.load_pack_file", boom)
    with pytest.raises(RuntimeError, match="loader bug"):
        load_domain_packs(packs_dir=tmp_path)


def test_check_packs_name_lookup_skips_unreadable_and_matches_stem(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
):
    (tmp_path / "noise.json").write_text("{not json\n", encoding="utf-8")
    _write_pack(tmp_path / "climate.json", name="climate")
    with caplog.at_level("WARNING", logger="artificial_emotions.packs"):
        report = check_packs(name="climate", packs_dir=tmp_path)
    assert report["ok"] is True
    assert report["n_packs"] == 1
    assert any("pack name lookup" in rec.message for rec in caplog.records)


def test_transfer_evidence_failure_skips_titles_and_logs(caplog: pytest.LogCaptureFixture):
    class NoSearch:
        def search_works(self, query: str, per_page: int = 8):
            raise RuntimeError("down")

    with caplog.at_level("WARNING", logger="artificial_emotions.transfer"):
        assert transfer_mod._titles(NoSearch(), "Fish oil Blood viscosity", 2) == []
    assert any("transfer evidence titles" in rec.message for rec in caplog.records)

    past = [d for d in CORPUS if int(d["year"]) < 1986]

    class NoSearchClient(LocalCorpusClient):
        def search_works(self, query: str, per_page: int = 8):
            raise RuntimeError("down")

    links = discover_transfers("Fish oil", client=NoSearchClient(documents=past))
    assert links
    assert links[0].evidence_ab == []
    assert links[0].evidence_bc == []


def test_transfer_titles_propagates_post_search_bugs():
    class BadHits:
        def search_works(self, query: str, per_page: int = 8):
            return None

    with pytest.raises(TypeError):
        transfer_mod._titles(BadHits(), "Fish oil Blood viscosity", 2)


def test_discover_titles_propagates_post_search_bugs():
    class BadHits(StubClient):
        def search_works(self, query, per_page=8):
            return None

    with pytest.raises(TypeError):
        discover_links("fish oil", client=BadHits())


def test_mix_unknown_profile_skips_cap_and_logs(caplog: pytest.LogCaptureFixture):
    with caplog.at_level("WARNING", logger="artificial_emotions.emotions"):
        out = mix_emotions(
            {"curiosity": 20, "fear": 40, "anger": 40},
            profile_name="not_a_real_preset",
        )
    assert out["intensity_capped"] is False
    assert out.get("mix_intensity_cap") is None
    assert any("mix intensity cap" in rec.message for rec in caplog.records)


def test_mix_named_profile_still_applies_cap():
    out = mix_emotions(
        {"curiosity": 20, "fear": 40, "anger": 40},
        profile_name="public_demo_strict_risk",
    )
    assert out["intensity_capped"] is True
    assert out["mix_intensity_cap"] == 0.35


def test_mix_cap_lookup_bug_still_raises(monkeypatch: pytest.MonkeyPatch):
    def boom(*, profile_name: str | None = None):  # noqa: ARG001
        raise RuntimeError("profile resolver bug")

    monkeypatch.setattr("artificial_emotions.models.resolve_value_profile", boom)
    with pytest.raises(RuntimeError, match="profile resolver bug"):
        mix_emotions(
            {"curiosity": 20, "fear": 40, "anger": 40},
            profile_name="public_demo_strict_risk",
        )
