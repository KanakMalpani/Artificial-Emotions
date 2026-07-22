"""Question generation: seeds + optional LLM expansion."""

from __future__ import annotations

import json
import os
import re
import urllib.request
from typing import Any

from artificial_curiosity.models import CuriosityConfig, Domain, UnansweredQuestion
from artificial_curiosity.seeds import seeds_for


GENERATE_SYSTEM = """You generate valuable UNANSWERED scientific questions.
Rules:
- Each question must be unanswered or only partially answered in the literature.
- Each must be investigable: include operationalization (how we'd know it's answered).
- Prefer high expected impact, neglectedness, and tractability.
- Avoid vague philosophy, pure opinion, or already-solved textbook questions.
- Avoid near-duplicates.
Return JSON: {"questions":[{"question":"...","operationalization":"...","why_it_matters":"...","assumptions":[],"tags":[],"domain":"..."}]}
"""


def _slug(text: str, prefix: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40]
    return f"{prefix}-{s or 'q'}"


class LLMClient:
    def __init__(self, api_key: str, model: str, base_url: str | None = None):
        self.api_key = api_key
        self.model = model
        self.base_url = (base_url or "https://api.openai.com/v1").rstrip("/")

    def chat_json(self, system: str, user: str) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "temperature": 0.7,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=90) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        content = body["choices"][0]["message"]["content"]
        return json.loads(content)


def generate_candidates(config: CuriosityConfig) -> list[UnansweredQuestion]:
    base = seeds_for(
        str(config.domain),
        topic=config.topic,
        limit=config.n_candidates,
    )

    if not config.use_llm:
        return base

    api_key = os.environ.get(config.openai_api_key_env, "")
    if not api_key:
        return base

    client = LLMClient(api_key, config.llm_model, config.openai_base_url)
    user = (
        f"Domain: {config.domain}\n"
        f"Topic focus: {config.topic or 'open'}\n"
        f"Value profile: {config.value_profile.description}\n"
        f"Generate {config.n_candidates} distinct high-value unanswered questions.\n"
        f"Time horizon: {config.value_profile.time_horizon_years} years."
    )
    try:
        raw = client.chat_json(GENERATE_SYSTEM, user)
    except Exception:
        return base

    out: list[UnansweredQuestion] = []
    for i, item in enumerate(raw.get("questions", [])):
        try:
            qtext = item["question"]
            out.append(
                UnansweredQuestion(
                    id=_slug(qtext, f"gen{i}"),
                    question=qtext,
                    domain=item.get("domain") or config.domain or Domain.GENERAL,
                    operationalization=item.get("operationalization")
                    or "Specify measurable success criteria.",
                    why_it_matters=item.get("why_it_matters") or "High expected impact.",
                    assumptions=item.get("assumptions") or [],
                    tags=item.get("tags") or [],
                    source="llm",
                )
            )
        except Exception:
            continue

    # Prefer LLM outputs but keep seeds for diversity if short.
    merged = out + [q for q in base if q.question not in {x.question for x in out}]
    return merged[: max(config.n_candidates, len(out))]
