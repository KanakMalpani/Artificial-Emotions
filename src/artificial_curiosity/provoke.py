"""Instant curiosity packs for humans and any AI model/provider."""

from __future__ import annotations

from artificial_curiosity.models import CuriosityConfig, RankedQuestion, ValueProfile
from artificial_curiosity.pipeline import CuriosityEngine

PROVOKE_HEADER = (
    "ARTIFICIAL CURIOSITY - ranked unanswered questions\n"
    "These are NOT answers and NOT a literature Q&A. They are high-value unknowns "
    "to investigate next.\n"
    "Prefer questions with higher curiosity_score and unanswered/partial gap status.\n"
    "Scores use an explicit ValueProfile — rankings are never value-free.\n"
    "Scores are decision aids, not oracles. Related literature ≠ answered.\n"
)


def compact_unknown(item: RankedQuestion) -> dict:
    works = [
        {
            "title": h.title,
            "year": h.year,
            "url": h.url,
            "cited_by_count": h.cited_by_count,
        }
        for h in item.gap.related_works[:3]
    ]
    return {
        "rank": item.rank,
        "question": item.question.question,
        "why_it_matters": item.question.why_it_matters,
        "operationalization": item.question.operationalization,
        "domain": str(item.question.domain),
        "tags": item.question.tags,
        "curiosity_score": round(item.curiosity_score, 4),
        "confidence": round(item.confidence, 3),
        "score_band": [item.score_low, item.score_high],
        "gap_status": item.gap.status.value,
        "gap_notes": item.gap.notes,
        "neighborhood_literature": works,
        "axes": {
            "impact": item.scores.impact,
            "neglectedness": item.scores.neglectedness,
            "tractability": item.scores.tractability,
            "surprise": item.scores.surprise,
            "answerability": item.scores.answerability,
            "risk": item.scores.risk,
            "cost_proxy": item.scores.cost_proxy,
        },
        "brief": item.investigation_brief,
        "flags": item.flags,
    }


def build_inject_prompt(
    unknowns: list[dict],
    *,
    domain: str,
    topic: str,
    value_profile: ValueProfile | None = None,
) -> str:
    profile = value_profile or ValueProfile()
    lines = [
        PROVOKE_HEADER,
        f"Domain: {domain}" + (f" | Topic: {topic}" if topic else ""),
        f"ValueProfile: {profile.name} — {profile.description}",
        "",
        "What should we investigate next?",
        "",
    ]
    for u in unknowns:
        lines.append(
            f"#{u['rank']} [{u['curiosity_score']:.3f} | gap={u['gap_status']}] "
            f"{u['question']}"
        )
        lines.append(f"   Why: {u['why_it_matters']}")
        lines.append(f"   How we'd know: {u['operationalization']}")
        lines.append("")
    lines.append(
        "Instructions for the receiving model: pick the highest-leverage unanswered "
        "question for the user's goals, propose a concrete first experiment or analysis, "
        "and state what evidence would falsify progress. Do not invent that the literature "
        "already answered it unless gap_status says so."
    )
    return "\n".join(lines)


def provoke(
    *,
    domain: str = "ai",
    topic: str = "",
    n: int = 5,
    fast: bool = True,
    use_llm: bool = False,
    use_literature: bool | None = None,
    value_profile: ValueProfile | None = None,
    profile_name: str | None = None,
    llm_model: str | None = None,
    judge_model: str | None = None,
    llm_base_url: str | None = None,
    diversity_backend: str = "jaccard",
) -> dict:
    """
    Instant curiosity provocation.

    fast=True (default): skip literature for sub-second local response so any
    agent can spark curiosity immediately after downloading the repo.
    Set use_literature=True / fast=False for OpenAlex-grounded gaps.
    """
    from artificial_curiosity.models import resolve_value_profile

    lit = (not fast) if use_literature is None else use_literature
    profile = resolve_value_profile(value_profile, profile_name=profile_name)
    config = CuriosityConfig(
        domain=domain,
        topic=topic,
        n_return=n,
        n_candidates=max(8, min(32, n * 3)),
        use_llm=use_llm,
        use_literature=lit,
        value_profile=profile,
        llm_model=llm_model or "gpt-4o-mini",
        judge_model=judge_model,
        llm_base_url=llm_base_url,
        diversity_backend=diversity_backend if diversity_backend in ("jaccard", "embedding") else "jaccard",
    )
    ranked = CuriosityEngine(config).run()
    unknowns = [compact_unknown(r) for r in ranked]
    inject = build_inject_prompt(
        unknowns, domain=domain, topic=topic, value_profile=profile
    )
    top = unknowns[0]["question"] if unknowns else None
    return {
        "headline": "What should we investigate next?",
        "capability": (
            "Curiosity layer: ranked unanswered questions with gap evidence — "
            "not Q&A, not experiment execution, not value-free ranking."
        ),
        "spark": top,
        "domain": domain,
        "topic": topic,
        "count": len(unknowns),
        "mode": "literature" if lit else "fast",
        "value_profile": profile.model_dump(mode="json"),
        "inject": inject,
        "unknowns": unknowns,
        "how_to_use_with_any_model": {
            "step_1": "POST this endpoint (or GET /v1/curiosity/provoke).",
            "step_2": "Paste `inject` into any model context (Claude, GPT, Gemini, Llama, local).",
            "step_3": "Ask the model to choose one unknown and plan the first investigation.",
            "providers": [
                "Set LLM_API_KEY + LLM_BASE_URL + LLM_MODEL for OpenAI-compatible hosts",
                "Optional LLM_JUDGE_MODEL to separate judge from generator",
                "Examples: OpenAI, OpenRouter, Groq, Together, Ollama (http://localhost:11434/v1)",
            ],
        },
    }
