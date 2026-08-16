"""Versioned domain pack loader (WO-0.3.6) + CONTRIBUTING pack lint.

Packs are JSON assets that extend/override seed questions without code edits.
Schema is intentionally small — see CONTRIBUTING.md. `check_packs` enforces
the seed/pack bar (operationalization + why_it_matters) without changing the
lenient runtime loader.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from artificial_emotions.logutil import get_logger, soft_fail
from artificial_emotions.models import Domain, UnansweredQuestion

logger = get_logger("packs")

PACK_SCHEMA_VERSION = "domain_pack.v1"
# CONTRIBUTING JSON example / loader floor.
MIN_OPERATIONALIZATION_CHARS = 20
MIN_WHY_IT_MATTERS_CHARS = 20
MIN_QUESTION_CHARS = 12

_PLACEHOLDER_WHY = frozenset(
    {
        "pack-provided unknown",
        "sounds interesting",
        "interesting",
        "tbd",
        "todo",
        "...",
        "…",
        "n/a",
        "na",
        "placeholder",
        "why it matters",
    }
)
_VALID_DOMAINS = {d.value for d in Domain}

__all__ = [
    "MIN_OPERATIONALIZATION_CHARS",
    "MIN_QUESTION_CHARS",
    "MIN_WHY_IT_MATTERS_CHARS",
    "PACK_SCHEMA_VERSION",
    "check_pack_data",
    "check_pack_file",
    "check_packs",
    "default_packs_dir",
    "load_domain_packs",
    "load_pack_file",
    "questions_from_pack",
]


def default_packs_dir() -> Path:
    return Path(__file__).resolve().parent / "packs"


def load_pack_file(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Pack must be a JSON object: {p}")
    return data


def _is_skipped_pack_file(path: Path) -> bool:
    """Skip non-domain assets co-located in packs/ (e.g. emotion_catalog.json)."""
    return path.name == "emotion_catalog.json" or path.stem.startswith("emotion_")


def _iter_bundled_pack_files(packs_dir: Path) -> list[Path]:
    if not packs_dir.is_dir():
        return []
    return sorted(
        p for p in packs_dir.glob("*.json") if p.is_file() and not _is_skipped_pack_file(p)
    )


def questions_from_pack(data: dict[str, Any]) -> list[UnansweredQuestion]:
    """Parse pack JSON → UnansweredQuestion list (validates operationalization bar lightly)."""
    schema = str(data.get("schema_version") or PACK_SCHEMA_VERSION)
    if not schema.startswith("domain_pack"):
        raise ValueError(f"Unsupported pack schema_version: {schema}")
    domain = str(data.get("domain") or Domain.GENERAL.value)
    raw_qs = data.get("questions") or []
    out: list[UnansweredQuestion] = []
    for i, raw in enumerate(raw_qs):
        if not isinstance(raw, dict):
            continue
        ops = str(raw.get("operationalization") or "").strip()
        if len(ops) < MIN_OPERATIONALIZATION_CHARS:
            raise ValueError(
                f"Pack question[{i}] operationalization too short "
                f"(need ≥{MIN_OPERATIONALIZATION_CHARS} chars; see CONTRIBUTING seed bar)"
            )
        qid = str(raw.get("id") or f"{domain}-pack-{i + 1:02d}")
        out.append(
            UnansweredQuestion(
                id=qid,
                question=str(raw["question"]).strip(),
                domain=raw.get("domain") or domain,
                operationalization=ops,
                why_it_matters=str(raw.get("why_it_matters") or "").strip()
                or "Pack-provided unknown.",
                assumptions=list(raw.get("assumptions") or []),
                enabling_questions=list(raw.get("enabling_questions") or []),
                tags=list(raw.get("tags") or []),
                source=str(raw.get("source") or f"pack:{data.get('name', 'unnamed')}"),
            )
        )
    return out


def load_domain_packs(
    paths: list[str | Path] | None = None,
    *,
    packs_dir: str | Path | None = None,
) -> list[UnansweredQuestion]:
    """Load explicit paths and/or all `*.json` under packs_dir."""
    files: list[Path] = []
    if paths:
        files.extend(Path(p) for p in paths)
    directory = Path(packs_dir) if packs_dir is not None else default_packs_dir()
    if directory.is_dir():
        files.extend(sorted(directory.glob("*.json")))
    seen: set[str] = set()
    out: list[UnansweredQuestion] = []
    for f in files:
        if not f.is_file():
            continue
        key = str(f.resolve())
        if key in seen:
            continue
        seen.add(key)
        if _is_skipped_pack_file(f):
            continue
        try:
            data = load_pack_file(f)
        except (OSError, ValueError) as exc:
            soft_fail(logger, "Skipping unreadable domain pack %s", f, exc=exc)
            continue
        schema = str(data.get("schema_version") or "")
        if schema and not schema.startswith("domain_pack"):
            continue
        if not data.get("questions"):
            continue
        qs = questions_from_pack(data)
        out.extend(qs)
    return out


def _issue(
    code: str,
    message: str,
    *,
    question_id: str | None = None,
    severity: str = "error",
) -> dict[str, Any]:
    return {
        "code": code,
        "severity": severity,
        "question_id": question_id,
        "message": message,
    }


def _norm_placeholder(text: str) -> str:
    return text.strip().lower().rstrip(".! ")


def _is_placeholder_why(why: str) -> bool:
    return _norm_placeholder(why) in _PLACEHOLDER_WHY


def check_pack_data(data: dict[str, Any], *, source: str = "") -> dict[str, Any]:
    """Lint one pack object against the CONTRIBUTING seed/pack bar.

    Stricter than ``questions_from_pack``: missing ``why_it_matters`` is an
    error here, not a silent default.
    """
    issues: list[dict[str, Any]] = []
    schema = str(data.get("schema_version") or "").strip()
    if not schema:
        issues.append(_issue("missing_schema", "schema_version missing (need domain_pack.v1)"))
    elif not schema.startswith("domain_pack"):
        issues.append(_issue("unsupported_schema", f"Unsupported pack schema_version: {schema}"))

    domain = str(data.get("domain") or "").strip()
    if not domain:
        issues.append(_issue("missing_domain", "pack domain missing"))
    elif domain not in _VALID_DOMAINS:
        issues.append(_issue("invalid_domain", f"domain '{domain}' is not a known Domain"))

    raw_qs = data.get("questions")
    if not isinstance(raw_qs, list) or not raw_qs:
        issues.append(_issue("empty_questions", "questions must be a non-empty list"))
        raw_qs = []

    question_ids: list[str] = []
    for i, raw in enumerate(raw_qs):
        if not isinstance(raw, dict):
            issues.append(
                _issue(
                    "invalid_question_entry",
                    f"questions[{i}] must be an object",
                    question_id=f"index:{i}",
                )
            )
            continue
        qid = str(raw.get("id") or f"{domain or 'pack'}-pack-{i + 1:02d}")
        question_ids.append(qid)
        issues.extend(_check_question(raw, qid=qid, pack_domain=domain))

    errors = [i for i in issues if i["severity"] == "error"]
    warnings = [i for i in issues if i["severity"] != "error"]
    return {
        "ok": not errors,
        "source": source,
        "name": data.get("name"),
        "n_questions": len(question_ids),
        "n_errors": len(errors),
        "n_warnings": len(warnings),
        "question_ids": question_ids,
        "issues": issues,
    }


def _check_question(raw: dict[str, Any], *, qid: str, pack_domain: str) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    q = str(raw.get("question") or "").strip()
    if not q:
        issues.append(_issue("missing_question", "question missing", question_id=qid))
    elif len(q) < MIN_QUESTION_CHARS:
        issues.append(
            _issue(
                "question_too_short",
                f"question must be ≥{MIN_QUESTION_CHARS} chars",
                question_id=qid,
            )
        )
    elif q.count("?") > 1:
        issues.append(
            _issue(
                "multiple_unknowns",
                "more than one '?' — CONTRIBUTING bar is one primary unknown (F9)",
                question_id=qid,
            )
        )

    q_domain = str(raw.get("domain") or pack_domain or "").strip()
    if q_domain and q_domain not in _VALID_DOMAINS:
        issues.append(
            _issue(
                "invalid_domain",
                f"question domain '{q_domain}' is not a known Domain",
                question_id=qid,
            )
        )

    ops = str(raw.get("operationalization") or "").strip()
    if not ops:
        issues.append(
            _issue(
                "missing_operationalization",
                "operationalization missing (CONTRIBUTING bar)",
                question_id=qid,
            )
        )
    elif len(ops) < MIN_OPERATIONALIZATION_CHARS:
        issues.append(
            _issue(
                "operationalization_too_short",
                f"operationalization must be ≥{MIN_OPERATIONALIZATION_CHARS} chars "
                "(CONTRIBUTING bar)",
                question_id=qid,
            )
        )

    why = str(raw.get("why_it_matters") or "").strip()
    if not why:
        issues.append(
            _issue(
                "missing_why_it_matters",
                "why_it_matters missing (CONTRIBUTING bar)",
                question_id=qid,
            )
        )
    elif _is_placeholder_why(why):
        issues.append(
            _issue(
                "why_it_matters_placeholder",
                "why_it_matters is a placeholder (not “sounds interesting” / TBD)",
                question_id=qid,
            )
        )
    elif len(why) < MIN_WHY_IT_MATTERS_CHARS:
        issues.append(
            _issue(
                "why_it_matters_too_short",
                f"why_it_matters must be ≥{MIN_WHY_IT_MATTERS_CHARS} chars "
                "(stakeholder-relevant reason)",
                question_id=qid,
            )
        )

    tags = raw.get("tags") or []
    if not tags:
        issues.append(
            _issue(
                "missing_tags",
                "tags missing (CONTRIBUTING seed schema)",
                question_id=qid,
                severity="warning",
            )
        )

    blob = " ".join([q, ops, why])
    if blob.strip():
        from artificial_emotions.safety import assess_dual_use

        assessment = assess_dual_use(blob)
        if assessment.hard_reject_likely:
            issues.append(
                _issue(
                    "dual_use_hard_reject",
                    "dual-use hard-reject language (CONTRIBUTING F10; heuristic, not an oracle)",
                    question_id=qid,
                )
            )
        elif assessment.needs_human_review:
            issues.append(
                _issue(
                    "dual_use_review",
                    "dual-use review flag (heuristic; not dual-use solved)",
                    question_id=qid,
                    severity="warning",
                )
            )
    return issues


def check_pack_file(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    source = str(p)
    if not p.is_file():
        issue = _issue("missing_file", f"Pack file not found: {p}")
        return {
            "ok": False,
            "source": source,
            "name": None,
            "n_questions": 0,
            "n_errors": 1,
            "n_warnings": 0,
            "question_ids": [],
            "issues": [issue],
        }
    try:
        data = load_pack_file(p)
    except json.JSONDecodeError as exc:
        issue = _issue("invalid_json", f"Pack is not valid JSON: {exc}")
        return {
            "ok": False,
            "source": source,
            "name": None,
            "n_questions": 0,
            "n_errors": 1,
            "n_warnings": 0,
            "question_ids": [],
            "issues": [issue],
        }
    except ValueError as exc:
        issue = _issue("invalid_pack", str(exc))
        return {
            "ok": False,
            "source": source,
            "name": None,
            "n_questions": 0,
            "n_errors": 1,
            "n_warnings": 0,
            "question_ids": [],
            "issues": [issue],
        }
    result = check_pack_data(data, source=source)
    result["source"] = source
    return result


def _name_matches_pack(path: Path, name: str, pack_name: str | None = None) -> bool:
    key = name.strip().lower().replace("-", "_")
    stem = path.stem.lower().replace("-", "_")
    aliases = {stem, stem.removesuffix("_pack"), f"{stem}_pack"}
    if stem == "affective_science":
        aliases.update({"affect", "affective_science_pack"})
    if key in aliases:
        return True
    if pack_name and key in {
        pack_name.lower().replace("-", "_"),
        pack_name.lower().replace("-", "_").removesuffix("_pack"),
    }:
        return True
    return False


def _summarize_pack_reports(reports: list[dict[str, Any]]) -> dict[str, Any]:
    n_errors = sum(int(p.get("n_errors") or 0) for p in reports)
    n_warnings = sum(int(p.get("n_warnings") or 0) for p in reports)
    n_questions = sum(int(p.get("n_questions") or 0) for p in reports)
    return {
        "ok": n_errors == 0 and bool(reports),
        "report": "pack_contributing_lint",
        "n_packs": len(reports),
        "n_ok": sum(1 for p in reports if p.get("ok")),
        "n_questions": n_questions,
        "n_errors": n_errors,
        "n_warnings": n_warnings,
        "packs": reports,
        "honesty": (
            "Lint against CONTRIBUTING seed/pack bar (operationalization + "
            "why_it_matters). Not a scientific review; not dual-use solved."
        ),
    }


def check_packs(
    paths: list[str | Path] | None = None,
    *,
    name: str | None = None,
    packs_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Lint explicit pack files, a named bundled pack, or all bundled domain packs."""
    directory = Path(packs_dir) if packs_dir is not None else default_packs_dir()
    files: list[Path] = []
    if paths:
        files.extend(Path(p) for p in paths)
    elif name:
        for p in _iter_bundled_pack_files(directory):
            pack_name = None
            try:
                data = load_pack_file(p)
                pack_name = str(data.get("name") or "") or None
            except (OSError, ValueError) as exc:
                soft_fail(logger, "Skipping unreadable pack name lookup %s", p, exc=exc)
                pack_name = None
            if _name_matches_pack(p, name, pack_name):
                files.append(p)
        if not files:
            issue = _issue("unknown_pack", f"No bundled pack matching '{name}'")
            empty = {
                "ok": False,
                "source": name,
                "name": name,
                "n_questions": 0,
                "n_errors": 1,
                "n_warnings": 0,
                "question_ids": [],
                "issues": [issue],
            }
            return _summarize_pack_reports([empty])
    else:
        files.extend(_iter_bundled_pack_files(directory))

    reports = [check_pack_file(f) for f in files]
    return _summarize_pack_reports(reports)
