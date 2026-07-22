"""Optional LLM judge for multi-axis scoring."""

from __future__ import annotations

import json
import os
from typing import Any

from artificial_curiosity.generate import LLMClient
from artificial_curiosity.models import (
    CuriosityConfig,
    GapEvidence,
    ScoreAxes,
    UnansweredQuestion,
)

JUDGE_SYSTEM = """You score unanswered scientific questions on six axes from 0 to 1.
Axes:
- impact: value if answered well
- neglectedness: understudied relative to importance
- tractability: near-term progress possible
- surprise: expected belief shift / epistemic value
- answerability: well-posed and investigable
- risk: dual-use / harm potential (higher = worse)
- cost_proxy: relative investigation cost (higher = costlier)

Return JSON only:
{"impact":0.0,"neglectedness":0.0,"tractability":0.0,"surprise":0.0,"answerability":0.0,"risk":0.0,"cost_proxy":0.0,"rationale":{"impact":"...","neglectedness":"..."}}
Be calibrated. Most scores should not be extreme.
"""


def llm_score(
    question: UnansweredQuestion,
    gap: GapEvidence,
    config: CuriosityConfig,
) -> ScoreAxes | None:
    api_key = os.environ.get(config.openai_api_key_env, "")
    if not api_key or not config.use_llm:
        return None

    client = LLMClient(api_key, config.llm_model, config.openai_base_url)
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
