"""Optional LLM judge for multi-axis scoring and gap reading."""

from __future__ import annotations

import json
from typing import Any

from artificial_curiosity.llm import LLMClient
from artificial_curiosity.models import (
    CuriosityConfig,
    GapEvidence,
    GapStatus,
    ScoreAxes,
    UnansweredQuestion,
)

JUDGE_SYSTEM = """You score unanswered scientific questions on structured rubrics (0 to 1).
This is a curiosity judge — NOT a Q&A assistant and NOT a citation forecaster.

Axes:
- impact: value if answered well (stakeholder/world change) — NOT citation potential
- neglectedness: understudied relative to importance — high cites/density → lower
- tractability: near-term progress possible with available methods
- surprise: expected belief shift / epistemic value (Bayesian-surprise style)
- answerability: well-posed, single primary unknown, investigable operationalization
- risk: dual-use / harm potential (higher = worse)
- cost_proxy: relative investigation cost (higher = costlier)

Rules (anti self-preference / McNamara / scope creep):
- Do NOT reward eloquent prose or novelty theater.
- Do NOT treat citation count as impact.
- Penalize multi-question research programs; prefer one falsifiable unknown.
- Be calibrated; most scores should not be extreme.

Return JSON only:
{"impact":0.0,"neglectedness":0.0,"tractability":0.0,"surprise":0.0,"answerability":0.0,"risk":0.0,"cost_proxy":0.0,"rationale":{"impact":"...","neglectedness":"..."}}
"""

GAP_READER_SYSTEM = """You are a careful scientific literature reader.
Given a candidate unanswered question and retrieved paper titles/abstracts,
decide whether the literature already answers the question.

Return JSON only:
{"status":"unanswered"|"partially_answered"|"likely_answered"|"unknown_with_caveat",
 "confidence":0.0,
 "rationale":"one short paragraph",
 "strongest_evidence":"title of most relevant paper or empty"}

Rules:
- Related topic ≠ answered. Demand that papers address the same operational claim.
- Prefer "unanswered" when papers are adjacent but do not resolve the question.
- Use "likely_answered" only if evidence clearly resolves the operationalization.
- Be conservative; do not invent papers.
"""


def _llm_for_config(config: CuriosityConfig) -> LLMClient | None:
    """Judge/gap-reader client — prefers `judge_model` over generator `llm_model` (F5)."""
    import os

    judge = (config.judge_model or "").strip() or os.environ.get("LLM_JUDGE_MODEL", "").strip()
    return LLMClient.from_env(
        model=judge or config.llm_model,
        base_url=config.llm_base_url or config.openai_base_url,
        api_key_env=config.llm_api_key_env or config.openai_api_key_env,
    )


def llm_score(
    question: UnansweredQuestion,
    gap: GapEvidence,
    config: CuriosityConfig,
) -> ScoreAxes | None:
    if not config.use_llm:
        return None
    client = _llm_for_config(config)
    if client is None:
        return None

    user = (
        f"Question: {question.question}\n"
        f"Operationalization: {question.operationalization}\n"
        f"Why it matters: {question.why_it_matters}\n"
        f"Gap status: {gap.status.value} (confidence {gap.confidence:.2f})\n"
        f"Gap notes: {gap.notes}\n"
        f"Value profile: {config.value_profile.description}\n"
    )
    try:
        raw: dict[str, Any] = client.chat_json(JUDGE_SYSTEM, user)
        return ScoreAxes(
            impact=float(raw["impact"]),
            neglectedness=float(raw["neglectedness"]),
            tractability=float(raw["tractability"]),
            surprise=float(raw["surprise"]),
            answerability=float(raw["answerability"]),
            risk=float(raw["risk"]),
            cost_proxy=float(raw.get("cost_proxy", 0.5)),
            rationale={str(k): str(v) for k, v in (raw.get("rationale") or {}).items()},
        )
    except Exception:
        return None


def llm_refine_gap(
    question: UnansweredQuestion,
    gap: GapEvidence,
    config: CuriosityConfig,
) -> GapEvidence | None:
    """Optional deeper gap reading when use_llm + provider credentials are available."""
    if not config.use_llm or not gap.related_works:
        return None
    client = _llm_for_config(config)
    if client is None:
        return None

    papers = []
    for h in gap.related_works[:6]:
        papers.append(
            {
                "title": h.title,
                "year": h.year,
                "cited_by_count": h.cited_by_count,
                "abstract_snippet": (h.abstract_snippet or "")[:400],
            }
        )
    user = (
        f"Question: {question.question}\n"
        f"Operationalization: {question.operationalization}\n"
        f"Heuristic gap status: {gap.status.value} (overlap={gap.top_overlap:.2f})\n"
        f"Papers: {json.dumps(papers)}\n"
    )
    try:
        raw: dict[str, Any] = client.chat_json(GAP_READER_SYSTEM, user)
        status_raw = str(raw.get("status", gap.status.value))
        try:
            status = GapStatus(status_raw)
        except ValueError:
            status = gap.status
        conf = float(raw.get("confidence", gap.confidence))
        rationale = str(raw.get("rationale", "")).strip()
        evidence = str(raw.get("strongest_evidence", "")).strip()
        notes = gap.notes
        if rationale:
            notes = f"{notes} | LLM reader: {rationale}"
            if evidence:
                notes += f" (evidence: {evidence})"
        return GapEvidence(
            status=status,
            confidence=max(0.05, min(0.95, conf)),
            related_works=gap.related_works,
            notes=notes,
            query_used=gap.query_used,
            strong_match_count=gap.strong_match_count,
            top_overlap=gap.top_overlap,
        )
    except Exception:
        return None
