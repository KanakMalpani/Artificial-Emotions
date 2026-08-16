"""Bayesian surprise closed-loop worksheet — belief-shift logging only.

Not EVSI and not AutoDiscovery Bayesian surprise. See research/BAYESIAN_SURPRISE.md.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from artificial_emotions.resources import find_data_file
from artificial_emotions.timeutil import utc_now_iso


def default_surprise_worksheet_path() -> Path:
    return find_data_file("examples/bayesian_surprise_worksheet.json")


def fill_surprise_worksheet(
    *,
    question_id: str | None = None,
    profile_name: str | None = None,
    predicted_surprise: float | None = None,
    pilot_result: str = "",
    belief_shift_1_to_5: int | None = None,
    crude_update_note: str = "",
    template_path: str | Path | None = None,
) -> dict[str, Any]:
    """Prefill belief-shift worksheet metadata — does not rename ScoreAxes.surprise."""
    p = Path(template_path) if template_path else default_surprise_worksheet_path()
    sheet = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(sheet, dict):
        raise ValueError(f"Invalid surprise worksheet: {p}")
    sheet = dict(sheet)
    fields = dict(sheet.get("fields") or {})
    fields["question_id"] = question_id
    fields["profile_name"] = profile_name
    fields["predicted_surprise"] = predicted_surprise
    fields["pilot_result"] = pilot_result or fields.get("pilot_result") or ""
    fields["belief_shift_1_to_5"] = belief_shift_1_to_5
    fields["crude_update_note"] = crude_update_note or fields.get("crude_update_note") or ""
    fields["logged_at"] = utc_now_iso()
    sheet["fields"] = fields
    sheet["filled_by"] = "artificial_emotions.fill_surprise_worksheet"
    sheet["honesty"] = sheet.get("honesty") or (
        "Manual belief-shift logging only — not EVSI, not axis rename, "
        "not AutoDiscovery Bayesian surprise."
    )
    sheet["non_claims"] = [
        "Does not rename ScoreAxes.surprise",
        "Does not compute EVSI/ENBS",
        "n<30 Spearman vs belief_shift is exploratory only",
    ]
    return sheet
