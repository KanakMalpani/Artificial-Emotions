"""VOI worksheet export — fill template metadata only (not EVSI)."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from artificial_emotions.resources import find_data_file

__all__ = [
    "HONESTY_NOT_EVSI",
    "default_voi_template_path",
    "estimate_evsi",
    "fill_voi_worksheet",
    "load_voi_template",
]

#: Machine-readable honesty token. Worksheet fill is not computed EVSI/ENBS.
HONESTY_NOT_EVSI = "not_evsi"

_HONESTY_NOTE = (
    "Not computed EVSI. External decision model + utilities required. "
    "Supporting notes are private local notes; not in the public tree."
)


def default_voi_template_path() -> Path:
    return find_data_file("examples/voi_worksheet_template.json")


def load_voi_template(path: str | Path | None = None) -> dict[str, Any]:
    p = Path(path) if path else default_voi_template_path()
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Invalid VOI template: {p}")
    return data


def _nonempty_seq(value: Any) -> bool:
    if isinstance(value, str | bytes | bytearray) or not isinstance(value, Sequence):
        return False
    return len(value) > 0


def estimate_evsi(
    *,
    psa_draws: Sequence[Any] | None = None,
    utilities: Sequence[Any] | None = None,
    likelihood: Any = None,
    options: Sequence[Any] | None = None,
) -> float | None:
    """Optional EVSI formula hook.

    Returns ``None`` without PSA draws, utilities, likelihood, and options.
    There is no in-tree solver: even when those inputs are present this
    returns ``None`` rather than inventing a number. Never derives EVSI from
    curiosity ``ScoreAxes``.
    """
    has_data = (
        _nonempty_seq(psa_draws)
        and _nonempty_seq(utilities)
        and likelihood is not None
        and _nonempty_seq(options)
    )
    if not has_data:
        return None
    # Fail-closed: ConVOI / ISPOR tooling is external. Do not invent EVSI.
    return None


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

    Always sets ``evsi`` to ``None`` and ``honesty`` to ``not_evsi``.
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
    sheet["filled_by"] = "artificial_emotions.fill_voi_worksheet"
    note = sheet.get("honesty_note") or sheet.get("honesty") or _HONESTY_NOTE
    if not isinstance(note, str) or note == HONESTY_NOT_EVSI:
        note = _HONESTY_NOTE
    sheet["honesty"] = HONESTY_NOT_EVSI
    sheet["honesty_note"] = note
    sheet["evsi"] = estimate_evsi()
    if isinstance(sheet.get("external_compute"), Mapping):
        sheet["external_compute"] = dict(sheet["external_compute"])
    sheet["imprecise_note"] = (
        "If stakeholders disagree on utilities, prefer profile-compare + veto "
        "(strictest max_risk) over a fake consensus EVSI. See research/VOI_IMPRECISE.md."
    )
    return sheet
