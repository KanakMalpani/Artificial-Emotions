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


class GapEvidence(BaseModel):
    status: GapStatus
    confidence: float = Field(..., ge=0.0, le=1.0)
    related_works: list[LiteratureHit] = Field(default_factory=list)
    notes: str = ""
    query_used: str = ""
    strong_match_count: int = 0
    top_overlap: float = 0.0


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


class CuriosityConfig(BaseModel):
    domain: Domain | str = Domain.GENERAL
    topic: str = ""
    n_candidates: int = Field(16, ge=4, le=64)
    n_return: int = Field(8, ge=1, le=32)
    value_profile: ValueProfile = Field(default_factory=ValueProfile)
    use_llm: bool = False
    use_literature: bool = True
    literature_timeout_s: float = 12.0
    diversity_threshold: float = Field(0.82, ge=0.5, le=0.99)
    seed: int = 42
    llm_model: str = "gpt-4o-mini"
    openai_base_url: str | None = None
    openai_api_key_env: str = "OPENAI_API_KEY"
