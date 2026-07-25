"""Judge / gap-reader behaviour with a stubbed LLM client — no network, no key.

The safety-relevant contract here is that the LLM is always *optional*: every
failure mode (no client, bad JSON, malformed axes, ungrounded citations) must
degrade to the heuristic result rather than raise or invent evidence.
"""

from __future__ import annotations

from typing import Any

import pytest

import artificial_curiosity.judge as judge_mod
from artificial_curiosity.judge import (
    ScoreAxes,
    _ensemble_models,
    _parse_axes,
    disagreement_entropy,
    llm_refine_gap,
    llm_score,
    llm_score_ensemble,
    mean_axes,
)
from artificial_curiosity.models import (
    CuriosityConfig,
    GapEvidence,
    GapStatus,
    LiteratureHit,
    UnansweredQuestion,
)

_AXES = {
    "impact": 0.8,
    "neglectedness": 0.6,
    "tractability": 0.5,
    "surprise": 0.4,
    "answerability": 0.7,
    "risk": 0.2,
}


def _question() -> UnansweredQuestion:
    return UnansweredQuestion(
        id="q-1",
        question="Which biomarkers predict remaining healthspan under caloric restriction?",
        domain="biology",
        operationalization="AUROC >= 0.7 on a held-out cohort.",
        why_it_matters="Aging interventions need surrogate endpoints.",
    )


def _gap(**kwargs: Any) -> GapEvidence:
    base: dict[str, Any] = {
        "status": GapStatus.UNANSWERED,
        "confidence": 0.4,
        "notes": "heuristic gap",
        "top_overlap": 0.3,
        "strong_match_count": 0,
        "literature_backend": "openalex",
    }
    base.update(kwargs)
    return GapEvidence(**base)


def _config(**kwargs: Any) -> CuriosityConfig:
    base: dict[str, Any] = {"domain": "biology", "use_llm": True, "use_literature": False}
    base.update(kwargs)
    return CuriosityConfig(**base)


class _StubClient:
    """Stands in for LLMClient; records prompts and returns canned JSON."""

    def __init__(self, response: Any):
        self.response = response
        self.calls: list[tuple[str, str]] = []

    def chat_json(self, system: str, user: str) -> dict[str, Any]:
        self.calls.append((system, user))
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def _use_client(monkeypatch, client):
    monkeypatch.setattr(judge_mod, "_llm_for_config", lambda _cfg, model=None: client)


# --- axis parsing -------------------------------------------------------------------


def test_parse_axes_reads_all_six_axes():
    axes = _parse_axes({**_AXES, "rationale": {"impact": "large cohort effect"}})
    assert axes.impact == 0.8
    assert axes.risk == 0.2
    assert axes.cost_proxy == 0.5  # default when the model omits it
    assert axes.rationale["impact"] == "large cohort effect"


def test_parse_axes_coerces_numeric_strings():
    axes = _parse_axes({k: str(v) for k, v in _AXES.items()})
    assert axes.impact == 0.8


def test_parse_axes_rejects_a_missing_axis():
    incomplete = {k: v for k, v in _AXES.items() if k != "risk"}
    with pytest.raises(KeyError):
        _parse_axes(incomplete)


# --- llm_score soft-fail contract ---------------------------------------------------


def test_llm_score_is_skipped_when_llm_is_off():
    assert llm_score(_question(), _gap(), _config(use_llm=False)) is None


def test_llm_score_returns_none_without_a_client(monkeypatch):
    _use_client(monkeypatch, None)
    assert llm_score(_question(), _gap(), _config()) is None


def test_llm_score_parses_a_well_formed_response(monkeypatch):
    client = _StubClient(_AXES)
    _use_client(monkeypatch, client)
    axes = llm_score(_question(), _gap(), _config())
    assert axes is not None
    assert axes.impact == 0.8
    # The judge must see the question and the gap status it is scoring against.
    _system, user = client.calls[0]
    assert "healthspan" in user
    assert "unanswered" in user


@pytest.mark.parametrize(
    "response",
    [
        {"impact": 0.5},  # missing axes
        {**_AXES, "impact": "not-a-number"},  # uncoercible
        RuntimeError("provider 500"),  # transport failure
        ValueError("No JSON object in model response"),
    ],
)
def test_llm_score_soft_fails_to_none(monkeypatch, response):
    _use_client(monkeypatch, _StubClient(response))
    assert llm_score(_question(), _gap(), _config()) is None


# --- ensemble -----------------------------------------------------------------------


def test_ensemble_is_skipped_when_llm_is_off():
    assert llm_score_ensemble(_question(), _gap(), _config(use_llm=False)) == (None, [], 0.0)


def test_ensemble_averages_successful_members(monkeypatch):
    _use_client(monkeypatch, _StubClient(_AXES))
    aggregate, members, entropy = llm_score_ensemble(
        _question(), _gap(), _config(judge_ensemble_n=3)
    )
    assert aggregate is not None
    assert len(members) == 3
    assert entropy == pytest.approx(0.0)  # identical judges never disagree


def test_ensemble_returns_nothing_when_every_judge_fails(monkeypatch):
    _use_client(monkeypatch, _StubClient(RuntimeError("down")))
    assert llm_score_ensemble(_question(), _gap(), _config(judge_ensemble_n=3)) == (None, [], 0.0)


