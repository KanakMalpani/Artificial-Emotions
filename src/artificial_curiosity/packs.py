"""Versioned domain pack loader (WO-0.3.6).

Packs are JSON assets that extend/override seed questions without code edits.
Schema is intentionally small — see CONTRIBUTING.md.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from artificial_curiosity.models import Domain, UnansweredQuestion

PACK_SCHEMA_VERSION = "domain_pack.v1"


def default_packs_dir() -> Path:
    return Path(__file__).resolve().parent / "packs"


def load_pack_file(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Pack must be a JSON object: {p}")
    return data


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
        if len(ops) < 20:
            raise ValueError(
                f"Pack question[{i}] operationalization too short "
                f"(need ≥20 chars; see CONTRIBUTING seed bar)"
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
        qs = questions_from_pack(load_pack_file(f))
        out.extend(qs)
    return out
