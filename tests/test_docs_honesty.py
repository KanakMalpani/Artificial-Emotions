"""P0 honesty: advertised claims must not drift into overclaim or stale counts."""

from __future__ import annotations

import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _readme() -> str:
    return (_ROOT / "README.md").read_text(encoding="utf-8")


def _limits() -> str:
    return (_ROOT / "docs" / "LIMITS.md").read_text(encoding="utf-8")


def _proofs() -> str:
    return (_ROOT / "docs" / "PROOFS.md").read_text(encoding="utf-8")


def _roadmap() -> str:
    return (_ROOT / "docs" / "ROADMAP.md").read_text(encoding="utf-8")


def _roadmap_summary() -> str:
    return (_ROOT / "docs" / "ROADMAP_SUMMARY.md").read_text(encoding="utf-8")


def _changelog() -> str:
    return (_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")


def test_readme_and_limits_passing_counts_agree():
    """Advertised passing counts must match each other.

    Update README badge + verify comment + LIMITS in the same commit after
    ``pytest -q``. Do not leave a stale snapshot behind when the suite grows.
    """
    readme = _readme()
    badge_m = re.search(r"tests-(\d+)%20passing", readme)
    verify_m = re.search(r"# (\d+) passed", readme)
    limits_m = re.search(r"pytest -q` \((\d+) passed\)", _limits())
    assert badge_m, "README tests badge missing (tests-N%20passing)"
    assert verify_m, "README verify-section passing-count comment missing"
    assert limits_m, "LIMITS.md passing-count snapshot missing"
    badge_n = int(badge_m.group(1))
    verify_n = int(verify_m.group(1))
    limits_n = int(limits_m.group(1))
    assert badge_n == verify_n == limits_n, (
        f"README badge {badge_n} vs verify {verify_n} vs LIMITS {limits_n}"
    )
    assert badge_n >= 1200, "advertised suite shrank without a LIMITS rationale"


def test_coverage_badge_matches_readme_body_and_floor():
    pyproject = (_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    floor_m = re.search(r"fail_under\s*=\s*(\d+)", pyproject)
    assert floor_m, "pyproject coverage fail_under missing"
    floor = int(floor_m.group(1))

    readme = _readme()
    badge_m = re.search(r"coverage-(\d+)%25", readme)
    verify_m = re.search(r"# \d+ passed · (\d+)%", readme)
    assert badge_m, "README coverage badge missing (coverage-N%25)"
    assert verify_m, "README verify-section coverage percent missing"
    badge_pct = int(badge_m.group(1))
    verify_pct = int(verify_m.group(1))
    assert badge_pct == verify_pct, f"README badge {badge_pct}% vs verify {verify_pct}%"
    assert badge_pct >= floor, f"advertised {badge_pct}% is below fail_under={floor}"
    assert "floor" in readme.lower()


def test_wired_imagination_kinds_are_not_documented_as_stubs():
    """harm_scenario / rehearsal / eulogy generators shipped; product docs must not call them stubs.

    Tagged CHANGELOG ``[1.0.0]`` may keep historical stub language. README,
    LIMITS, and ARCHITECTURE describe current code.
    """
    architecture = (_ROOT / "docs" / "ARCHITECTURE.md").read_text(encoding="utf-8")
    for blob in (_readme(), _limits(), architecture):
        lowered = blob.lower()
        assert "stubs until generators land" not in lowered
        assert "registered stubs" not in lowered
        assert "generators next" not in lowered
    for rel in (
        "src/artificial_emotions/api_pkg/routers/meta.py",
        "src/artificial_emotions/api_pkg/routers/alive.py",
    ):
        surface = (_ROOT / rel).read_text(encoding="utf-8")
        assert "Stubs and" not in surface


def test_limits_proofs_roadmap_keep_hard_non_claims():
    limits = _limits().lower()
    proofs = _proofs().lower()
    roadmap = _roadmap().lower()
    summary = _roadmap_summary().lower()
    for blob in (limits, proofs, roadmap, summary):
        assert "not calibrated" in blob or "not a calibration" in blob
        assert "not_evsi" in blob or "not evsi" in blob
    assert "not a waf" in limits
    assert "residual" in limits
    assert "not phenomenal" in limits or "not phenomenal feeling" in limits
    assert "not a lab closed-loop" in limits or "not experiment execution" in limits

    verified = limits.split("## known limits", 1)[0]
    assert "scores are calibrated" not in verified
    assert "calibrated curiosity scores" not in verified
    assert "the system feels" not in verified
    assert "tls termination" not in verified
    # Honest negations may contain these substrings; require the negation nearby.
    assert "not dual-use solved" in limits
    assert "not production" in limits or "not a production" in limits


def test_changelog_unreleased_precedes_tagged_1_0_0():
    """Post-tag work belongs under Unreleased — do not rewrite [1.0.0]."""
    text = _changelog()
    assert "## [Unreleased]" in text
    assert "## [1.0.0]" in text
    assert text.index("## [Unreleased]") < text.index("## [1.0.0]"), (
        "[Unreleased] must sit above tagged 1.0.0"
    )
    body = text.split("## [1.0.0]", 1)[1]
    nxt = body.find("\n## ")
    tagged = (body if nxt < 0 else body[:nxt]).lower()
    assert "not calibrated" in tagged
    assert "residual" in tagged
    assert "not a production" in tagged or "not production" in tagged


def test_proofs_packaging_acknowledges_published_1_0_0():
    proofs = _proofs()
    pack = proofs.split("## Packaging smoke", 1)[1].split("## ", 1)[0]
    lowered = pack.lower()
    assert "1.0.0" in pack
    assert "when ready" not in lowered
    assert "does not publish" in lowered or "not a pypi publish" in lowered


def test_roadmap_section_2_leaves_v1_1_unfinished():
    text = _roadmap()
    section = text.split("## 2. Priority queue", 1)[1].split("## 3.", 1)[0]
    remaining = section.split("### Remaining next", 1)[1].split("### Shipped leftovers", 1)[0]
    assert "**v1.1-cal**" in remaining
    assert "**v1.1-http**" in remaining
    assert "✅" not in remaining.split("**v1.1-cal**", 1)[1].split("\n", 1)[0]
    assert "✅" not in remaining.split("**v1.1-http**", 1)[1].split("\n", 1)[0]
    leftovers = section.split("### Shipped leftovers", 1)[1].split("### How to pick", 1)[0]
    assert "**W-cal**" in leftovers
    assert "not calibrated" in leftovers.lower()
    summary = _roadmap_summary()
    assert "v1.1 calibration proof" in summary.lower() or "v1.1-cal" in summary.lower()
    assert "production HTTP" in summary
    assert "W-cal scaffolding shipped" in summary or "W-cal** scaffolding" in summary
