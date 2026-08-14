"""Pydantic request bodies for the HTTP surface.

Class names are part of the generated OpenAPI (``components.schemas``) — do not
rename them without treating it as a breaking API-doc change.

Two knobs are deliberately absent from every request model: ``llm_base_url``
(SSRF / key leak) and ``literature_cache_dir`` (path injection). Both stay
env/CLI-only.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from artificial_emotions.errors import classify_value_error
from artificial_emotions.models import (
    Domain,
    ValueProfile,
    list_profile_names,
    resolve_value_profile,
)

__all__ = [
    "AnnotateEmotionsRequest",
    "CompareProfilesRequest",
    "ConstitutionCompareRequest",
    "CritiqueBriefRequest",
    "DecomposeRequest",
    "DreamRequest",
    "ExploreRequest",
    "CrossModelVoteRequest",
    "IdeaGraphRequest",
    "MemoryForgetRequest",
    "MemoryIntentRequest",
    "MemoryResetRequest",
    "MixEmotionsRequest",
    "PreferenceHintsRequest",
    "PreferenceSummarizeRequest",
    "ProvokeRequest",
    "RunRequest",
    "SoundnessPassRequest",
    "SuggestPairRequest",
    "SurpriseWorksheetRequest",
    "TransferImaginationRequest",
    "VoiWorksheetRequest",
    "safe_profile",
]


def safe_profile(
    value_profile: ValueProfile | None,
    profile_name: str | None,
) -> ValueProfile:
    """Resolve a profile, converting a bad name into a coded API error."""
    try:
        return resolve_value_profile(value_profile, profile_name=profile_name)
    except ValueError as exc:
        raise classify_value_error(exc) from exc


class RunRequest(BaseModel):
    domain: str = Field(
        Domain.AI.value,
        examples=["ai", "biology", "climate"],
        description="Domain key for seed pool / packs",
    )
    topic: str = Field("", examples=["aging biomarkers", "sandbagging evals"])
    n_return: int = Field(8, ge=1, le=32, examples=[5, 8])
    n_candidates: int = Field(16, ge=4, le=64)
    use_llm: bool = False
    use_literature: bool = True
    literature_backend: str = Field(
        "openalex",
        pattern="^(openalex|semantic_scholar|both)$",
        description="Literature adapter (W11)",
        examples=["openalex", "both"],
    )
    llm_model: str | None = None
    judge_model: str | None = None
    judge_ensemble_n: int = Field(1, ge=1, le=5)
    # llm_base_url / literature_cache_dir are env/CLI-only (SSRF + path injection).
    literature_workers: int = Field(
        4,
        ge=1,
        le=16,
        description="Parallel literature fetches when use_literature=true (1=serial)",
        examples=[1, 4],
    )
    profile_name: str | None = Field(
        None,
        description=f"Named ValueProfile preset: {', '.join(list_profile_names())}",
        examples=["humanity_default", "alignment_lab", "climate_adaptation"],
    )
    value_profile: ValueProfile | None = None
    diversity_backend: str = Field("jaccard", pattern="^(jaccard|embedding)$")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "domain": "ai",
                    "topic": "",
                    "n_return": 8,
                    "n_candidates": 16,
                    "use_llm": False,
                    "use_literature": True,
                    "literature_backend": "openalex",
                    "literature_workers": 4,
                    "profile_name": "alignment_lab",
                    "diversity_backend": "jaccard",
                }
            ]
        }
    }


class ProvokeRequest(BaseModel):
    domain: str = Domain.AI.value
    topic: str = ""
    n: int = Field(5, ge=1, le=16)
    fast: bool = Field(
        True,
        description=(
            "Skip literature for instant local spark (default). Set false for OpenAlex grounding."
        ),
    )
    use_llm: bool = False
    use_literature: bool | None = None
    llm_model: str | None = None
    judge_model: str | None = None
    # llm_base_url is env/CLI-only — never accept client URLs (SSRF / key leak).
    profile_name: str | None = None
    value_profile: ValueProfile | None = None
    diversity_backend: str = Field("jaccard", pattern="^(jaccard|embedding)$")


class PreferenceHintsRequest(BaseModel):
    """Inline preference events → tiny ValueProfile weight hints (no filesystem paths)."""

    events: list[dict[str, Any]] = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Labeled prefer/reject events with score_axes",
        examples=[
            [
                {
                    "event_type": "prefer",
                    "profile_name": "humanity_default",
                    "question_id": "ai-01",
                    "score_axes": {
                        "impact": 0.8,
                        "neglectedness": 0.7,
                        "tractability": 0.4,
                        "surprise": 0.6,
                    },
                },
                {
                    "event_type": "reject",
                    "profile_name": "humanity_default",
                    "question_id": "ai-02",
                    "score_axes": {
                        "impact": 0.4,
                        "neglectedness": 0.3,
                        "tractability": 0.8,
                        "surprise": 0.3,
                    },
                },
            ]
        ],
    )
    profile_name: str | None = Field(
        "humanity_default",
        description=f"Named ValueProfile preset: {', '.join(list_profile_names())}",
    )
    value_profile: ValueProfile | None = None
    max_delta: float = Field(0.08, ge=0.01, le=0.2)
    apply: bool = Field(
        False,
        description=(
            "If true, return applied_profile via apply_weight_hints_to_profile. "
            "Default false (preview). Never overwrites a named preset. "
            "Not calibrated learning. Inline events only — no filesystem paths."
        ),
    )


class PreferenceSummarizeRequest(BaseModel):
    """Inline preference events → counts / pairwise wins / hints (no filesystem paths)."""

    events: list[dict[str, Any]] = Field(..., min_length=1, max_length=2000)
    profile_name: str | None = None
    top_k: int = Field(10, ge=1, le=50)


class CompareProfilesRequest(BaseModel):
    domain: str = Domain.AI.value
    topic: str = ""
    profile_a: str = Field("humanity_default", examples=["humanity_default", "funder_10y"])
    profile_b: str = Field("alignment_lab", examples=["alignment_lab", "climate_adaptation"])
    n: int = Field(8, ge=1, le=32)
    n_candidates: int = Field(16, ge=4, le=64)


class ConstitutionCompareRequest(BaseModel):
    domain: str = Domain.AI.value
    topic: str = ""
    primary_profile: str | None = Field(
        None, description="Override stack primary; default from constitution JSON"
    )
    veto_profile: str | None = Field(
        None,
        description="Override safety veto; default from stack or public_demo_strict_risk",
    )
    n: int = Field(8, ge=1, le=32)
    n_candidates: int = Field(16, ge=4, le=64)


class CritiqueBriefRequest(BaseModel):
    question: str = ""
    operationalization: str = ""
    brief: str = ""
    why_it_matters: str = ""


class DecomposeRequest(BaseModel):
    """Open one unknown into its next layer of questions — never into an answer."""

    question: str = Field(..., min_length=12, examples=["Which biomarkers predict healthspan?"])
    operationalization: str = Field(
        "",
        description="Numeric criteria here (e.g. 'AUROC >= 0.7') are turned into falsifiers.",
        examples=["AUROC >= 0.7 on a held-out cohort."],
    )
    domain: str = Domain.AI.value
    depth: int = Field(
        1,
        ge=1,
        le=3,
        description="1 = one layer of sub-questions; 2-3 also split mechanism and confound.",
    )
    answerability: float | None = Field(None, ge=0.0, le=1.0)
    tractability: float | None = Field(None, ge=0.0, le=1.0)
    risk: float | None = Field(None, ge=0.0, le=1.0)


class VoiWorksheetRequest(BaseModel):
    question_id: str | None = None
    question: str = ""
    operationalization: str = ""
    profile_name: str | None = None
    domain: str = ""


class SuggestPairRequest(BaseModel):
    candidates: list[dict[str, Any]] = Field(
        ...,
        min_length=2,
        description="Top-k ranked unknowns with question_id / rank / curiosity_score",
    )
    events: list[dict[str, Any]] = Field(default_factory=list)
    profile_name: str | None = "humanity_default"


class CrossModelVoteRequest(BaseModel):
    candidates: list[dict[str, Any]] = Field(..., min_length=1)
    judges: int = Field(1, ge=1, le=6)


class AnnotateEmotionsRequest(BaseModel):
    question: str = Field(..., min_length=12)
    gap_status: str = Field(
        "unanswered",
        description="unanswered | partially_answered | likely_answered | unknown_with_caveat",
    )
    surprise: float = Field(0.5, ge=0.0, le=1.0)
    neglectedness: float = Field(0.5, ge=0.0, le=1.0)
    answerability: float = Field(0.5, ge=0.0, le=1.0)
    notes: str = ""
    domain: str = Domain.AI.value


class MixEmotionsRequest(BaseModel):
    """Percentage or weight mix over catalog emotion ids (normalized to sum=1)."""

    weights: dict[str, float] = Field(
        ...,
        description=(
            "Map of emotion_id → percent (e.g. 40) or weight (e.g. 0.4). "
            "Normalized to sum 1.0. Example: "
            '{"curiosity": 40, "confusion": 30, "awe": 30}'
        ),
        min_length=1,
    )
    profile_name: str | None = Field(
        None,
        description="Optional ValueProfile for mix_intensity_cap (e.g. public_demo_strict_risk)",
    )
    mix_intensity_cap: float | None = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Override non-epistemic mix mass cap (None → profile default)",
    )
    simulate_feeling: bool = Field(
        True,
        description="Include felt_simulation (PAD mood, intensity, and computational inner_monologue) in response",
    )

    @field_validator("weights")
    @classmethod
    def _weights_must_be_numeric(cls, v: dict[str, Any]) -> dict[str, float]:
        if not v:
            raise ValueError("weights must contain at least one emotion_id")
        out: dict[str, float] = {}
        for key, val in v.items():
            kid = str(key).strip()
            if not kid:
                raise ValueError("empty emotion id in weights")
            try:
                out[kid] = float(val)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"weight for '{kid}' must be a number, got {val!r}") from exc
        return out


class IdeaGraphRequest(BaseModel):
    candidates: list[dict[str, Any]] = Field(..., min_length=1)
    similarity_threshold: float = Field(0.28, ge=0.0, le=1.0)


class SoundnessPassRequest(BaseModel):
    candidates: list[dict[str, Any]] = Field(..., min_length=1)


class SurpriseWorksheetRequest(BaseModel):
    question_id: str | None = None
    profile_name: str | None = None
    predicted_surprise: float | None = Field(None, ge=0.0, le=1.0)
    pilot_result: str = ""
    belief_shift_1_to_5: int | None = Field(None, ge=1, le=5)
    crude_update_note: str = ""


class ExploreRequest(BaseModel):
    """Run the curiosity loop: appraise, feel, modulate, remember, repeat."""

    domain: str = Domain.AI.value
    topic: str = ""
    steps: int = Field(5, ge=1, le=12, description="Passes to take")
    n_return: int = Field(5, ge=1, le=16, description="Unknowns per step")
    profile_name: str | None = None
    use_literature: bool = False
    allow_weight_deltas: bool = Field(
        False,
        description=(
            "Let affect nudge ValueProfile weights. Bounded and logged; off by "
            "default so ranking stays a pure function of the stated profile."
        ),
    )
    somatic_modulate: bool = Field(
        False,
        description=(
            "Let high-coercion affect (fear, anger, disgust, joy, sadness) change "
            "search knobs. Off by default: those ids still appraise and surface. "
            "Never raises the risk ceiling."
        ),
    )
    allow_domain_jump: bool = Field(True, description="Let boredom change ground")
    decompose_depth: int = Field(1, ge=1, le=3)


class TransferImaginationRequest(BaseModel):
    """Corpus-gated analogical transfer (POST /v1/imagination/transfer)."""

    seed: str = Field(..., min_length=1, examples=["Fish oil"])
    corpus: list[dict[str, Any]] | None = Field(
        None,
        description="Inline corpus documents: [{title, concepts, year?}, ...]",
    )
    corpus_text: str | None = Field(
        None,
        description="JSON text of a document list (alternative to corpus)",
    )
    corpus_path: str | None = Field(
        None,
        description=(
            "Local corpus JSON/JSONL path (trusted/local use). Prefer inline corpus for agents."
        ),
    )
    max_bridges: int = Field(4, ge=1, le=16)
    max_links: int = Field(8, ge=1, le=32)
    cooccurrence_ceiling: int = Field(400, ge=1, le=10_000)


class MemoryIntentRequest(BaseModel):
    """POST body for read-only memory intents that still require explicit POST."""

    path: str | None = Field(
        None,
        description="Optional local memory JSON path (tests / local)",
    )


class MemoryForgetRequest(BaseModel):
    """Explicit forget — confirm=true required."""

    what: str = Field(
        ...,
        min_length=1,
        description=(
            "Session id, question id, scar target, or keyword: "
            "sessions|encounters|selections|mood|scars|affinities"
        ),
    )
    confirm: bool = False
    path: str | None = None


class MemoryResetRequest(BaseModel):
    """Wipe memory + delete file — confirm=true required."""

    confirm: bool = False
    path: str | None = None


class DreamRequest(BaseModel):
    """Explicit offline reanalysis of stored PersistentMemory history."""

    path: str | None = Field(
        None,
        description="Optional local memory JSON path (tests / local)",
    )
