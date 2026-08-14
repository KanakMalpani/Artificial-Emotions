"""Guards for data files that must survive `pip install` (offline).

The worksheet templates and eval fixtures live at the repo root but are read at
runtime. They used to be resolved via ``Path(__file__).parents[2]``, which only
exists in a source checkout — installed users got FileNotFoundError. These tests
pin both halves of the fix: the resolver, and the wheel force-include list.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from artificial_emotions import resources
from artificial_emotions.bayesian import default_surprise_worksheet_path
from artificial_emotions.compare import default_constitution_path
from artificial_emotions.elicit_eval import default_protocol_path
from artificial_emotions.evals import default_fixtures_dir
from artificial_emotions.outcome_loop import default_outcome_loop_fixture
from artificial_emotions.voi import default_voi_template_path

_PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"

# Repo-relative data every default path resolver depends on.
_REQUIRED_FILES = [
    "examples/bayesian_surprise_worksheet.json",
    "examples/constitution_veto_stack.json",
    "examples/elicit_ab_protocol.json",
    "examples/elicit_ab_sample_responses.json",
    "examples/elicit_ab_sample_responses_climate.json",
    "examples/voi_worksheet_template.json",
    "examples/discovery_corpus_demo.json",
    "examples/discovery_corpus_timesplit_demo.json",
    "evals/fixtures/cooccur_neglectedness_smoke_v1.json",
    "evals/fixtures/preference_calibration_smoke_v1.jsonl",
    "evals/fixtures/outcome_loop_smoke_v1.jsonl",
]


def _force_include() -> dict[str, str]:
    data = tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))
    wheel = data["tool"]["hatch"]["build"]["targets"]["wheel"]
    return wheel.get("force-include", {})


@pytest.mark.parametrize("relative", _REQUIRED_FILES)
def test_required_data_file_resolves(relative: str):
    path = resources.find_data_file(relative)
    assert path.is_file(), f"{relative} did not resolve to a readable file ({path})"


@pytest.mark.parametrize("relative", _REQUIRED_FILES)
def test_required_data_file_is_shipped_in_wheel(relative: str):
    """Every runtime data file must be force-included, or installs break."""
    include = _force_include()
    covered = relative in include or any(
        relative.startswith(f"{src.rstrip('/')}/") for src in include
    )
    assert covered, (
        f"{relative} is read at runtime but not in "
        f"[tool.hatch.build.targets.wheel.force-include] — pip installs will 404 on it."
    )


def test_force_include_targets_land_inside_the_package():
    """Targets must sit under artificial_emotions/data/ so the resolver finds them."""
    for source, target in _force_include().items():
        assert target.startswith("artificial_emotions/data/"), (
            f"force-include {source} → {target} lands outside the package data dir"
        )
        assert Path(_PYPROJECT.parent / source).exists(), f"force-include source missing: {source}"


def test_default_paths_all_exist():
    for path in (
        default_surprise_worksheet_path(),
        default_constitution_path(),
        default_protocol_path(),
        default_voi_template_path(),
        default_outcome_loop_fixture(),
    ):
        assert path.is_file(), path
    assert default_fixtures_dir().is_dir()


def test_find_data_file_prefers_packaged_copy(tmp_path, monkeypatch):
    packaged = tmp_path / "pkg"
    (packaged / "examples").mkdir(parents=True)
    (packaged / "examples" / "thing.json").write_text("{}", encoding="utf-8")
    source = tmp_path / "repo"
    (source / "examples").mkdir(parents=True)
    (source / "examples" / "thing.json").write_text("{}", encoding="utf-8")

    monkeypatch.setattr(resources, "data_dir", lambda: packaged)
    monkeypatch.setattr(resources, "repo_root", lambda: source)
    assert resources.find_data_file("examples/thing.json") == packaged / "examples/thing.json"


def test_find_data_file_falls_back_to_repo_checkout(tmp_path, monkeypatch):
    source = tmp_path / "repo"
    (source / "examples").mkdir(parents=True)
    (source / "examples" / "thing.json").write_text("{}", encoding="utf-8")

    monkeypatch.setattr(resources, "data_dir", lambda: tmp_path / "absent")
    monkeypatch.setattr(resources, "repo_root", lambda: source)
    assert resources.find_data_file("examples/thing.json") == source / "examples/thing.json"


def test_find_data_file_missing_returns_packaged_path(tmp_path, monkeypatch):
    """Neither copy present → stable packaged path so the caller's error names it."""
    monkeypatch.setattr(resources, "data_dir", lambda: tmp_path / "pkg")
    monkeypatch.setattr(resources, "repo_root", lambda: tmp_path / "repo")
    assert resources.find_data_file("examples/nope.json") == tmp_path / "pkg/examples/nope.json"


def test_find_data_dir_resolution(tmp_path, monkeypatch):
    source = tmp_path / "repo"
    (source / "evals" / "fixtures").mkdir(parents=True)
    monkeypatch.setattr(resources, "data_dir", lambda: tmp_path / "absent")
    monkeypatch.setattr(resources, "repo_root", lambda: source)
    assert resources.find_data_dir("evals/fixtures") == source / "evals/fixtures"

    monkeypatch.setattr(resources, "repo_root", lambda: tmp_path / "gone")
    assert resources.find_data_dir("evals/fixtures") == tmp_path / "absent/evals/fixtures"


def test_pytest_pythonpath_keeps_repo_root_importable():
    """Ubuntu collection has `src` on the path, not cwd.

    `from tests.*` then raises ``ModuleNotFoundError: No module named 'tests'``
    (publish.yml run 31850928558). Repo root must stay on pythonpath.
    """
    data = tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))
    pythonpath = data["tool"]["pytest"]["ini_options"]["pythonpath"]
    assert "." in pythonpath, (
        "pythonpath must include '.' so test modules can import each other "
        "as tests.* when pytest/importlib does not put cwd on sys.path"
    )
