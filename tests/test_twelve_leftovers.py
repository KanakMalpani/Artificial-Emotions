"""Wave 1 Twelve: catalog antecedents for the 12 leftover emotions.

Evaluates catalog ``when`` against constructed :class:`AppraisalContext`.
Does not make catalog ``when`` the ``appraise_run`` source of truth —
Interpreter owns that dispatch. Pride/shame stay silent without an outcome
fixture. Embarrassment/relief/anger need ``previous_*``.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from artificial_emotions.appraisal import (
    EFFECT_IDS,
    AppraisalContext,
    build_context,
    context_feature,
    evaluate_when,
    validate_catalog_entry,
)
from artificial_emotions.emotions import emotion_catalog
from artificial_emotions.models import CuriosityConfig
from artificial_emotions.pipeline import CuriosityEngine

TWELVE = (
    "intrigue",
    "admiration",
    "gratitude",
    "pride",
    "shame",
    "embarrassment",
    "relief",
    "joy",
    "sadness",
    "anger",
    "fear",
    "disgust",
)

#: Constructed overrides that should satisfy each row's ``when``.
FIRING: dict[str, dict[str, object]] = {
    "intrigue": {"gap_ratio": 0.4, "mean_surprise": 0.2},
    "admiration": {"mean_citations": 40.0, "gap_ratio": 0.5, "mean_related": 3.0},
    "gratitude": {"mean_related": 2.0, "top_ops_len": 80},
    "pride": {
        "outcome_result": "partial_progress",
        "outcome_question_id": "q_logged",
        "top_score": 0.3,
        "thin_evidence": 0.5,
    },
    "shame": {
        "outcome_result": "contradicted",
        "outcome_question_id": "q_logged",
        "mean_confidence": 0.75,
    },
    "embarrassment": {"previous_hubris": 0.4, "ungrounded_ratio": 0.3},
    "relief": {"previous_max_risk": 0.7, "max_risk": 0.2, "dual_use_ratio": 0.0},
    "joy": {"gap_ratio": 0.75, "mean_tractability": 0.8, "mean_cost": 0.2},
    "sadness": {"answered_ratio": 0.7, "gap_ratio": 0.2},
    "anger": {
        "previous_top_id": "q_wasted",
        "top_repeated": False,
        "steps_without_progress": 1,
    },
    "fear": {"max_risk": 0.75, "mean_tractability": 0.2, "dual_use_ratio": 0.0},
    "disgust": {"dual_use_ratio": 0.4, "max_risk": 0.2},
}


def _row(eid: str) -> dict:
    for entry in emotion_catalog()["emotions"]:
        if entry["id"] == eid:
            return entry
    raise AssertionError(f"missing catalog id {eid}")


def _eval(ctx: AppraisalContext, eid: str) -> float | None:
    return evaluate_when(ctx, _row(eid)["when"])


def _cmp(actual: object, op: str, expected: object) -> bool:
    if op == "eq":
        if isinstance(expected, list):
            return actual in expected
        return actual == expected
    if op == "ne":
        if isinstance(expected, list):
            return actual not in expected
        return actual != expected
    try:
        left = float(actual)  # type: ignore[arg-type]
        right = float(expected)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False
    if op == "ge":
        return left >= right
    if op == "le":
        return left <= right
    if op == "gt":
        return left > right
    if op == "lt":
        return left < right
    raise AssertionError(f"unknown op {op}")


def when_holds(ctx: AppraisalContext, when: list) -> bool:
    """AND of catalog clauses. List ``eq``/``ne`` is membership (pride/shame)."""
    if not when:
        return False
    return all(
        _cmp(context_feature(ctx, clause["feature"]), clause["op"], clause["value"])
        for clause in when
    )


@pytest.fixture(scope="module")
def neutral() -> AppraisalContext:
    items = CuriosityEngine(
        CuriosityConfig(domain="ai", use_llm=False, use_literature=False, n_return=5)
    ).run()
    ctx = build_context(items)
    return replace(
        ctx,
        gap_ratio=0.0,
        mean_impact=0.3,
        mean_neglect=0.3,
        mean_surprise=0.2,
        mean_tractability=0.4,
        mean_answerability=0.6,
        mean_risk=0.1,
        mean_confidence=0.5,
        mean_cost=0.6,
        max_risk=0.1,
        disagreement=0.0,
        band_width=0.2,
        score_spread=0.0,
        top_score=0.3,
        top_answerability=0.4,
        top_ops_len=200,
        top_clause_count=1,
        thin_evidence=0.0,
        dense_yet_open=0.0,
        answered_ratio=0.0,
        dual_use_ratio=0.0,
        ungrounded_ratio=0.0,
        duplicate_ratio=0.0,
        repeat_ratio=0.0,
        mean_related=0.0,
        mean_citations=0.0,
        term_saturation=0.0,
        steps_without_progress=0,
        rejected_ratio=0.0,
        top_repeated=False,
        previous_max_risk=0.0,
        previous_hubris=0.0,
        previous_top_id="",
        outcome_result="",
        outcome_question_id="",
    )


@pytest.mark.parametrize("eid", TWELVE)
def test_twelve_catalog_rows_are_filled(eid: str) -> None:
    entry = _row(eid)
    validate_catalog_entry(entry)
    assert entry["when"], eid
    assert entry["effects"], eid
    assert entry["use_for"].strip(), eid
    assert entry["coercion"] in {"low", "high"}, eid
    requires = entry["requires"]
    tokens = [requires] if isinstance(requires, str) else list(requires)
    assert tokens, eid
    assert "i feel" not in entry["use_for"].lower()
    unknown = [e for e in entry["effects"] if e not in EFFECT_IDS]
    assert not unknown, unknown


@pytest.mark.parametrize("eid", TWELVE)
def test_twelve_when_fires_on_constructed_context(eid: str, neutral: AppraisalContext) -> None:
    ctx = replace(neutral, **FIRING[eid])
    assert when_holds(ctx, _row(eid)["when"]), eid


def test_pride_silent_without_outcome(neutral: AppraisalContext) -> None:
    ctx = replace(neutral, top_score=0.9, thin_evidence=0.1)
    assert not when_holds(ctx, _row("pride")["when"])


def test_shame_silent_without_outcome(neutral: AppraisalContext) -> None:
    ctx = replace(neutral, mean_confidence=0.9)
    assert not when_holds(ctx, _row("shame")["when"])


def test_pride_fires_on_answered_outcome(neutral: AppraisalContext) -> None:
    ctx = replace(neutral, outcome_result="answered", outcome_question_id="q_logged")
    assert when_holds(ctx, _row("pride")["when"])


def test_shame_fires_on_already_answered(neutral: AppraisalContext) -> None:
    ctx = replace(
        neutral,
        outcome_result="already_answered",
        outcome_question_id="q_logged",
        mean_confidence=0.7,
    )
    assert when_holds(ctx, _row("shame")["when"])


def test_shame_silent_without_high_confidence(neutral: AppraisalContext) -> None:
    ctx = replace(
        neutral,
        outcome_result="contradicted",
        outcome_question_id="q_logged",
        mean_confidence=0.4,
    )
    assert not when_holds(ctx, _row("shame")["when"])


def test_embarrassment_needs_previous_hubris(neutral: AppraisalContext) -> None:
    ctx = replace(neutral, ungrounded_ratio=0.5)
    assert not when_holds(ctx, _row("embarrassment")["when"])
    ctx = replace(neutral, previous_hubris=0.4, ungrounded_ratio=0.5)
    assert when_holds(ctx, _row("embarrassment")["when"])


def test_relief_needs_previous_max_risk(neutral: AppraisalContext) -> None:
    ctx = replace(neutral, max_risk=0.2)
    assert not when_holds(ctx, _row("relief")["when"])
    ctx = replace(neutral, previous_max_risk=0.7, max_risk=0.2)
    assert when_holds(ctx, _row("relief")["when"])


def test_anger_needs_previous_top_id(neutral: AppraisalContext) -> None:
    ctx = replace(neutral, top_repeated=False, steps_without_progress=1)
    assert not when_holds(ctx, _row("anger")["when"])
    ctx = replace(
        neutral,
        previous_top_id="q_wasted",
        top_repeated=False,
        steps_without_progress=1,
    )
    assert when_holds(ctx, _row("anger")["when"])


def test_pride_is_not_triumph_from_rank(neutral: AppraisalContext) -> None:
    ctx = replace(neutral, **FIRING["pride"])
    assert _eval(ctx, "triumph") is None
    assert when_holds(ctx, _row("pride")["when"])


def test_admiration_is_not_respect_or_envy(neutral: AppraisalContext) -> None:
    ctx = replace(neutral, **FIRING["admiration"])
    assert _eval(ctx, "respect") is None
    assert _eval(ctx, "envy") is None
    assert when_holds(ctx, _row("admiration")["when"])


def test_gratitude_is_not_respect(neutral: AppraisalContext) -> None:
    ctx = replace(neutral, **FIRING["gratitude"])
    assert _eval(ctx, "respect") is None
    assert when_holds(ctx, _row("gratitude")["when"])


def test_joy_is_stricter_than_enjoyment(neutral: AppraisalContext) -> None:
    mere = replace(neutral, mean_cost=0.5, mean_tractability=0.5, gap_ratio=0.51)
    assert _eval(mere, "enjoyment") is not None
    assert not when_holds(mere, _row("joy")["when"])
    assert when_holds(replace(neutral, **FIRING["joy"]), _row("joy")["when"])


def test_fear_is_not_anxiety_dual_use_only(neutral: AppraisalContext) -> None:
    anxious = replace(neutral, dual_use_ratio=0.5, max_risk=0.2, mean_tractability=0.8)
    assert _eval(anxious, "anxiety") is not None
    assert not when_holds(anxious, _row("fear")["when"])
    assert when_holds(replace(neutral, **FIRING["fear"]), _row("fear")["when"])


def test_context_feature_dotted_previous_and_outcome(neutral: AppraisalContext) -> None:
    ctx = replace(
        neutral,
        previous_max_risk=0.8,
        previous_hubris=0.4,
        previous_top_id="q_prev",
        outcome_result="Partial_Progress",
        outcome_question_id="q1",
    )
    assert context_feature(ctx, "previous.max_risk") == 0.8
    assert context_feature(ctx, "previous.hubris") == 0.4
    assert context_feature(ctx, "previous.top_id") == "q_prev"
    assert context_feature(ctx, "outcome.result") == "partial_progress"
    assert context_feature(ctx, "outcome.question_id") == "q1"


def test_build_context_wires_previous_and_outcome() -> None:
    items = CuriosityEngine(
        CuriosityConfig(domain="ai", use_llm=False, use_literature=False, n_return=3)
    ).run()
    ctx = build_context(
        items,
        previous_top_id="q_prev",
        previous_max_risk=0.8,
        previous_hubris=0.4,
        outcome_result="partial_progress",
        outcome_question_id="q1",
    )
    assert ctx.previous_max_risk == 0.8
    assert ctx.previous_hubris == 0.4
    assert ctx.previous_top_id == "q_prev"
    assert ctx.outcome_result == "partial_progress"
    assert ctx.outcome_question_id == "q1"


def test_outcome_for_appraisal_silent_without_event(tmp_path: Path) -> None:
    from artificial_emotions.preferences import outcome_for_appraisal

    missing = tmp_path / "missing.jsonl"
    assert outcome_for_appraisal(None) == ("", "")
    assert outcome_for_appraisal(missing) == ("", "")
    missing.write_text("", encoding="utf-8")
    assert outcome_for_appraisal(missing) == ("", "")


def test_outcome_for_appraisal_matches_question_id(tmp_path: Path) -> None:
    from artificial_emotions.preferences import (
        PreferenceEvent,
        append_preference_event,
        outcome_for_appraisal,
    )

    log = tmp_path / "prefs.jsonl"
    append_preference_event(
        log,
        PreferenceEvent(
            event_type="outcome",
            question_id="q_hit",
            labels={"result": "partial_progress"},
        ),
    )
    append_preference_event(
        log,
        PreferenceEvent(
            event_type="note",
            question_id="q_hit",
            notes="not an outcome",
        ),
    )
    assert outcome_for_appraisal(log, question_ids={"q_hit"}) == (
        "partial_progress",
        "q_hit",
    )
    assert outcome_for_appraisal(log, question_ids={"other"}) == ("", "")


def test_explore_passes_previous_into_second_step(monkeypatch: pytest.MonkeyPatch) -> None:
    import artificial_emotions.explore as expl

    captured: list[tuple[object, dict]] = []
    real = expl.appraise_run

    def wrap(items, **kwargs):  # type: ignore[no-untyped-def]
        captured.append((items, kwargs))
        return real(items, **kwargs)

    monkeypatch.setattr(expl, "appraise_run", wrap)
    expl.explore(domain="ai", steps=2, n_return=3, seed=42)
    assert len(captured) == 2
    items0, kw0 = captured[0]
    _items1, kw1 = captured[1]
    expected_risk = max((float(i.scores.risk) for i in items0), default=0.0)
    assert kw0.get("previous_max_risk", 0.0) == 0.0
    assert kw1["previous_max_risk"] == expected_risk


def test_explore_wires_matching_preference_outcome(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from artificial_emotions.preferences import PreferenceEvent, append_preference_event

    items = CuriosityEngine(
        CuriosityConfig(
            domain="ai",
            use_llm=False,
            use_literature=False,
            n_return=3,
            seed=42,
        )
    ).run()
    qid = items[0].question.id
    log = tmp_path / "prefs.jsonl"
    append_preference_event(
        log,
        PreferenceEvent(
            event_type="outcome",
            question_id=qid,
            labels={"result": "partial_progress"},
        ),
    )

    import artificial_emotions.explore as expl

    captured: list[dict] = []
    real = expl.appraise_run

    def wrap(run_items, **kwargs):  # type: ignore[no-untyped-def]
        captured.append(kwargs)
        return real(run_items, **kwargs)

    monkeypatch.setattr(expl, "appraise_run", wrap)
    expl.explore(
        domain="ai",
        steps=1,
        n_return=3,
        seed=42,
        preference_log_path=str(log),
    )
    assert captured[0]["outcome_result"] == "partial_progress"
    assert captured[0]["outcome_question_id"] == qid


def test_explore_outcome_silent_when_question_does_not_match(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from artificial_emotions.preferences import PreferenceEvent, append_preference_event

    log = tmp_path / "prefs.jsonl"
    append_preference_event(
        log,
        PreferenceEvent(
            event_type="outcome",
            question_id="not_in_this_run",
            labels={"result": "partial_progress"},
        ),
    )

    import artificial_emotions.explore as expl

    captured: list[dict] = []
    real = expl.appraise_run

    def wrap(run_items, **kwargs):  # type: ignore[no-untyped-def]
        captured.append(kwargs)
        return real(run_items, **kwargs)

    monkeypatch.setattr(expl, "appraise_run", wrap)
    expl.explore(
        domain="ai",
        steps=1,
        n_return=3,
        seed=42,
        preference_log_path=str(log),
    )
    assert captured[0]["outcome_result"] == ""
    assert captured[0]["outcome_question_id"] == ""


def test_memory_previous_step_roundtrip(tmp_path: Path) -> None:
    from artificial_emotions.memory import PersistentMemory, PreviousStepSnapshot

    path = tmp_path / "memory.json"
    mem = PersistentMemory.load(path)
    mem.previous_step = PreviousStepSnapshot(max_risk=0.8, hubris=0.5, top_id="q9")
    assert mem.save()
    loaded = PersistentMemory.load(path)
    assert loaded.previous_step.max_risk == 0.8
    assert loaded.previous_step.hubris == 0.5
    assert loaded.previous_step.top_id == "q9"


def test_explore_loads_previous_step_from_memory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from artificial_emotions.memory import PersistentMemory, PreviousStepSnapshot

    monkeypatch.delenv("CURIOSITY_NO_MEMORY", raising=False)
    path = tmp_path / "memory.json"
    mem = PersistentMemory.load(path)
    mem.previous_step = PreviousStepSnapshot(max_risk=0.9, hubris=0.4, top_id="prev_q")
    mem.save()

    import artificial_emotions.explore as expl

    captured: list[dict] = []
    real = expl.appraise_run

    def wrap(run_items, **kwargs):  # type: ignore[no-untyped-def]
        captured.append(kwargs)
        return real(run_items, **kwargs)

    monkeypatch.setattr(expl, "appraise_run", wrap)
    expl.explore(
        domain="ai",
        steps=1,
        n_return=3,
        seed=42,
        persist_memory=True,
        memory_path=str(path),
    )
    assert captured[0]["previous_max_risk"] == 0.9
    assert captured[0]["previous_hubris"] == 0.4
    assert captured[0]["previous_top_id"] == "prev_q"
