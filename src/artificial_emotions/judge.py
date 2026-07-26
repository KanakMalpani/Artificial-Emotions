"""Optional LLM judge for multi-axis scoring and gap reading."""

from __future__ import annotations

import json
import os
import re
import statistics
from typing import Any

from artificial_emotions.llm import LLMClient
from artificial_emotions.logutil import get_logger
from artificial_emotions.models import (
    CuriosityConfig,
    GapEvidence,
    GapStatus,
    ScoreAxes,
    UnansweredQuestion,
)

logger = get_logger("judge")

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
 "rationale":"one short paragraph that quotes or cites ONLY titles from the provided Papers list",
 "strongest_evidence":"EXACT title of the most relevant paper from Papers, or empty string",
 "evidence_titles":["exact titles from Papers that support your status"]}

Rules:
- Related topic ≠ answered. Demand that papers address the same operational claim.
- Prefer "unanswered" when papers are adjacent but do not resolve the question.
- Use "likely_answered" only if evidence clearly resolves the operationalization.
- Be conservative; do NOT invent papers, DOIs, or titles not in Papers.
- If you cannot ground the claim in provided titles, use status unknown_with_caveat
  and leave strongest_evidence empty.
"""


def _llm_for_config(config: CuriosityConfig, model: str | None = None) -> LLMClient | None:
    """Judge/gap-reader client — prefers `judge_model` over generator `llm_model` (F5)."""
    judge = (model or "").strip()
    if not judge:
        judge = (config.judge_model or "").strip() or os.environ.get("LLM_JUDGE_MODEL", "").strip()
    return LLMClient.from_env(
        model=judge or config.llm_model,
        base_url=config.llm_base_url or config.openai_base_url,
        api_key_env=config.llm_api_key_env or config.openai_api_key_env,
    )


def _parse_axes(raw: dict[str, Any]) -> ScoreAxes:
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


def llm_score(
    question: UnansweredQuestion,
    gap: GapEvidence,
    config: CuriosityConfig,
    *,
    model: str | None = None,
) -> ScoreAxes | None:
    if not config.use_llm:
        return None
    client = _llm_for_config(config, model=model)
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
        return _parse_axes(raw)
    except Exception as exc:  # noqa: BLE001 — optional LLM soft-fail
        logger.warning("LLM judge soft-fail; heuristic scores kept: %s", exc)
        return None


def _ensemble_models(config: CuriosityConfig) -> list[str | None]:
    """Resolve judge model list for multi-judge ensemble (W15)."""
    models: list[str | None] = []
    if config.judge_models:
        models.extend([m.strip() for m in config.judge_models if m and str(m).strip()])
    env_multi = os.environ.get("LLM_JUDGE_MODELS", "").strip()
    if env_multi:
        models.extend([m.strip() for m in env_multi.split(",") if m.strip()])
    primary = (config.judge_model or "").strip() or None
    if primary and primary not in models:
        models.insert(0, primary)
    n = max(1, int(config.judge_ensemble_n or 1))
    if not models:
        # Repeat primary/None n times (same model, multiple samples when client supports it).
        return [None] * n
    # Pad / trim to ensemble size.
    while len(models) < n:
        models.append(models[-1])
    return models[:n]


def mean_axes(scores: list[ScoreAxes]) -> ScoreAxes:
    """Average numeric axes; merge rationales."""
    if len(scores) == 1:
        return scores[0]
    keys = (
        "impact",
        "neglectedness",
        "tractability",
        "surprise",
        "answerability",
        "risk",
        "cost_proxy",
    )
    avg = {k: statistics.fmean(getattr(s, k) for s in scores) for k in keys}
    rationale: dict[str, str] = {"method": "multi_judge_mean"}
    for i, s in enumerate(scores):
        for rk, rv in s.rationale.items():
            rationale[f"j{i}:{rk}"] = rv
    return ScoreAxes(**avg, rationale=rationale)


def disagreement_entropy(scores: list[ScoreAxes]) -> float:
    """
    Normalized disagreement in [0, 1] across judges (W15 / F5 / F8).

    Uses mean pairwise absolute deviation on impact+answerability+risk,
    scaled so ~0.3 axis spread ≈ 1.0 entropy flag threshold territory.
    """
    if len(scores) < 2:
        return 0.0
    dims = []
    for key in ("impact", "answerability", "risk", "neglectedness"):
        vals = [getattr(s, key) for s in scores]
        if len(vals) >= 2:
            dims.append(statistics.pstdev(vals))
    if not dims:
        return 0.0
    # pstdev of axes in [0,1] → map mean stdev to [0,1] with soft saturation.
    raw = statistics.fmean(dims)
    return float(max(0.0, min(1.0, raw / 0.25)))


def llm_score_ensemble(
    question: UnansweredQuestion,
    gap: GapEvidence,
    config: CuriosityConfig,
) -> tuple[ScoreAxes | None, list[ScoreAxes], float]:
    """
    Run one or more judges; return (aggregate, members, disagreement_entropy).

    Aggregate is None when no judge succeeds.
    """
    if not config.use_llm:
        return None, [], 0.0
    members: list[ScoreAxes] = []
    for model in _ensemble_models(config):
        axes = llm_score(question, gap, config, model=model)
        if axes is not None:
            members.append(axes)
    if not members:
        return None, [], 0.0
    entropy = disagreement_entropy(members)
    return mean_axes(members), members, entropy


def _norm_title(t: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", " ", (t or "").lower())).strip()


def evidence_titles_grounded(
    claimed: list[str],
    related_titles: list[str],
    *,
    min_overlap: float = 0.55,
) -> tuple[bool, list[str]]:
    """
    Check that claimed evidence titles match retrieved papers (W12 / F7).

    Returns (ok, unmatched_claims). Empty claimed list → not grounded.
    """
    if not claimed:
        return False, []
    norms = [_norm_title(t) for t in related_titles if t]
    unmatched: list[str] = []
    for c in claimed:
        cn = _norm_title(c)
        if not cn:
            unmatched.append(c)
            continue
        ok = False
        for nt in norms:
            if not nt:
                continue
            if cn == nt or cn in nt or nt in cn:
                ok = True
                break
            # Token Jaccard fallback for light punctuation drift.
            ta, tb = set(cn.split()), set(nt.split())
            if ta and tb and len(ta & tb) / len(ta | tb) >= min_overlap:
                ok = True
                break
        if not ok:
            unmatched.append(c)
    return (len(unmatched) == 0), unmatched


def validate_gap_reader_grounding(
    raw: dict[str, Any],
    related_titles: list[str],
) -> tuple[bool, str]:
    """
    Enforce evidence-required gap reading. Reject inventing papers.

    Returns (grounded, reason).
    """
    strongest = str(raw.get("strongest_evidence") or "").strip()
    evidence_titles = raw.get("evidence_titles") or []
    if isinstance(evidence_titles, str):
        evidence_titles = [evidence_titles]
    claimed = [str(x).strip() for x in evidence_titles if str(x).strip()]
    if strongest:
        claimed = list(dict.fromkeys([strongest] + claimed))

    status_raw = str(raw.get("status", "")).strip()
    # unknown_with_caveat may omit evidence.
    if status_raw == GapStatus.UNKNOWN_WITH_CAVEAT.value and not claimed:
        return True, "unknown_without_evidence_ok"

    if not claimed:
        return False, "missing_evidence_titles"

    ok, unmatched = evidence_titles_grounded(claimed, related_titles)
    if not ok:
        return False, f"ungrounded_titles:{unmatched[:3]}"
    return True, "grounded"


def llm_refine_gap(
    question: UnansweredQuestion,
    gap: GapEvidence,
    config: CuriosityConfig,
) -> GapEvidence | None:
    """Optional deeper gap reading when use_llm + provider credentials are available.

    W12: rejects ungrounded claims (invented paper titles) and falls back to heuristic gap.
    """
    if not config.use_llm or not gap.related_works:
        return None
    client = _llm_for_config(config)
    if client is None:
        return None

    papers = []
    related_titles: list[str] = []
    for h in gap.related_works[:6]:
        related_titles.append(h.title)
        papers.append(
            {
                "title": h.title,
                "year": h.year,
                "cited_by_count": h.cited_by_count,
                "abstract_snippet": (h.abstract_snippet or "")[:400],
                "source": h.source,
            }
        )
    user = (
        f"Question: {question.question}\n"
        f"Operationalization: {question.operationalization}\n"
        f"Heuristic gap status: {gap.status.value} (overlap={gap.top_overlap:.2f})\n"
        f"Papers: {json.dumps(papers)}\n"
        "Remember: strongest_evidence and evidence_titles MUST be exact titles from Papers.\n"
    )
    try:
        raw: dict[str, Any] = client.chat_json(GAP_READER_SYSTEM, user)
        grounded, reason = validate_gap_reader_grounding(raw, related_titles)
        if not grounded:
            # Soft-fail: keep heuristic gap; annotate rejection (do not invent).
            return GapEvidence(
                status=gap.status,
                confidence=max(0.05, gap.confidence * 0.95),
                related_works=gap.related_works,
                notes=(
                    f"{gap.notes} | LLM reader REJECTED (ungrounded: {reason}). "
                    "Kept heuristic gap; no invented papers."
                ),
                query_used=gap.query_used,
                strong_match_count=gap.strong_match_count,
                top_overlap=gap.top_overlap,
                llm_grounded=False,
                literature_backend=gap.literature_backend,
            )

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
            llm_grounded=True,
            literature_backend=gap.literature_backend,
        )
    except Exception as exc:  # noqa: BLE001 — optional LLM gap reader soft-fail
        logger.warning("LLM gap reader soft-fail; keeping heuristic gap: %s", exc)
        return None
