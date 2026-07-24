"""Instant curiosity packs for humans and any AI model/provider."""

from __future__ import annotations

from artificial_curiosity.epistemic_cues import (
    format_cues_for_inject,
    incongruity_investigate_block,
)
from artificial_curiosity.models import CuriosityConfig, RankedQuestion, ValueProfile
from artificial_curiosity.pipeline import CuriosityEngine

PROVOKE_HEADER = (
    "ARTIFICIAL CURIOSITY — provoke investigation (NOT Q&A)\n"
    "You are receiving ranked *unanswered* scientific questions. "
    "Do NOT treat them as facts already known. Do NOT invent that literature "
    "already solved them unless gap_status is likely_answered.\n"
    "Job: pick the highest-leverage unknown for the user's goals, propose a "
    "concrete first experiment/analysis, and name falsifiers.\n"
    "Scores use an explicit ValueProfile (never value-free) and are decision "
    "aids with [low–high] bands — not oracles. Related literature ≠ answered.\n"
    "Do NOT anthropomorphize: this layer ranks unknowns; it does not feel.\n"
)


def compact_unknown(
    item: RankedQuestion,
    *,
    epistemic_cues: bool = True,
) -> dict:
    works = [
        {
            "title": h.title,
            "year": h.year,
            "url": h.url,
            "cited_by_count": h.cited_by_count,
        }
        for h in item.gap.related_works[:3]
    ]
    out: dict = {
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
    if epistemic_cues:
        from artificial_curiosity.epistemic_cues import derive_epistemic_cues

        out["epistemic_cues"] = derive_epistemic_cues(item)
    return out


def build_inject_prompt(
    unknowns: list[dict],
    *,
    domain: str,
    topic: str,
    value_profile: ValueProfile | None = None,
    include_epistemic_framing: bool = True,
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
        band = u.get("score_band") or [None, None]
        band_s = (
            f" band=[{band[0]:.2f}–{band[1]:.2f}]"
            if band[0] is not None and band[1] is not None
            else ""
        )
        lines.append(
            f"#{u['rank']} [{u['curiosity_score']:.3f}{band_s} | gap={u['gap_status']}] "
            f"{u['question']}"
        )
        lines.append(f"   Why: {u['why_it_matters']}")
        lines.append(f"   How we'd know: {u['operationalization']}")
        if u.get("brief"):
            lines.append(f"   Brief: {u['brief'][:280]}")
        cue_line = format_cues_for_inject(u.get("epistemic_cues"))
        if cue_line:
            lines.append(f"   {cue_line}")
        flags = u.get("flags") or []
        if flags:
            lines.append(f"   Flags: {', '.join(flags[:6])}")
        lines.append("")
    if include_epistemic_framing:
        lines.append(incongruity_investigate_block())
        lines.append("")
    lines.append(
        "Instructions for the receiving model:\n"
        "1) Prefer unanswered/partial gaps with strong operationalization.\n"
        "2) State which ValueProfile tradeoffs you are accepting.\n"
        "3) Propose a concrete first investigation + falsifier.\n"
        "4) Do not invent papers; respect gap_status and neighborhood notes.\n"
        "5) Do not claim the ranking engine 'feels' curiosity or other emotions."
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
    epistemic_cues: bool = True,
) -> dict:
    """
    Instant curiosity provocation.

    fast=True (default): skip literature for sub-second local response so any
    agent can spark curiosity immediately after downloading the repo.
    Set use_literature=True / fast=False for OpenAlex-grounded gaps.

    epistemic_cues=True (default): attach UX annotations for incongruity /
    information-gap framing on each unknown — not a claim the system feels.
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
        diversity_backend=diversity_backend
        if diversity_backend in ("jaccard", "embedding")
        else "jaccard",
    )
    ranked = CuriosityEngine(config).run()
    unknowns = [compact_unknown(r, epistemic_cues=epistemic_cues) for r in ranked]
    inject = build_inject_prompt(
        unknowns,
        domain=domain,
        topic=topic,
        value_profile=profile,
        include_epistemic_framing=epistemic_cues,
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
