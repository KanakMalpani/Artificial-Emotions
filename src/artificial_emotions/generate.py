"""Question generation: seeds + optional LLM expansion."""

from __future__ import annotations

import re

from artificial_emotions.llm import LLMClient
from artificial_emotions.logutil import get_logger
from artificial_emotions.models import CuriosityConfig, Domain, UnansweredQuestion
from artificial_emotions.seeds import seeds_for

logger = get_logger("generate")


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


def _llm_for_config(config: CuriosityConfig) -> LLMClient | None:
    return LLMClient.from_env(
        model=config.llm_model,
        base_url=config.llm_base_url or config.openai_base_url,
        api_key_env=config.llm_api_key_env or config.openai_api_key_env,
    )


def generate_candidates(config: CuriosityConfig) -> list[UnansweredQuestion]:
    base = seeds_for(
        str(config.domain),
        topic=config.topic,
        limit=config.n_candidates,
    )

    # Optional versioned domain packs (WO-0.3.6).
    if config.domain_pack_paths or config.load_bundled_packs:
        from artificial_emotions.packs import default_packs_dir, load_domain_packs

        pack_qs = load_domain_packs(
            list(config.domain_pack_paths) or None,
            packs_dir=default_packs_dir() if config.load_bundled_packs else None,
        )
        domain_key = str(config.domain).lower()
        for pq in pack_qs:
            if domain_key in ("general", str(Domain.GENERAL.value)) or str(pq.domain).lower() in (
                domain_key,
                "general",
            ):
                base.append(pq)
        # De-dupe by question text, keep order.
        seen: set[str] = set()
        deduped: list[UnansweredQuestion] = []
        for q in base:
            key = q.question.strip().lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(q)
        base = deduped[: max(config.n_candidates, len(deduped))]

    if not config.use_llm:
        return base[: config.n_candidates] if len(base) > config.n_candidates else base

    client = _llm_for_config(config)
    if client is None:
        return base[: config.n_candidates]

    user = (
        f"Domain: {config.domain}\n"
        f"Topic focus: {config.topic or 'open'}\n"
        f"Value profile: {config.value_profile.description}\n"
        f"Generate {config.n_candidates} distinct high-value unanswered questions.\n"
        f"Time horizon: {config.value_profile.time_horizon_years} years."
    )
    try:
        raw = client.chat_json(GENERATE_SYSTEM, user)
    except Exception as exc:  # noqa: BLE001 — optional LLM soft-fail
        logger.warning("LLM generate soft-fail; using seeds only: %s", exc)
        return base[: config.n_candidates]

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
        except Exception as exc:  # noqa: BLE001 — skip malformed item
            logger.warning("Skipping malformed LLM question item: %s", exc)
            continue
    return (out + base)[: config.n_candidates] if out else base[: config.n_candidates]
