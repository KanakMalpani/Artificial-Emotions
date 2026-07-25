"""Expert-eval / spot-check harness (W10 / WO-0.3.1–0.3.2).

Offline fixtures only — no live literature required for the harness itself.
Methodology: see evals/METHODOLOGY.md. Do NOT publish a single “accuracy %”.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from artificial_curiosity.models import GapStatus, LiteratureHit, UnansweredQuestion
from artificial_curiosity.resources import find_data_dir
from artificial_curiosity.verify import verify_gap


def default_fixtures_dir() -> Path:
    return find_data_dir("evals/fixtures")


@dataclass
class SpotCheckCase:
    case_id: str
    question: UnansweredQuestion
    # Human / expert gold label for gap status (offline).
    gold_status: GapStatus
    # Optional pre-baked literature hits for offline verify path.
    hits: list[LiteratureHit] = field(default_factory=list)
    notes: str = ""
    # If True, top-ranked presentation of this Q would be an F1 failure.
    already_answered_fail_if_returned: bool = False


@dataclass
class SpotCheckResult:
    case_id: str
    gold_status: str
    predicted_status: str
    match: bool
    top_overlap: float
    strong_match_count: int
    notes: str = ""


@dataclass
class HarnessReport:
    n_cases: int
    n_match: int
    n_already_answered_gold: int
    n_missed_answered: int  # gold=likely_answered but predicted otherwise (F1 risk)
    n_false_unknown: int  # predicted unanswered-ish when gold likely_answered
    match_rate: float | None
    results: list[SpotCheckResult] = field(default_factory=list)
    # gold_status → {predicted_status: count} — stratified, not a single accuracy %
    by_gold_status: dict[str, dict[str, int]] = field(default_factory=dict)
    methodology: str = (
        "Offline fixture spot-check. Report case-level agreement and F1-style "
        "miss rates — never a single marketing accuracy percentage."
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "n_cases": self.n_cases,
            "n_match": self.n_match,
            "n_already_answered_gold": self.n_already_answered_gold,
            "n_missed_answered": self.n_missed_answered,
            "n_false_unknown": self.n_false_unknown,
            "match_rate": self.match_rate,
            "by_gold_status": self.by_gold_status,
            "methodology": self.methodology,
            "results": [
                {
                    "case_id": r.case_id,
                    "gold_status": r.gold_status,
                    "predicted_status": r.predicted_status,
                    "match": r.match,
                    "top_overlap": r.top_overlap,
                    "strong_match_count": r.strong_match_count,
                    "notes": r.notes,
                }
                for r in self.results
            ],
        }


class _FixtureLitClient:
    """Literature client that returns pre-baked hits (no network)."""

    def __init__(self, hits: list[LiteratureHit]):
        self.hits = hits

    def search_works(self, query: str, per_page: int = 8) -> list[LiteratureHit]:
        return list(self.hits)[:per_page]


def _parse_case(raw: dict[str, Any]) -> SpotCheckCase:
    qraw = raw["question"]
    q = UnansweredQuestion(
        id=str(qraw.get("id") or raw.get("case_id") or "case"),
        question=str(qraw["question"]),
        domain=qraw.get("domain") or "general",
        operationalization=str(qraw["operationalization"]),
        why_it_matters=str(qraw.get("why_it_matters") or "fixture"),
        tags=list(qraw.get("tags") or []),
        source="eval_fixture",
    )
    hits = [LiteratureHit.model_validate(h) for h in (raw.get("hits") or [])]
    gold = GapStatus(str(raw["gold_status"]))
    return SpotCheckCase(
        case_id=str(raw.get("case_id") or q.id),
        question=q,
        gold_status=gold,
        hits=hits,
        notes=str(raw.get("notes") or ""),
        already_answered_fail_if_returned=bool(
            raw.get("already_answered_fail_if_returned") or gold == GapStatus.LIKELY_ANSWERED
        ),
    )


def load_fixtures(path: str | Path | None = None) -> list[SpotCheckCase]:
    """Load spot-check cases from a JSON file or directory of JSON files.

    Default loads **all** ``*.json`` under ``evals/fixtures/`` (v1 + adversarial v2).
    """
    if path is None:
        path = default_fixtures_dir()
    p = Path(path)
    files: list[Path]
    if p.is_dir():
        files = sorted(p.glob("*.json"))
    else:
        files = [p]
    cases: list[SpotCheckCase] = []
    for f in files:
        # Hand-label gap-status packs use a different schema (items/…).
        if f.name.startswith("gap_status_") or f.name.startswith("cooccur_"):
            continue
        data = json.loads(f.read_text(encoding="utf-8"))
        if isinstance(data, dict) and "cases" in data:
            rows = data["cases"]
        elif isinstance(data, list):
            rows = data
        elif isinstance(data, dict) and "items" in data:
            # Not a spot-check pack — skip (gap-status handlabel, etc.).
            continue
        else:
            rows = [data]
        for raw in rows:
            if not isinstance(raw, dict) or "question" not in raw:
                continue
            cases.append(_parse_case(raw))
    return cases


def run_spotcheck(cases: list[SpotCheckCase] | None = None) -> HarnessReport:
    """
    Run offline gap classification against fixture gold labels.

    Uses verify_gap with a fixture literature client when hits are provided;
    empty hits → ``unknown_with_caveat`` via the normal verify path.
    """
    if cases is None:
        cases = load_fixtures()

    results: list[SpotCheckResult] = []
    n_match = 0
    n_answered_gold = 0
    n_missed = 0
    n_false_unknown = 0
    by_gold: dict[str, dict[str, int]] = {}

    for case in cases:
        gap = verify_gap(
            case.question,
            client=_FixtureLitClient(list(case.hits)),
            use_literature=True,
            literature_backend="fixture",
        )
        predicted = gap.status
        top_overlap = gap.top_overlap
        strong = gap.strong_match_count
        notes = gap.notes

        match = predicted == case.gold_status
        if match:
            n_match += 1
        gold_key = case.gold_status.value
        pred_key = predicted.value
        bucket = by_gold.setdefault(gold_key, {})
        bucket[pred_key] = bucket.get(pred_key, 0) + 1
        if case.gold_status == GapStatus.LIKELY_ANSWERED:
            n_answered_gold += 1
            if predicted != GapStatus.LIKELY_ANSWERED:
                n_missed += 1
                n_false_unknown += 1

        results.append(
            SpotCheckResult(
                case_id=case.case_id,
                gold_status=case.gold_status.value,
                predicted_status=predicted.value,
                match=match,
                top_overlap=top_overlap,
                strong_match_count=strong,
                notes=notes[:240],
            )
        )

    n = len(cases)
    return HarnessReport(
        n_cases=n,
        n_match=n_match,
        n_already_answered_gold=n_answered_gold,
        n_missed_answered=n_missed,
        n_false_unknown=n_false_unknown,
        match_rate=(n_match / n) if n else None,
        results=results,
        by_gold_status=by_gold,
    )


def already_answered_fail_rate(report: HarnessReport) -> float | None:
    """Fraction of gold-likely_answered cases the harness failed to mark answered (F1 monitor)."""
    if report.n_already_answered_gold == 0:
        return None
    return report.n_missed_answered / report.n_already_answered_gold


def _normalize_gold_status(raw: str) -> GapStatus:
    key = str(raw or "").strip().lower()
    if key in ("answered", "likely_answered"):
        return GapStatus.LIKELY_ANSWERED
    if key in ("partial", "partially_answered"):
        return GapStatus.PARTIALLY_ANSWERED
    if key in ("unknown", "unknown_with_caveat"):
        return GapStatus.UNKNOWN_WITH_CAVEAT
    return GapStatus.UNANSWERED


@dataclass
class GapStatusCase:
    case_id: str
    question: UnansweredQuestion
    gold_status: GapStatus
    related_but_unanswered: bool = False
    hits: list[LiteratureHit] = field(default_factory=list)
    notes: str = ""
    gold_tags: list[str] = field(default_factory=list)


@dataclass
class GapStatusReport:
    n_cases: int
    status_accuracy: float | None
    related_but_unanswered_n: int
    related_but_unanswered_recall: float | None
    false_answered_rate: float | None
    n_false_answered: int
    results: list[dict[str, Any]] = field(default_factory=list)
    methodology: str = (
        "Hand-labeled gap-status fixture eval. Report status_accuracy, "
        "related_but_unanswered_recall, and false_answered_rate — never a vanity "
        "single marketing accuracy claim."
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "n_cases": self.n_cases,
            "status_accuracy": self.status_accuracy,
            "related_but_unanswered_n": self.related_but_unanswered_n,
            "related_but_unanswered_recall": self.related_but_unanswered_recall,
            "false_answered_rate": self.false_answered_rate,
            "n_false_answered": self.n_false_answered,
            "methodology": self.methodology,
            "results": self.results,
        }


def load_gap_status_fixtures(path: str | Path | None = None) -> list[GapStatusCase]:
    """Load hand-label gap fixtures (template schema or spotcheck-compatible)."""
    if path is None:
        path = default_fixtures_dir() / "gap_status_handlabel_v1.json"
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    rows = data.get("items") or data.get("cases") or []
    out: list[GapStatusCase] = []
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        qraw = raw.get("question") or {}
        if isinstance(qraw, str):
            qraw = {"question": qraw}
        qtext = str(qraw.get("question") or raw.get("question_text") or "").strip()
        if not qtext or qtext.startswith("REPLACE"):
            continue
        q = UnansweredQuestion(
            id=str(raw.get("question_id") or raw.get("case_id") or qraw.get("id") or "gap"),
            question=qtext,
            domain=qraw.get("domain") or raw.get("domain") or "general",
            operationalization=str(
                qraw.get("operationalization")
                or raw.get("operationalization")
                or "Hand-label fixture — operationalize with a measurable success criterion."
            ),
            why_it_matters=str(qraw.get("why_it_matters") or raw.get("notes") or "fixture"),
            tags=list(qraw.get("tags") or raw.get("tags") or []),
            source="gap_status_fixture",
        )
        hits = [LiteratureHit.model_validate(h) for h in (raw.get("hits") or [])]
        out.append(
            GapStatusCase(
                case_id=str(raw.get("question_id") or raw.get("case_id") or q.id),
                question=q,
                gold_status=_normalize_gold_status(
                    str(raw.get("gold_status") or GapStatus.UNANSWERED.value)
                ),
                related_but_unanswered=bool(raw.get("related_but_unanswered")),
                hits=hits,
                notes=str(raw.get("notes") or ""),
                gold_tags=[str(t) for t in (raw.get("gold_tags") or [])],
            )
        )
    return out


def run_gap_status_eval(cases: list[GapStatusCase] | None = None) -> GapStatusReport:
    """Status accuracy + related-but-unanswered recall (F1 / related≠answered)."""
    if cases is None:
        cases = load_gap_status_fixtures()
    results: list[dict[str, Any]] = []
    n_match = 0
    n_rbu = 0
    n_rbu_ok = 0
    n_false_answered = 0

    for case in cases:
        gap = verify_gap(
            case.question,
            client=_FixtureLitClient(list(case.hits)),
            use_literature=True,
            literature_backend="fixture",
        )
        pred = gap.status
        match = pred == case.gold_status
        if match:
            n_match += 1
        # related-but-unanswered: gold says neighborhood exists but not settled;
        # success = predicted unanswered or partially_answered (not likely_answered)
        if case.related_but_unanswered:
            n_rbu += 1
            if pred in (GapStatus.UNANSWERED, GapStatus.PARTIALLY_ANSWERED):
                n_rbu_ok += 1
        if case.gold_status != GapStatus.LIKELY_ANSWERED and pred == GapStatus.LIKELY_ANSWERED:
            n_false_answered += 1
        results.append(
            {
                "case_id": case.case_id,
                "gold_status": case.gold_status.value,
                "predicted_status": pred.value,
                "match": match,
                "related_but_unanswered": case.related_but_unanswered,
                "gold_tags": list(case.gold_tags),
                "top_overlap": gap.top_overlap,
                "strong_match_count": gap.strong_match_count,
            }
        )

    n = len(cases)
    return GapStatusReport(
        n_cases=n,
        status_accuracy=(n_match / n) if n else None,
        related_but_unanswered_n=n_rbu,
        related_but_unanswered_recall=(n_rbu_ok / n_rbu) if n_rbu else None,
        false_answered_rate=(n_false_answered / n) if n else None,
        n_false_answered=n_false_answered,
        results=results,
    )