def test_ensemble_model_list_pads_to_the_requested_size():
    models = _ensemble_models(_config(judge_model="a", judge_ensemble_n=3))
    assert len(models) == 3
    assert models[0] == "a"


def test_ensemble_model_list_trims_to_the_requested_size():
    models = _ensemble_models(_config(judge_models=["a", "b", "c", "d"], judge_ensemble_n=2))
    assert len(models) == 2


def test_ensemble_model_list_reads_the_env_var(monkeypatch):
    monkeypatch.setenv("LLM_JUDGE_MODELS", "env-a, env-b")
    models = _ensemble_models(_config(judge_ensemble_n=2))
    assert "env-a" in models and "env-b" in models


def test_disagreement_entropy_rises_with_spread():
    tight = [ScoreAxes(**_AXES), ScoreAxes(**_AXES)]
    wide = [
        ScoreAxes(**{**_AXES, "impact": 0.05}),
        ScoreAxes(**{**_AXES, "impact": 0.95}),
    ]
    assert disagreement_entropy(wide) > disagreement_entropy(tight)


def test_mean_axes_averages_each_axis():
    averaged = mean_axes(
        [ScoreAxes(**{**_AXES, "impact": 0.2}), ScoreAxes(**{**_AXES, "impact": 0.8})]
    )
    assert averaged.impact == pytest.approx(0.5)


# --- gap reader grounding -----------------------------------------------------------


def _gap_with_papers() -> GapEvidence:
    return _gap(
        related_works=[
            LiteratureHit(title="Caloric restriction and epigenetic clocks", year=2023),
            LiteratureHit(title="Proteomic aging signatures in humans", year=2024),
        ]
    )


def test_gap_reader_is_skipped_without_related_works():
    assert llm_refine_gap(_question(), _gap(related_works=[]), _config()) is None


def test_gap_reader_is_skipped_when_llm_is_off():
    assert llm_refine_gap(_question(), _gap_with_papers(), _config(use_llm=False)) is None


def test_gap_reader_accepts_a_grounded_verdict(monkeypatch):
    _use_client(
        monkeypatch,
        _StubClient(
            {
                "status": "likely_answered",
                "confidence": 0.8,
                "rationale": "Direct replication exists.",
                "strongest_evidence": "Caloric restriction and epigenetic clocks",
                "evidence_titles": ["Caloric restriction and epigenetic clocks"],
            }
        ),
    )
    refined = llm_refine_gap(_question(), _gap_with_papers(), _config())
    assert refined is not None
    assert refined.llm_grounded is True
    assert refined.status == GapStatus.LIKELY_ANSWERED
    assert "LLM reader" in refined.notes


def test_gap_reader_rejects_invented_citations_and_keeps_the_heuristic(monkeypatch):
    """The core anti-hallucination guard: an unmatched title must not change the verdict."""
    original = _gap_with_papers()
    _use_client(
        monkeypatch,
        _StubClient(
            {
                "status": "likely_answered",
                "confidence": 0.95,
                "strongest_evidence": "A Nature paper that does not exist",
                "evidence_titles": ["A Nature paper that does not exist"],
            }
        ),
    )
    refined = llm_refine_gap(_question(), original, _config())
    assert refined is not None
    assert refined.llm_grounded is False
    assert refined.status == original.status  # verdict unchanged
    assert refined.confidence <= original.confidence
    assert "REJECTED" in refined.notes
    # The unmatched title may be named as the *reason*, but must never be
    # presented as accepted evidence (the grounded path formats "(evidence: …)").
    assert "(evidence:" not in refined.notes


def test_gap_reader_falls_back_on_an_unknown_status(monkeypatch):
    original = _gap_with_papers()
    _use_client(
        monkeypatch,
        _StubClient(
            {
                "status": "totally_made_up_status",
                "confidence": 0.7,
                "strongest_evidence": "",
                "evidence_titles": [],
            }
        ),
    )
    refined = llm_refine_gap(_question(), original, _config())
    assert refined is not None
    assert refined.status == original.status


def test_gap_reader_clamps_confidence_into_range(monkeypatch):
    _use_client(
        monkeypatch,
        _StubClient(
            {
                "status": "unanswered",
                "confidence": 99.0,
                "strongest_evidence": "",
                "evidence_titles": [],
            }
        ),
    )
    refined = llm_refine_gap(_question(), _gap_with_papers(), _config())
    assert refined is not None
    assert 0.05 <= refined.confidence <= 0.95


def test_gap_reader_soft_fails_when_the_provider_errors(monkeypatch):
    _use_client(monkeypatch, _StubClient(RuntimeError("provider down")))
    assert llm_refine_gap(_question(), _gap_with_papers(), _config()) is None


def test_gap_reader_sends_only_a_bounded_number_of_papers(monkeypatch):
    client = _StubClient({"status": "unanswered", "strongest_evidence": "", "evidence_titles": []})
    _use_client(monkeypatch, client)
    many = _gap(
        related_works=[LiteratureHit(title=f"Paper {i}", year=2020) for i in range(20)],
    )
    llm_refine_gap(_question(), many, _config())
    _system, user = client.calls[0]
    assert "Paper 0" in user
    assert "Paper 5" in user
    assert "Paper 6" not in user  # capped at the first 6
