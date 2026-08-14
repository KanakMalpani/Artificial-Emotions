"""Tool implementations. Each returns a JSON-serializable dict."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from artificial_emotions.agent_tools_pkg.schemas import _DOMAIN_ENUM
from artificial_emotions.emotions import (
    annotate_epistemic,
    elicit_helpers,
    emotion_catalog,
    emotion_pack,
    list_epistemic_cues,
    mix_emotions,
)
from artificial_emotions.models import (
    VALUE_PROFILE_PRESETS,
    CuriosityConfig,
    ValueProfile,
    resolve_value_profile,
)
from artificial_emotions.pipeline import CuriosityEngine
from artificial_emotions.provoke import provoke


def _parse_value_profile(
    raw: Any,
    *,
    profile_name: str | None = None,
) -> ValueProfile:
    return resolve_value_profile(raw, profile_name=profile_name)


def handle_provoke_curiosity(
    *,
    domain: str = "ai",
    topic: str = "",
    n: int = 5,
    fast: bool = True,
    use_llm: bool = False,
    value_profile: Any = None,
    profile_name: str | None = None,
    judge_model: str | None = None,
    diversity_backend: str = "jaccard",
    **_extra: Any,
) -> dict[str, Any]:
    """Instant ranked unknowns + inject pack for any model."""
    return provoke(
        domain=domain,
        topic=topic,
        n=int(n),
        fast=bool(fast),
        use_llm=bool(use_llm),
        value_profile=_parse_value_profile(value_profile) if value_profile else None,
        profile_name=profile_name,
        judge_model=judge_model,
        diversity_backend=diversity_backend,
    )


def handle_rank_unknowns(
    *,
    domain: str = "ai",
    topic: str = "",
    n_return: int = 8,
    n_candidates: int = 16,
    use_literature: bool = True,
    literature_backend: str = "openalex",
    use_llm: bool = False,
    value_profile: Any = None,
    profile_name: str | None = None,
    judge_model: str | None = None,
    judge_ensemble_n: int = 1,
    diversity_backend: str = "jaccard",
    **_extra: Any,
) -> dict[str, Any]:
    """Full curiosity pipeline: generate → verify → score → diversify → brief."""
    profile = _parse_value_profile(value_profile, profile_name=profile_name)
    backend = (
        literature_backend
        if literature_backend
        in (
            "openalex",
            "semantic_scholar",
            "both",
        )
        else "openalex"
    )
    config = CuriosityConfig(
        domain=domain,
        topic=topic,
        n_return=int(n_return),
        n_candidates=int(n_candidates),
        use_llm=bool(use_llm),
        use_literature=bool(use_literature),
        literature_backend=backend,
        value_profile=profile,
        judge_model=judge_model,
        judge_ensemble_n=int(judge_ensemble_n or 1),
        diversity_backend=diversity_backend
        if diversity_backend in ("jaccard", "embedding")
        else "jaccard",
    )
    results = CuriosityEngine(config).run_dict()
    return {
        "headline": "What should we investigate next?",
        "capability": (
            "Curiosity layer: ranked unanswered questions — not Q&A, "
            "not lab automation, not value-free ranking."
        ),
        "domain": domain,
        "topic": topic,
        "count": len(results),
        "mode": "literature" if use_literature else "offline",
        "literature_backend": backend if use_literature else "none",
        "value_profile": config.value_profile.model_dump(mode="json"),
        "questions": results,
        "note": (
            "Scores are decision aids with explicit ValueProfile weights — "
            "not oracles. Related literature ≠ answered."
        ),
    }


def handle_list_domains(**_extra: Any) -> dict[str, Any]:
    return {
        "domains": list(_DOMAIN_ENUM),
        "note": "Pass any of these as the `domain` argument to other tools.",
    }


def handle_list_profiles(**_extra: Any) -> dict[str, Any]:
    return {
        "presets": [
            {
                "name": name,
                "description": p.description,
                "time_horizon_years": p.time_horizon_years,
            }
            for name, p in sorted(VALUE_PROFILE_PRESETS.items())
        ],
        "note": (
            "Pass profile_name to provoke_curiosity / rank_unknowns. "
            "There is no value-free / neutral ranking mode."
        ),
    }


def handle_compare_profiles(
    *,
    domain: str = "ai",
    topic: str = "",
    profile_a: str = "humanity_default",
    profile_b: str = "alignment_lab",
    n: int = 8,
    **_extra: Any,
) -> dict[str, Any]:
    """Side-by-side offline ranks under two ValueProfiles."""
    from artificial_emotions.compare import compare_profiles

    return compare_profiles(
        domain=domain or "ai",
        topic=topic or "",
        profile_a=profile_a or "humanity_default",
        profile_b=profile_b or "alignment_lab",
        n=int(n or 8),
    )


def handle_constitution_compare(
    *,
    domain: str = "ai",
    topic: str = "",
    primary_profile: str | None = None,
    veto_profile: str | None = None,
    n: int = 8,
    **_extra: Any,
) -> dict[str, Any]:
    """Constitution stack compare + hard risk veto — no consensus merge."""
    from artificial_emotions.compare import compare_constitution

    return compare_constitution(
        domain=domain or "ai",
        topic=topic or "",
        primary_profile=primary_profile,
        veto_profile=veto_profile,
        n=int(n or 8),
    )


def handle_critique_brief(
    *,
    question: str = "",
    operationalization: str = "",
    brief: str = "",
    why_it_matters: str = "",
    **_extra: Any,
) -> dict[str, Any]:
    """Form-only brief critic — does not change ranks."""
    from artificial_emotions.critique import critique_brief

    return critique_brief(
        question=question or "",
        operationalization=operationalization or "",
        brief=brief or "",
        why_it_matters=why_it_matters or "",
    )


def handle_decompose_question(
    *,
    question: str = "",
    operationalization: str = "",
    domain: str = "ai",
    depth: int = 1,
    answerability: float | None = None,
    tractability: float | None = None,
    risk: float | None = None,
    **_extra: Any,
) -> dict[str, Any]:
    """Expand one unknown into sub-questions, a first step, and stop rules."""
    from artificial_emotions.decompose import decompose_question
    from artificial_emotions.models import UnansweredQuestion

    q = UnansweredQuestion(
        id="decompose-request",
        question=question or "",
        domain=domain or "ai",
        operationalization=operationalization or "",
        why_it_matters="Supplied for decomposition.",
    )
    return decompose_question(
        q,
        depth=int(depth or 1),
        answerability=answerability,
        tractability=tractability,
        risk=risk,
    )


def handle_explore_curiosity(
    *,
    domain: str = "ai",
    topic: str = "",
    steps: int = 5,
    n_return: int = 5,
    profile_name: str | None = None,
    use_literature: bool = False,
    allow_weight_deltas: bool = False,
    somatic_modulate: bool = False,
    allow_domain_jump: bool = True,
    decompose_depth: int = 1,
    persist_memory: Any = None,
    memory_path: Any = None,
    **_extra: Any,
) -> dict[str, Any]:
    """Run the curiosity loop and return the trajectory.

    MCP never persists: ``persist_memory`` / ``memory_path`` are refused even if
    a host passes them. CLI owns the opt-in write path.
    """
    from artificial_emotions.explore import explore

    # Hard refuse — kwargs must not enable disk writes from this surface.
    _ = persist_memory, memory_path, _extra
    return explore(
        domain=domain,
        topic=topic,
        steps=int(steps or 5),
        n_return=int(n_return or 5),
        profile_name=profile_name,
        use_literature=bool(use_literature),
        allow_weight_deltas=bool(allow_weight_deltas),
        somatic_modulate=bool(somatic_modulate),
        allow_domain_jump=bool(allow_domain_jump),
        decompose_depth=int(decompose_depth or 1),
        persist_memory=False,
        memory_path=None,
    )


def handle_cross_model_vote(
    *,
    candidates: list[dict[str, Any]] | None = None,
    judges: int = 1,
    **_extra: Any,
) -> dict[str, Any]:
    """Offline HybridQuestion-style vote proxy — does not re-rank."""
    from artificial_emotions.hybrid_vote import cross_model_vote

    return cross_model_vote(list(candidates or []), judges=int(judges or 1))


def handle_voi_worksheet(
    *,
    question_id: str | None = None,
    question: str = "",
    operationalization: str = "",
    profile_name: str | None = None,
    domain: str = "",
    **_extra: Any,
) -> dict[str, Any]:
    """Fill VOI worksheet metadata — evsi is null, honesty=not_evsi."""
    from artificial_emotions.voi import fill_voi_worksheet

    return fill_voi_worksheet(
        question_id=question_id or None,
        question=question or "",
        operationalization=operationalization or "",
        profile_name=profile_name or None,
        domain=domain or "",
    )


def handle_preference_weight_hints(
    *,
    events: list[dict[str, Any]] | None = None,
    profile_name: str | None = "humanity_default",
    max_delta: float = 0.08,
    apply: bool = False,
    path: Any = None,
    events_path: Any = None,
    **_extra: Any,
) -> dict[str, Any]:
    """Preview (default) or apply tiny ValueProfile weight hints from inline events."""
    from artificial_emotions.preferences import preview_or_apply_weight_hints

    if path is not None or events_path is not None or "preference_learn_path" in _extra:
        return {
            "ok": False,
            "reason": "filesystem_paths_not_accepted",
            "mode": "preview",
            "applied": False,
            "deltas": {},
            "honesty": (
                "Inline events only — filesystem paths are not accepted on MCP. "
                "Weight hints are tiny profile-scoped deltas, not calibrated "
                "learning. Decision aids under an explicit ValueProfile — not oracles."
            ),
        }
    if not events:
        return {
            "ok": False,
            "reason": "need_inline_events",
            "mode": "preview" if not apply else "apply",
            "applied": False,
            "deltas": {},
            "honesty": (
                "Pass inline labeled events with score_axes. "
                "Not calibrated learning. Decision aids under an explicit "
                "ValueProfile — not oracles."
            ),
        }
    return preview_or_apply_weight_hints(
        events,
        profile_name=profile_name,
        max_delta=float(max_delta or 0.08),
        apply=bool(apply),
    )


def handle_list_epistemic_cues(**_extra: Any) -> dict[str, Any]:
    """List epistemic cue tag vocabulary (UX annotations — not felt emotion)."""
    return list_epistemic_cues()


def handle_annotate_epistemic(
    *,
    question: str,
    gap_status: str = "unanswered",
    surprise: float = 0.5,
    neglectedness: float = 0.5,
    answerability: float = 0.5,
    notes: str = "",
    domain: str = "ai",
    **_extra: Any,
) -> dict[str, Any]:
    """Annotate question text with epistemic cue tags."""
    return annotate_epistemic(
        question,
        gap_status=gap_status,
        surprise=float(surprise),
        neglectedness=float(neglectedness),
        answerability=float(answerability),
        notes=notes or "",
        domain=domain,
    )


def handle_emotion_pack(
    *,
    name: str = "affective_science",
    **_extra: Any,
) -> dict[str, Any]:
    """Return affective_science (or named) domain pack seeds."""
    return emotion_pack(name or "affective_science")


def handle_elicit_helpers(**_extra: Any) -> dict[str, Any]:
    """Incongruity → investigation framing + inject helpers."""
    return elicit_helpers()


def handle_emotion_catalog(
    *,
    family: str | None = None,
    **_extra: Any,
) -> dict[str, Any]:
    """Return mixable named-emotion catalog (computational affect simulation)."""
    return emotion_catalog(family=family or None)


def handle_mix_emotions(
    *,
    weights: dict[str, Any] | None = None,
    profile_name: str | None = None,
    mix_intensity_cap: float | None = None,
    simulate_feeling: bool = True,
    **_extra: Any,
) -> dict[str, Any]:
    """Mix catalog emotions by percent/weight; normalize to sum=1.0."""
    if not isinstance(weights, dict) or not weights:
        raise ValueError(
            'weights must be a non-empty object, e.g. {"curiosity": 40, "confusion": 30, "awe": 30}'
        )
    cleaned: dict[str, float] = {}
    for key, val in weights.items():
        cleaned[str(key)] = float(val)
    return mix_emotions(
        cleaned,
        profile_name=profile_name,
        mix_intensity_cap=mix_intensity_cap,
        simulate_feeling=simulate_feeling,
    )


def handle_idea_graph(
    *,
    candidates: list[dict[str, Any]] | None = None,
    similarity_threshold: float = 0.28,
    **_extra: Any,
) -> dict[str, Any]:
    """EIG-inspired idea graph export — display only."""
    from artificial_emotions.idea_graph import export_idea_graph

    return export_idea_graph(
        list(candidates or []),
        similarity_threshold=float(similarity_threshold or 0.28),
    )


def handle_export_unknowns(
    *,
    questions: list[dict[str, Any]] | None = None,
    domain: str = "",
    topic: str = "",
    profile_name: str | None = None,
    literature_backend: str = "none",
    **extra: Any,
) -> dict[str, Any]:
    """Wrap an already-ranked set as a JSON document. No webhook URLs (SSRF)."""
    from artificial_emotions.export_unknowns import (
        DELIVERY_HTTP_BODY,
        export_unknowns,
        reject_webhook_fields,
    )

    reject_webhook_fields(extra)
    return export_unknowns(
        list(questions or []),
        domain=domain,
        topic=topic,
        profile_name=profile_name,
        literature_backend=literature_backend or "none",
        delivery=DELIVERY_HTTP_BODY,
    )


def handle_soundness_pass(
    *,
    candidates: list[dict[str, Any]] | None = None,
    **_extra: Any,
) -> dict[str, Any]:
    """Offline soundness pass — does not re-rank."""
    from artificial_emotions.soundness import soundness_pass

    return soundness_pass(list(candidates or []))


def handle_surprise_worksheet(
    *,
    question_id: str | None = None,
    profile_name: str | None = None,
    predicted_surprise: float | None = None,
    pilot_result: str = "",
    belief_shift_1_to_5: int | None = None,
    crude_update_note: str = "",
    **_extra: Any,
) -> dict[str, Any]:
    """Belief-shift worksheet — not EVSI / not axis rename."""
    from artificial_emotions.bayesian import fill_surprise_worksheet

    return fill_surprise_worksheet(
        question_id=question_id,
        profile_name=profile_name,
        predicted_surprise=predicted_surprise,
        pilot_result=pilot_result or "",
        belief_shift_1_to_5=belief_shift_1_to_5,
        crude_update_note=crude_update_note or "",
    )


# Canonical tool registry: name → (description, schema, handler)
# Aliases (spark / run_curiosity) share handlers with primary names.
ToolHandler = Callable[..., dict[str, Any]]


def handle_list_stances(**_extra: Any) -> dict[str, Any]:
    """List the available stances and what each one is for."""
    from artificial_emotions.stances import list_stances

    return list_stances()


def handle_apply_stance(
    *,
    stance: str,
    domain: str = "ai",
    topic: str = "",
    n_return: int = 6,
    profile_name: str | None = None,
    use_literature: bool = False,
    **_extra: Any,
) -> dict[str, Any]:
    """Rank once, then look at the result through one emotional stance."""
    from artificial_emotions.models import CuriosityConfig, resolve_value_profile
    from artificial_emotions.pipeline import CuriosityEngine
    from artificial_emotions.stances import apply_stance

    items = CuriosityEngine(
        CuriosityConfig(
            domain=domain,
            topic=topic,
            n_return=int(n_return or 6),
            use_llm=False,
            use_literature=bool(use_literature),
            value_profile=resolve_value_profile(profile_name=profile_name),
        )
    ).run()
    return apply_stance(stance, items)


def handle_list_imagination_kinds(**_extra: Any) -> dict[str, Any]:
    """List imagination kinds and which generators are wired."""
    from artificial_emotions.imagine import list_imagination_kinds
    from artificial_emotions.transfer import TRANSFER_SHIP_STATUS

    payload = list_imagination_kinds()
    # Document transfer as corpus_gated — never apply_imagination.
    transfer_entry = next(
        (k for k in payload.get("kinds") or [] if k.get("kind") == "transfer"),
        None,
    )
    if transfer_entry is not None:
        transfer_entry["generator"] = "corpus_gated" if TRANSFER_SHIP_STATUS == "shipped" else "cut"
        transfer_entry["entry"] = "imagine_transfer"
        transfer_entry["not"] = "apply_imagination"
    payload["transfer"] = {
        "generator": "corpus_gated" if TRANSFER_SHIP_STATUS == "shipped" else "cut",
        "ship_status": TRANSFER_SHIP_STATUS,
        "tool": "imagine_transfer",
        "note": (
            "Transfer is corpus_gated: call imagine_transfer with seed + corpus. "
            "Never routed through apply_imagination; never ranked injection. "
            "Decision aid under quarantine — does not feel."
        ),
    }
    return payload


def handle_apply_imagination(
    *,
    kind: str,
    domain: str = "ai",
    topic: str = "",
    n_return: int = 6,
    profile_name: str | None = None,
    use_literature: bool = False,
    **_extra: Any,
) -> dict[str, Any]:
    """Rank once offline, then generate quarantined imagined content."""
    from artificial_emotions.imagine import apply_imagination
    from artificial_emotions.models import CuriosityConfig, resolve_value_profile
    from artificial_emotions.pipeline import CuriosityEngine

    key = (kind or "").strip().lower()
    if key == "transfer":
        return {
            "ok": False,
            "kind": "transfer",
            "refused": True,
            "reason": (
                "transfer is corpus_gated — use imagine_transfer with seed + corpus; "
                "never apply_imagination"
            ),
            "honesty": "imagined_not_retrieved",
            "confidence": None,
            "imagined": [],
            "note": (
                "Decision aid under quarantine — does not feel; not ranked findings. "
                "Related literature ≠ answered."
            ),
        }

    items = CuriosityEngine(
        CuriosityConfig(
            domain=domain,
            topic=topic,
            n_return=int(n_return or 6),
            use_llm=False,
            use_literature=bool(use_literature),
            value_profile=resolve_value_profile(profile_name=profile_name),
        )
    ).run()
    return apply_imagination(kind, items)


def handle_memory_show(
    *,
    path: str | None = None,
    **_extra: Any,
) -> dict[str, Any]:
    """Read-only dump of local memory JSON if present — never creates the file."""
    from artificial_emotions.memory import PersistentMemory, memory_disabled

    if memory_disabled():
        return {
            "disabled": True,
            "reason": "CURIOSITY_NO_MEMORY is set — no read or write",
            "created_file": False,
            "note": (
                "MCP does not persist by default. Annotation continuity — "
                "does not feel; decision aid only."
            ),
        }

    mem = PersistentMemory.load(path or None)
    exists = mem.path.is_file()
    payload = (
        mem.show()
        if exists
        else {
            "present": False,
            "path": str(mem.path),
            "privacy_notice": mem.to_dict()["privacy_notice"],
            "sessions": [],
            "encounters": {},
            "selections": {},
            "scars": [],
            "affinities": [],
            "mood_carryover": mem.mood_carryover.to_dict(),
        }
    )
    payload["present"] = exists
    payload["created_file"] = False
    payload["mcp_persists"] = False
    payload["note"] = (
        "Read-only MCP surface — never creates or writes memory.json. "
        "CLI explore may persist; MCP/HTTP do not by default. "
        "Annotation continuity — does not feel; decision aid only. "
        "Related literature ≠ answered."
    )
    return payload


def handle_memory_forget(
    *,
    what: str = "",
    confirm: bool = False,
    path: str | None = None,
    **_extra: Any,
) -> dict[str, Any]:
    """Explicit forget — requires confirm=true; still no auto-write from explore."""
    from artificial_emotions.memory import PersistentMemory, memory_disabled

    if not confirm:
        return {
            "forgot": False,
            "refused": True,
            "reason": "confirm must be true — destructive ops are explicit only",
            "note": ("MCP does not auto-persist from explore. Decision aid only — does not feel."),
        }
    if memory_disabled():
        return {
            "forgot": False,
            "disabled": True,
            "reason": "CURIOSITY_NO_MEMORY is set — no read or write",
        }

    mem = PersistentMemory.load(path or None)
    result = mem.forget(what or "")
    if result.get("forgot"):
        mem.save()
    result["mcp_persists_default"] = False
    result["note"] = (
        "Explicit forget only. Explore-style MCP tools never auto-write. "
        "Annotation continuity — does not feel; decision aid only."
    )
    return result


def handle_memory_reset(
    *,
    confirm: bool = False,
    path: str | None = None,
    **_extra: Any,
) -> dict[str, Any]:
    """Wipe remembered state + delete file — requires confirm=true."""
    from artificial_emotions.memory import PersistentMemory, memory_disabled

    if not confirm:
        return {
            "reset": False,
            "refused": True,
            "reason": "confirm must be true — destructive ops are explicit only",
            "note": ("MCP does not auto-persist from explore. Decision aid only — does not feel."),
        }
    if memory_disabled():
        return {
            "reset": False,
            "disabled": True,
            "reason": "CURIOSITY_NO_MEMORY is set — no read or write",
        }

    mem = PersistentMemory.load(path or None)
    mem.reset()
    deleted = mem.delete_file()
    return {
        "reset": True,
        "deleted_file": deleted,
        "path": str(mem.path),
        "mcp_persists_default": False,
        "note": (
            "Explicit reset only. Explore-style MCP tools never auto-write. "
            "Annotation continuity — does not feel; decision aid only."
        ),
    }


def handle_memory_avoiding(
    *,
    path: str | None = None,
    min_encounters: int | None = None,
    **_extra: Any,
) -> dict[str, Any]:
    """Surface avoidance patterns from local memory (pattern ≠ motive)."""
    from artificial_emotions.avoidance import avoiding_payload
    from artificial_emotions.memory import PersistentMemory, memory_disabled

    if memory_disabled():
        return {
            "disabled": True,
            "avoiding": [],
            "count": 0,
            "honesty": "pattern_not_motive",
            "reason": "CURIOSITY_NO_MEMORY is set — no read or write",
            "note": ("Pattern ≠ motive. Annotation only — does not feel; decision aid only."),
        }

    mem = PersistentMemory.load(path or None)
    kwargs: dict[str, Any] = {
        "encounters": mem.encounters,
        "selections": mem.selections,
    }
    if min_encounters is not None:
        kwargs["min_encounters"] = int(min_encounters)
    payload = avoiding_payload(**kwargs)
    payload["path"] = str(mem.path)
    payload["created_file"] = False
    payload["mcp_persists"] = False
    return payload


def handle_dream_reanalyze(
    *,
    path: str | None = None,
    **_extra: Any,
) -> dict[str, Any]:
    """Thin wrap of dream.reanalyze_history — offline reanalysis, not a dream."""
    from artificial_emotions.dream import HONESTY_REANALYSIS, reanalyze_history
    from artificial_emotions.memory import memory_disabled

    if memory_disabled():
        return {
            "disabled": True,
            "reason": "CURIOSITY_NO_MEMORY is set — no history to reanalyze",
            "framing": HONESTY_REANALYSIS,
            "honesty": HONESTY_REANALYSIS,
            "confidence": None,
            "note": (
                "Offline reanalysis of stored history — does not feel; "
                "decision aid only. Related literature ≠ answered."
            ),
        }

    return reanalyze_history(path=path or None)


def handle_imagine_transfer(
    *,
    seed: str = "",
    corpus: Any = None,
    max_bridges: int = 4,
    max_links: int = 8,
    **_extra: Any,
) -> dict[str, Any]:
    """Corpus-gated structural transfer — refuse when ship status is not cleared."""
    from artificial_emotions.transfer import (
        TRANSFER_SHIP_STATUS,
        imagine_transfer,
    )

    seed_text = (seed or "").strip()
    if not seed_text:
        return {
            "ok": False,
            "refused": True,
            "reason": "seed is required",
            "kind": "transfer",
            "honesty": "imagined_not_retrieved",
            "confidence": None,
            "imagined": [],
            "note": (
                "Corpus-gated transfer decision aid — does not feel; "
                "never ranked injection. Related literature ≠ answered."
            ),
        }
    if corpus is None or corpus == "" or corpus == []:
        return {
            "ok": False,
            "refused": True,
            "reason": "corpus path or document list is required",
            "kind": "transfer",
            "honesty": "imagined_not_retrieved",
            "confidence": None,
            "imagined": [],
            "ship_status": TRANSFER_SHIP_STATUS,
            "note": (
                "Corpus-gated transfer decision aid — does not feel; "
                "never ranked injection. Related literature ≠ answered."
            ),
        }

    # imagine_transfer itself refuses when TRANSFER_SHIP_STATUS != "shipped".
    payload = imagine_transfer(
        seed_text,
        corpus=corpus,
        max_bridges=int(max_bridges or 4),
        max_links=int(max_links or 8),
    )
    payload.setdefault("generator", "corpus_gated")
    payload.setdefault(
        "note",
        (
            "Imagined structural analogies — not ranked, not confidence-scored. "
            "Does not feel; computational generation under quarantine. "
            "Related literature ≠ answered."
        ),
    )
    return payload
