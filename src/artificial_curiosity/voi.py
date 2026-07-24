"""VOI worksheet export — fill template metadata only (not EVSI)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
_DEFAULT_TEMPLATE = _REPO / "examples" / "voi_worksheet_template.json"

__all__ = [
    "default_voi_template_path",
    "fill_voi_worksheet",
    "load_voi_template",
]


def default_voi_template_path() -> Path:
    return _DEFAULT_TEMPLATE


def load_voi_template(path: str | Path | None = None) -> dict[str, Any]:
    p = Path(path) if path else default_voi_template_path()
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Invalid VOI template: {p}")
    return data


def fill_voi_worksheet(
    *,
    question_id: str | None = None,
    question: str = "",
    operationalization: str = "",
    profile_name: str | None = None,
    domain: str = "",
    template_path: str | Path | None = None,
) -> dict[str, Any]:
    """
    Emit a VOI worksheet prefilled with ranked-question metadata.

    Does **not** compute EVSI/ENBS — external ConVOI/ISPOR tooling required.
    """
    sheet = load_voi_template(template_path)
    sheet = dict(sheet)
    sheet["decision_problem"] = question or sheet.get("decision_problem") or ""
    link = dict(sheet.get("link_to_ranked_question") or {})
    link["question_id"] = question_id
    link["profile_name"] = profile_name
    link["domain"] = domain or link.get("domain")
    link["operationalization"] = operationalization
    sheet["link_to_ranked_question"] = link
    sheet["proposed_study"] = dict(sheet.get("proposed_study") or {})
    if operationalization and not sheet["proposed_study"].get("endpoints"):
        sheet["proposed_study"]["endpoints"] = [operationalization[:240]]
    sheet["filled_by"] = "artificial_curiosity.fill_voi_worksheet"
    sheet["honesty"] = (
        sheet.get("honesty")
        or "Not computed EVSI. External decision model + utilities required."
    )
    sheet["imprecise_note"] = (
        "If stakeholders disagree on utilities, prefer profile-compare + veto "
        "(strictest max_risk) over a fake consensus EVSI. See research/VOI_IMPRECISE.md."
    )
    return sheet
