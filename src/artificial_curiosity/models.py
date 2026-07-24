"""Core data models for the curiosity layer."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class GapStatus(str, Enum):
    UNANSWERED = "unanswered"
    PARTIALLY_ANSWERED = "partially_answered"
    LIKELY_ANSWERED = "likely_answered"
    UNKNOWN_WITH_CAVEAT = "unknown_with_caveat"


class Domain(str, Enum):
    BIOLOGY = "biology"
    PHYSICS = "physics"
    AI = "ai"
    CLIMATE = "climate"
    MEDICINE = "medicine"
    MATERIALS = "materials"
    SOCIAL = "social"
    ENERGY = "energy"
    GENERAL = "general"


class ValueProfile(BaseModel):
    """Explicit stakeholder values — there is no value-free ranking."""

    name: str = "humanity_default"
    description: str = (
        "Prefer questions whose answers reduce suffering, expand reliable knowledge, "
        "or unlock many downstream investigations."
    )
    weight_impact: float = Field(1.0, ge=0.0, le=3.0)
    weight_neglectedness: float = Field(1.0, ge=0.0, le=3.0)
    weight_tractability: float = Field(0.85, ge=0.0, le=3.0)
    weight_surprise: float = Field(0.75, ge=0.0, le=3.0)
    max_risk: float = Field(0.85, ge=0.0, le=1.0)
    min_answerability: float = Field(0.45, ge=0.0, le=1.0)
    prefer_interdisciplinary: bool = True
    time_horizon_years: int = Field(10, ge=1, le=100)


# Named presets — never a "neutral / value-free" mode (F11).
VALUE_PROFILE_PRESETS: dict[str, ValueProfile] = {
    "humanity_default": ValueProfile(),
    "funder_10y": ValueProfile(
        name="funder_10y",
        description=(
            "Prefer tractable, high-impact unknowns with clear operationalization "
            "within a ~10-year funding horizon."
        ),
        weight_impact=1.2,
        weight_neglectedness=0.9,
        weight_tractability=1.3,
        weight_surprise=0.6,
        time_horizon_years=10,
        min_answerability=0.5,
    ),
    "alignment_lab": ValueProfile(
        name="alignment_lab",
        description=(
            "Prefer neglected alignment / control unknowns with strong operationalization "
            "and strict dual-use risk ceiling."
        ),
        weight_impact=1.1,
        weight_neglectedness=1.3,
        weight_tractability=1.0,
        weight_surprise=0.9,
        max_risk=0.7,
        min_answerability=0.5,
        time_horizon_years=15,
    ),
    "climate_adaptation": ValueProfile(
        name="climate_adaptation",
        description=(
            "Prefer climate adaptation / resilience unknowns that unlock downstream "
            "mitigation or adaptation decisions."
        ),
        weight_impact=1.3,
        weight_neglectedness=1.1,
        weight_tractability=1.0,
        weight_surprise=0.7,
        time_horizon_years=20,
    ),
    "basic_science": ValueProfile(
        name="basic_science",
        description=(
            "Prefer surprising, understudied fundamental unknowns even when near-term "
            "applications are unclear."
        ),
        weight_impact=0.8,
        weight_neglectedness=1.2,
        weight_tractability=0.7,
        weight_surprise=1.4,
        time_horizon_years=30,
    ),
    "near_term_ops": ValueProfile(
        name="near_term_ops",
        description=(
            "Prefer answerable, low-cost unknowns that can inform operations within 1–3 years."
        ),
        weight_impact=0.9,
        weight_neglectedness=0.7,
        weight_tractability=1.5,
        weight_surprise=0.5,
        min_answerability=0.55,
        time_horizon_years=3,
    ),
    "public_demo_strict_risk": ValueProfile(
        name="public_demo_strict_risk",
        description=(
            "Public / demo surface with a strict dual-use risk ceiling — use as a "
            "safety veto stakeholder when composing with a primary lab or funder profile."
        ),
        weight_impact=1.0,
        weight_neglectedness=1.0,
        weight_tractability=0.9,
        weight_surprise=0.6,
        max_risk=0.55,
        min_answerability=0.5,
        time_horizon_years=10,
    ),
}


def list_profile_names() -> list[str]:
    return sorted(VALUE_PROFILE_PRESETS.keys())


def get_profile(name: str | None = None) -> ValueProfile:
    """Resolve a named preset. Unknown names raise ValueError (no silent laundering)."""
    if not name or not str(name).strip():
        return ValueProfile()
    key = str(name).strip().lower()
    if key not in VALUE_PROFILE_PRESETS:
        known = ", ".join(list_profile_names())
        raise ValueError(f"Unknown ValueProfile preset '{name}'. Known: {known}")
    # Return a copy so callers can mutate safely.
    return VALUE_PROFILE_PRESETS[key].model_copy(deep=True)


def resolve_value_profile(
    profile: ValueProfile | dict[str, Any] | None = None,
    *,
    profile_name: str | None = None,
) -> ValueProfile:
    """Prefer explicit profile object; else named preset; else humanity_default."""
    if isinstance(profile, ValueProfile):
        return profile
    if isinstance(profile, dict):
        return ValueProfile.model_validate(profile)
    if profile_name:
        return get_profile(profile_name)
    return ValueProfile()


class ScoreAxes(BaseModel):
    impact: float = Field(..., ge=0.0, le=1.0)
    neglectedness: float = Field(..., ge=0.0, le=1.0)
    tractability: float = Field(..., ge=0.0, le=1.0)
    surprise: float = Field(..., ge=0.0, le=1.0)
    answerability: float = Field(..., ge=0.0, le=1.0)
    risk: float = Field(..., ge=0.0, le=1.0)
    cost_proxy: float = Field(0.5, ge=0.0, le=1.0)

    rationale: dict[str, str] = Field(default_factory=dict)


class LiteratureHit(BaseModel):
    title: str
    year: int | None = None
    doi: str | None = None
    openalex_id: str | None = None
    cited_by_count: int | None = None
    abstract_snippet: str | None = None
    url: str | None = None
    # Multi-backend provenance (openalex | semantic_scholar | fixture | …)
    source: str | None = None
    source_id: str | None = None
    # OpenAlex grants/funder metadata presence (rationale key only — often missing).
    has_funder: bool | None = None


class GapEvidence(BaseModel):
    status: GapStatus
    confidence: float = Field(..., ge=0.0, le=1.0)
    related_works: list[LiteratureHit] = Field(default_factory=list)
    notes: str = ""
    query_used: str = ""
    strong_match_count: int = 0
    top_overlap: float = 0.0
    # Set when LLM gap reader was grounded on retrieved titles only (W12).
    llm_grounded: bool | None = None
    literature_backend: str | None = None


class UnansweredQuestion(BaseModel):
    id: str
    question: str
    domain: Domain | str
    operationalization: str = Field(
        ...,
        description="How one would know the question was answered.",
    )
    why_it_matters: str
    assumptions: list[str] = Field(default_factory=list)
    enabling_questions: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    source: str = "generated"

    @field_validator("question")
    @classmethod
    def must_be_question(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 12:
            raise ValueError("question too short")
        return v


class RankedQuestion(BaseModel):
    question: UnansweredQuestion
    scores: ScoreAxes
    curiosity_score: float
    confidence: float
    gap: GapEvidence
    rank: int | None = None
    investigation_brief: str = ""
    flags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    # Soft calibration band (F8): not a true CI — evidence-strength envelope.
    score_low: float | None = None
    score_high: float | None = None


class CuriosityConfig(BaseModel):
    domain: Domain | str = Domain.GENERAL
    topic: str = ""
    n_candidates: int = Field(16, ge=4, le=64)
    n_return: int = Field(8, ge=1, le=32)
    value_profile: ValueProfile = Field(default_factory=ValueProfile)
    use_llm: bool = False
    use_literature: bool = True
    literature_timeout_s: float = 12.0
    # openalex (default) | semantic_scholar | both
    literature_backend: str = Field(
        "openalex",
        pattern="^(openalex|semantic_scholar|s2|both|merge|multi)$",
    )
    # Opt-in disk cache for literature responses (rate-limit softener).
    literature_cache_dir: str | None = None
    literature_cache_ttl_s: float = 86_400.0
    # Parallel OpenAlex/S2 fetches when literature is on (1 = serial).
    literature_workers: int = Field(4, ge=1, le=16)
    diversity_threshold: float = Field(0.82, ge=0.5, le=0.99)
    # "jaccard" (default, offline) | "embedding" (optional extras; falls back if missing)
    diversity_backend: str = Field("jaccard", pattern="^(jaccard|embedding)$")
    seed: int = 42
    llm_model: str = "gpt-4o-mini"
    # Separate judge/gap-reader model when set (F5). Falls back to llm_model / env.
    judge_model: str | None = None
    # Multi-judge ensemble size (W15). 1 = single judge; >1 runs extra passes.
    judge_ensemble_n: int = Field(1, ge=1, le=5)
    # Optional extra judge model ids (comma-separated env LLM_JUDGE_MODELS also honored).
    judge_models: list[str] = Field(default_factory=list)
    # Provider-agnostic (preferred). Any OpenAI-compatible /chat/completions host.
    llm_base_url: str | None = None
    llm_api_key_env: str = "LLM_API_KEY"
    # Backward-compatible aliases (still honored).
    openai_base_url: str | None = None
    openai_api_key_env: str = "OPENAI_API_KEY"
    # Opt-in preference / feedback JSONL path (W13).
    preference_log_path: str | None = None
    # Optional path of *labeled* prefer/reject events used for thin re-rank (not learning weights).
    preference_rerank_path: str | None = None
    # Optional labeled JSONL for tiny ValueProfile weight hints (CLI/config only).
    preference_learn_path: str | None = None
    # Optional versioned domain pack JSON paths (WO-0.3.6).
    domain_pack_paths: list[str] = Field(default_factory=list)
    # Include packaged example packs under artificial_curiosity/packs/.
    load_bundled_packs: bool = False
