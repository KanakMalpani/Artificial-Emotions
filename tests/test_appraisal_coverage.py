"""Guards against the emotion catalog becoming decoration.

Past hole: an earlier version could derive 13 of 54 catalogued emotions, and
only **four** ever fired across all nine domains. The other fifty were furniture.

The catalog is the **runtime** contract: production dispatch evaluates catalog
``when`` only. ``RULES`` lambdas stay a characterization golden (``evaluate_when``
vs lambda), not a second runtime.

Current guard: ``MIN_CATALOG_SHARE = 1.0`` — every catalog id has a condition
and a use. These tests make the old hole unreachable:

* every rule in ``RULES`` must be **firable** — constructible inputs exist that
  trigger it, so no rule is dead code;
* every rule must **matter** — it either changes behaviour in ``modulate`` or is
  explicitly declared ``OBSERVATION_ONLY``;
* every appraisable emotion must **exist in the catalog**, so appraisal cannot
  invent vocabulary the mixer does not know;
* every catalog id has a **condition** — non-empty ``when``, or
  ``requires: outcome_event`` plus a fixture that fires it — and a **use**
  (an effect other than only ``surface_only``, a stance driver, or an
  imagination driver). Unnamed holes are not licensed by a low floor;
* every catalog emotion must **have a use** — it steers the search, or it
  drives a stance, or it drives a wired imaginative lens. Being named and
  disclaimed is not a use.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from artificial_emotions.appraisal import (
    OBSERVATION_ONLY,
    RULES,
    AppraisalContext,
    build_context,
)
from artificial_emotions.emotions import emotion_catalog
from artificial_emotions.imagine import IMAGINATION_KINDS, IMPLEMENTED_IMAGINATION_KINDS
from artificial_emotions.models import CuriosityConfig
from artificial_emotions.modulate import modulate_config
from artificial_emotions.pipeline import CuriosityEngine
from artificial_emotions.stances import STANCES

CATALOG_IDS = {e["id"] for e in emotion_catalog()["emotions"]}


def _requires_tokens_of(entry: dict) -> list[str]:
    raw = entry.get("requires")
    if isinstance(raw, str):
        return [raw] if raw else []
    if isinstance(raw, list):
        return [str(t) for t in raw if t]
    return []


def _outcome_fire_fixtures() -> dict[str, dict[str, object]]:
    """Pride/shame fixtures live in Twelve; coverage only checks they exist."""
    from tests.test_twelve_leftovers import FIRING

    return {
        eid: ctx
        for eid, ctx in FIRING.items()
        if ctx.get("outcome_result") and ctx.get("outcome_question_id")
    }


def _has_condition(
    entry: dict,
    *,
    outcome_fixtures: dict[str, dict[str, object]] | None = None,
) -> bool:
    if entry.get("when"):
        return True
    if "outcome_event" not in _requires_tokens_of(entry):
        return False
    fixtures = outcome_fixtures if outcome_fixtures is not None else _outcome_fire_fixtures()
    fixture = fixtures.get(str(entry["id"]))
    return bool(fixture and fixture.get("outcome_result") and fixture.get("outcome_question_id"))


def _conditioned_ids(
    entries: list[dict] | None = None,
    *,
    outcome_fixtures: dict[str, dict[str, object]] | None = None,
) -> set[str]:
    rows = entries if entries is not None else list(emotion_catalog()["emotions"])
    return {str(e["id"]) for e in rows if _has_condition(e, outcome_fixtures=outcome_fixtures)}


#: A context per rule that should make it fire. Written by hand so each entry
#: documents the situation the emotion is *about*.
FIRING_CONTEXTS: dict[str, dict[str, object]] = {
    "curiosity": {
        "gap_ratio": 1.0,
        "mean_neglect": 0.9,
        "mean_impact": 0.9,
        "mean_tractability": 0.8,
    },
    "interest": {"gap_ratio": 0.8},
    "wonder": {"mean_impact": 0.7, "mean_surprise": 0.6},
    "surprise": {"mean_surprise": 0.7, "gap_ratio": 0.8},
    "confusion": {"disagreement": 0.5, "mean_answerability": 0.3},
    "perplexity": {"dense_yet_open": 0.8},
    "uncertainty": {"band_width": 0.7},
    "disorientation": {"mean_answerability": 0.2},
    "dissonance": {"top_clause_count": 3},
    "hubris": {"thin_evidence": 0.9, "mean_confidence": 0.9},
    "humility": {"thin_evidence": 0.9, "mean_confidence": 0.2},
    "skepticism": {"ungrounded_ratio": 0.5},
    "suspicion": {"mean_surprise": 0.7, "thin_evidence": 0.7},
    "anxiety": {"dual_use_ratio": 0.5, "max_risk": 0.8},
    "reluctance": {"max_risk": 0.7, "mean_impact": 0.7},
    "compassion": {"mean_impact": 0.8},
    "insight": {"top_score": 0.9, "top_answerability": 0.8},
    "determination": {"top_score": 0.9, "top_answerability": 0.8},
    "hope": {"mean_tractability": 0.8, "mean_answerability": 0.8},
    "anticipation": {"score_spread": 0.2},
    "recognition": {"term_saturation": 0.5},
    "absorption": {"top_repeated": True},
    "urgency": {"mean_impact": 0.8, "mean_cost": 0.2},
    "persistence": {"steps_without_progress": 1, "gap_ratio": 0.8},
    "elegance": {"top_ops_len": 80, "top_answerability": 0.8},
    "parsimony": {"top_clause_count": 1, "top_ops_len": 90},
    "clarity": {"mean_answerability": 0.9},
    "enjoyment": {"mean_cost": 0.2, "mean_tractability": 0.8, "gap_ratio": 0.8},
    "respect": {"mean_related": 8.0},
    "envy": {"mean_citations": 500.0},
    "boredom": {"repeat_ratio": 1.0, "term_saturation": 0.9},
    "impatience": {"duplicate_ratio": 0.6},
    "frustration": {"steps_without_progress": 3},
    "resignation": {"rejected_ratio": 3.0},
    "disappointment": {"answered_ratio": 0.6},
    "satisfaction": {"top_score": 0.7, "thin_evidence": 0.1},
    "triumph": {"top_score": 0.9, "thin_evidence": 0.1},
    "doubt": {
        "band_width": 0.7,
        "disagreement": 0.4,
        "thin_evidence": 0.6,
        "mean_confidence": 0.7,
    },
    "conviction": {
        "band_width": 0.1,
        "mean_answerability": 0.85,
        "thin_evidence": 0.1,
        "mean_tractability": 0.7,
    },
    "trust": {"mean_related": 6.0, "gap_ratio": 0.8},
    "awe": {"mean_impact": 0.8, "mean_surprise": 0.7, "gap_ratio": 0.9},
    "sublimity": {"mean_impact": 0.8, "mean_tractability": 0.2, "mean_cost": 0.8},
}


@pytest.fixture(scope="module")
def neutral_context() -> AppraisalContext:
    """A real run's context, used as the baseline each firing case perturbs."""
    items = CuriosityEngine(
        CuriosityConfig(domain="ai", use_llm=False, use_literature=False, n_return=5)
    ).run()
    ctx = build_context(items)
    # Flatten to genuinely neutral so a fixture cannot fire by accident.
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
    )


# --- no dead rules ---------------------------------------------------------------------


def test_every_rule_has_a_firing_fixture():
    """A rule with no known firing situation is untestable, so it is not allowed."""
    assert set(RULES) == set(FIRING_CONTEXTS), {
        "missing_fixture": sorted(set(RULES) - set(FIRING_CONTEXTS)),
        "stale_fixture": sorted(set(FIRING_CONTEXTS) - set(RULES)),
    }


@pytest.mark.parametrize("emotion", sorted(RULES))
def test_every_rule_is_firable(emotion: str, neutral_context: AppraisalContext):
    """No rule may be dead code — each must fire on a constructible context."""
    ctx = replace(neutral_context, **FIRING_CONTEXTS[emotion])
    _why, rule = RULES[emotion]
    outcome = rule(ctx)
    assert outcome is not None, f"{emotion} never fires"
    weight, evidence = outcome
    assert weight >= 0.04, f"{emotion} fires below the noise floor ({weight})"
    assert evidence, f"{emotion} fires without evidence"


@pytest.mark.parametrize("emotion", sorted(RULES))
def test_no_rule_fires_on_a_neutral_context(emotion: str, neutral_context: AppraisalContext):
    """Rules that always fire carry no information."""
    outcome = RULES[emotion][1](neutral_context)
    if outcome is not None:
        weight, _ = outcome
        assert weight < 0.04, f"{emotion} fires on a neutral run (weight {weight})"


# --- every rule matters ----------------------------------------------------------------


def _modulating_emotions() -> set[str]:
    """Emotions whose catalog effects change search (not ``surface_only`` only).

    Wave 2: the if-ladder is gone; catalog ``effects`` are the contract.
    ``inspect.getsource(modulate_config)`` would miss catalog-driven ids.
    ``drop_dual_use`` / ``forbid_similar_jump`` are plan flags — they count
    as acting; explore omits ``dual_use_high`` items when ``drop_dual_use``
    fires (heuristic residual remains).
    """
    acting: set[str] = set()
    for entry in emotion_catalog()["emotions"]:
        effects = [str(x) for x in (entry.get("effects") or [])]
        if any(x != "surface_only" for x in effects):
            acting.add(str(entry["id"]))
    return acting


def _appraisable_ids() -> set[str]:
    """Ids appraisal can actually emit: RULES plus catalog rows with a condition."""
    return set(RULES) | _conditioned_ids()


def _stance_driving_emotions() -> set[str]:
    """Emotions that are the *point* of a stance rather than a modifier on search."""
    return {e for stance in STANCES.values() for e in stance.driving_emotions}


def _imagination_driving_emotions() -> set[str]:
    """Emotions that drive a wired imaginative lens (B4+)."""
    return {
        e
        for kind in IMAGINATION_KINDS.values()
        if kind.generate is not None
        for e in kind.driving_emotions
    }


def test_every_appraisable_emotion_either_acts_or_is_declared_observation_only():
    """The anti-decoration rule: derive it, then either use it or say you won't."""
    acting = _modulating_emotions()
    unaccounted = set(RULES) - acting - OBSERVATION_ONLY
    assert not unaccounted, (
        f"{sorted(unaccounted)} are appraised but neither change behaviour nor are "
        "listed in OBSERVATION_ONLY — that is how a catalog becomes decoration."
    )


def test_every_emotion_has_a_use_not_merely_a_disclaimer():
    """The stronger claim, and the one users actually care about.

    ``OBSERVATION_ONLY`` is an honest label, but on its own it is still a catalog
    of things the system names and never uses. Stances closed that gap: an
    emotion that does not steer the search must at least be the question some
    stance asks — or drive a wired imaginative lens. Nothing is allowed to be
    merely observed. Wave 3: the union is every catalog id, not only ``RULES``.
    """
    useful = _modulating_emotions() | _stance_driving_emotions() | _imagination_driving_emotions()
    homeless = CATALOG_IDS - useful
    assert not homeless, (
        f"{sorted(homeless)} are catalogued but do nothing — they neither modulate "
        "search, drive a stance, nor drive an imaginative lens. Give them a use "
        "or drop the row."
    )
    for entry in emotion_catalog()["emotions"]:
        assert str(entry.get("use_for") or "").strip(), f"{entry['id']} has empty use_for"
        lowered = str(entry["use_for"]).lower()
        assert "i feel" not in lowered, f"{entry['id']} use_for is first-person"


def test_stances_only_claim_emotions_the_system_can_actually_appraise():
    """A stance driven by a feeling that never fires is a marketing claim."""
    invented = _stance_driving_emotions() - _appraisable_ids()
    assert not invented, f"stances claim {sorted(invented)}, which appraisal never derives"


def test_imagination_only_claims_emotions_the_system_can_actually_appraise():
    invented = _imagination_driving_emotions() - set(RULES)
    assert not invented, (
        f"imagination kinds claim {sorted(invented)}, which appraisal never derives"
    )


def test_stances_reach_past_curiosity():
    """Curiosity already had a surface. The stances exist for everything else."""
    drivers = _stance_driving_emotions()
    assert "curiosity" not in drivers, (
        "a stance is driven by curiosity — that is the ranking's job, not a stance's"
    )
    assert len(STANCES) >= MIN_STANCES, f"only {len(STANCES)} stances"
    assert len(drivers) >= MIN_STANCE_DRIVERS, f"only {len(drivers)} emotions drive a stance"


def test_imagination_twins_start_shipping():
    """Ratchet: six ranked-applicable generators stay wired (transfer stays corpus-gated)."""
    assert len(IMPLEMENTED_IMAGINATION_KINDS) >= MIN_IMAGINATION_GENERATORS
    for kind in (
        "premortem",
        "harm_scenario",
        "rehearsal",
        "eulogy",
        "reformulation",
        "counterfactual",
    ):
        assert kind in IMPLEMENTED_IMAGINATION_KINDS
    assert "transfer" not in IMPLEMENTED_IMAGINATION_KINDS


def test_former_stub_emotions_drive_wired_imagination():
    """Once lenses ship, their driving emotions must count toward the usefulness union."""
    drivers = _imagination_driving_emotions()
    for emotion in (
        "anxiety",
        "compassion",  # harm_scenario
        "determination",
        "absorption",  # rehearsal
        "resignation",
        "disappointment",  # eulogy
    ):
        assert emotion in drivers, f"{emotion} missing from wired imagination drivers"
    useful = _modulating_emotions() | _stance_driving_emotions() | drivers
    assert not (set(RULES) - useful)


def test_stripping_an_imagination_generator_fails_the_ratchet(monkeypatch: pytest.MonkeyPatch):
    """Mutation: treating a wired kind as generate=None must fail the ratchet.

    Same spirit as quarantine mutation tests — silently dropping a generator
    must make the coverage floor bite. Usefulness still holds via stances for
    these emotions; the generator count is what the ratchet guards.
    """
    target = "harm_scenario"
    original = IMAGINATION_KINDS[target]
    assert original.generate is not None
    monkeypatch.setitem(IMAGINATION_KINDS, target, replace(original, generate=None))

    implemented = frozenset(
        name for name, kind in IMAGINATION_KINDS.items() if kind.generate is not None
    )
    assert target not in implemented
    assert len(implemented) < MIN_IMAGINATION_GENERATORS
    for emotion in original.driving_emotions:
        assert emotion not in _imagination_driving_emotions()

    with pytest.raises(AssertionError):
        assert len(implemented) >= MIN_IMAGINATION_GENERATORS
        assert target in implemented


def test_observation_only_emotions_still_have_somewhere_to_go():
    """Every emotion the loop refuses to act on must at least answer some question."""
    stranded = OBSERVATION_ONLY - _stance_driving_emotions() - _imagination_driving_emotions()
    assert not stranded, (
        f"{sorted(stranded)} are appraised, deliberately never acted on, and drive no "
        "stance or imaginative lens — appraising them is pure decoration."
    )


def test_observation_only_emotions_really_do_not_act():
    """If it acts, it should not be claiming to be observation-only."""
    overlap = OBSERVATION_ONLY & _modulating_emotions()
    assert not overlap, f"{sorted(overlap)} are declared observation-only but do modulate"


# Ratchet floors. These sit just under what the code currently achieves, so
# ordinary churn does not trip them but a real regression toward the old
# "13 derivable, 4 firing" state does. Raise them as coverage grows; never lower.
MIN_RULES = 40
MIN_CATALOG_SHARE = 1.0
MIN_ACTING = 20
MIN_FIRING_OFFLINE = 18
MIN_DISTINCT_DRIVERS_PER_RUN = 3
MIN_STANCES = 7
MIN_STANCE_DRIVERS = 24
MIN_IMAGINATION_GENERATORS = 6

# Track B — original 37, measured on 6-step explore × ai,biology,physics,climate,medicine
# with use_literature=False (Engine.run loop). Do not fake literature or dual-use.
#
# Already fired before recalibration (13): anticipation, boredom, clarity, curiosity,
# determination, dissonance, elegance, hope, humility, insight, interest, persistence,
# uncertainty.
#
# Recalibrated so they fire from offline axes / bands / clause counts / repeats (12).
# Handoff guessed ~15; hubris (heuristic confidence cap), disorientation (empty /
# collapsed rank), and suspicion (would enable OpenAlex via modulate) stay gated.
RECALIBRATED_OFFLINE_RULES: frozenset[str] = frozenset(
    {
        "absorption",
        "compassion",
        "confusion",
        "enjoyment",
        "frustration",
        "impatience",
        "parsimony",
        "recognition",
        "resignation",
        "surprise",
        "urgency",
        "wonder",
    }
)
#: Need related_works, citations, LLM-grounded cites, or non-thin evidence.
LITERATURE_GATED_RULES: frozenset[str] = frozenset(
    {
        "disappointment",
        "envy",
        "perplexity",
        "respect",
        "satisfaction",
        "skepticism",
        "triumph",
    }
)
#: Need dual-use / max_risk flags that default packs do not raise offline.
RISK_FLAG_RULES: frozenset[str] = frozenset({"anxiety", "reluctance"})
#: Hubris needs confidence above the heuristic cap; disorientation needs an
#: empty or collapsed-answerability rank (empty runs still emit it in appraise_run).
#: Suspicion's thin-evidence input exists offline, but lowering its surprise bar
#: makes modulate set use_literature=True and pulls OpenAlex into spark.
OFFLINE_UNREACHABLE_WITHOUT_LIVE_SIGNALS: frozenset[str] = frozenset(
    {"hubris", "disorientation", "suspicion"}
)
_OFFLINE_EXPLORE_DOMAINS = ("ai", "biology", "physics", "climate", "medicine")

#: Catalog leftovers named so share=1.0 does not claim they fire on spark.
LITERATURE_GATED_CATALOG: frozenset[str] = frozenset({"admiration", "gratitude"})
RISK_FLAG_CATALOG: frozenset[str] = frozenset({"fear", "disgust"})
OUTCOME_EVENT_IDS: frozenset[str] = frozenset({"pride", "shame"})
PREVIOUS_STEP_IDS: frozenset[str] = frozenset({"embarrassment", "relief", "anger"})
_FIVE_EPISTEMIC = ("doubt", "conviction", "trust", "awe", "sublimity")


def test_a_meaningful_share_of_the_catalog_is_reachable():
    """The original failure was 13/54 derivable. Every id now has a condition."""
    assert len(RULES) >= MIN_RULES, f"only {len(RULES)} rules"
    conditioned = _conditioned_ids()
    share = len(conditioned) / len(CATALOG_IDS)
    assert share >= MIN_CATALOG_SHARE, f"only {share:.0%} of the catalog has a condition"
    assert conditioned == CATALOG_IDS


def test_every_catalog_id_has_a_condition():
    """Non-empty ``when``, or ``outcome_event`` plus a fixture that fires it."""
    missing = CATALOG_IDS - _conditioned_ids()
    assert not missing, f"catalog ids with no condition: {sorted(missing)}"
    extra = _conditioned_ids() - CATALOG_IDS
    assert not extra, f"conditioned ids unknown to the catalog: {sorted(extra)}"


def test_emptying_curiosity_when_fails():
    """Mutation: a shipped id with no ``when`` and no outcome fixture is a hole."""
    entries = []
    for raw in emotion_catalog()["emotions"]:
        entry = dict(raw)
        if entry["id"] == "curiosity":
            entry["when"] = []
        entries.append(entry)
    conditioned = _conditioned_ids(entries)
    assert "curiosity" not in conditioned
    share = len(conditioned) / len(CATALOG_IDS)
    with pytest.raises(AssertionError):
        assert share >= MIN_CATALOG_SHARE
        assert conditioned == CATALOG_IDS


def test_enough_emotions_actually_change_behaviour():
    """Derivable-but-inert is still decoration. Count the ones that act."""
    acting = _modulating_emotions()
    assert len(acting) >= MIN_ACTING, f"only {len(acting)} emotions modulate: {sorted(acting)}"


def test_appraisal_never_invents_vocabulary_outside_the_catalog():
    unknown = set(RULES) - CATALOG_IDS
    assert not unknown, f"appraisal can emit {sorted(unknown)}, which the mixer cannot mix"


def test_plan_flags_count_as_real_use_with_stance():
    """``drop_dual_use`` / ``forbid_similar_jump`` are plan flags, not a new effect id.

    Explore omits ``dual_use_high`` items when ``drop_dual_use`` fires;
    ``forbid_similar_jump`` skips similar-domain hops when opted in.
    Frustration/resignation stop is ``jump_ground``, not ``stop``.
    """
    by_id = {e["id"]: e for e in emotion_catalog()["emotions"]}
    assert "drop_dual_use" in by_id["disgust"]["effects"]
    assert "forbid_similar_jump" in by_id["anger"]["effects"]
    assert "jump_ground" in by_id["frustration"]["effects"]
    assert "jump_ground" in by_id["resignation"]["effects"]
    assert "stop" not in by_id["frustration"]["effects"]
    drivers = _stance_driving_emotions()
    assert "disgust" in drivers and "anger" in drivers


def test_outcome_gated_affect_is_not_derived_from_rank():
    """Pride/shame wait on logged outcomes, not top_score — that path is triumph."""
    assert not (OUTCOME_EVENT_IDS & set(RULES)), (
        f"{sorted(OUTCOME_EVENT_IDS & set(RULES))} derived from rank — that is triumph, not outcome"
    )
    fixtures = _outcome_fire_fixtures()
    for eid in OUTCOME_EVENT_IDS:
        assert eid in fixtures, f"{eid} requires outcome_event but has no Twelve firing fixture"
        assert fixtures[eid].get("outcome_result")
        assert fixtures[eid].get("outcome_question_id")


def test_gated_catalog_antecedents_are_named():
    """Literature / risk / previous / outcome stay named; share=1.0 is not spark coverage."""
    by_id = {e["id"]: e for e in emotion_catalog()["emotions"]}
    for eid in OUTCOME_EVENT_IDS:
        assert "outcome_event" in _requires_tokens_of(by_id[eid]), eid
    for eid in PREVIOUS_STEP_IDS:
        assert "previous_step" in _requires_tokens_of(by_id[eid]), eid
    for eid in LITERATURE_GATED_CATALOG:
        assert "literature" in _requires_tokens_of(by_id[eid]), eid
    for eid in RISK_FLAG_CATALOG:
        assert "risk_flags" in _requires_tokens_of(by_id[eid]), eid


def test_five_epistemic_rules_are_in_rules_and_firing_contexts():
    for emotion in _FIVE_EPISTEMIC:
        assert emotion in RULES, f"{emotion} missing from RULES"
        assert emotion in FIRING_CONTEXTS, f"{emotion} missing from FIRING_CONTEXTS"
        assert emotion in CATALOG_IDS


def test_hopeless_mega_gap_does_not_outrank_tractable_curiosity(
    neutral_context: AppraisalContext,
):
    """Loewenstein/Pekrun: curiosity wants a closable gap, not a hopeless mega-gap."""
    hopeless = replace(
        neutral_context,
        gap_ratio=1.0,
        mean_neglect=0.95,
        mean_impact=0.95,
        mean_tractability=0.02,
    )
    tractable = replace(
        neutral_context,
        gap_ratio=0.45,
        mean_neglect=0.55,
        mean_impact=0.55,
        mean_tractability=0.8,
    )
    hopeless_out = RULES["curiosity"][1](hopeless)
    tractable_out = RULES["curiosity"][1](tractable)
    assert hopeless_out is not None and tractable_out is not None
    h_weight, h_ev = hopeless_out
    t_weight, _ = tractable_out
    assert t_weight > h_weight, (
        f"hopeless mega-gap curiosity {h_weight:.3f} outranked tractable {t_weight:.3f}"
    )
    assert "mean_tractability" in h_ev
    assert h_ev["mean_tractability"] == pytest.approx(0.02, abs=1e-6)


def test_conviction_does_not_fire_on_a_hopeless_mega_gap(neutral_context: AppraisalContext):
    hopeless = replace(
        neutral_context,
        band_width=0.1,
        mean_answerability=0.9,
        thin_evidence=0.0,
        mean_tractability=0.05,
        gap_ratio=1.0,
        mean_impact=0.95,
    )
    assert RULES["conviction"][1](hopeless) is None


def test_awe_requires_an_open_gap_wonder_does_not(neutral_context: AppraisalContext):
    closed_scale = replace(neutral_context, mean_impact=0.8, mean_surprise=0.7, gap_ratio=0.0)
    open_scale = replace(neutral_context, mean_impact=0.8, mean_surprise=0.7, gap_ratio=0.9)
    assert RULES["wonder"][1](closed_scale) is not None
    assert RULES["awe"][1](closed_scale) is None
    awe_open = RULES["awe"][1](open_scale)
    assert awe_open is not None
    assert awe_open[0] >= 0.04


def test_trust_requires_a_live_gap_respect_does_not(neutral_context: AppraisalContext):
    dense_closed = replace(neutral_context, mean_related=8.0, gap_ratio=0.0)
    dense_open = replace(neutral_context, mean_related=6.0, gap_ratio=0.8)
    assert RULES["respect"][1](dense_closed) is not None
    assert RULES["trust"][1](dense_closed) is None
    trust_open = RULES["trust"][1](dense_open)
    assert trust_open is not None
    assert trust_open[0] >= 0.04


def test_sublimity_does_not_loosen_safety_gates():
    """The vast/hard is never a reason to raise max_risk or skip review."""
    config = CuriosityConfig(domain="ai", use_literature=False)
    new_config, plan = modulate_config(config, {"sublimity": 0.9})
    assert plan.changes == []
    assert new_config.value_profile.max_risk == config.value_profile.max_risk
    assert plan.require_review is False


# --- reachability on *real* runs, not just constructed contexts ------------------------


def test_offline_rule_buckets_partition_the_original_catalog_minus_track_a():
    """Literature / risk / live-signal rules are named; the rest must be reachable offline."""
    track_a = {"doubt", "conviction", "trust", "awe", "sublimity"}
    original = set(RULES) - track_a
    gated = LITERATURE_GATED_RULES | RISK_FLAG_RULES | OFFLINE_UNREACHABLE_WITHOUT_LIVE_SIGNALS
    assert not (RECALIBRATED_OFFLINE_RULES & gated)
    assert RECALIBRATED_OFFLINE_RULES <= original
    assert gated <= original
    leftover = original - RECALIBRATED_OFFLINE_RULES - gated
    # The leftover are the 13 that already fired on the measured suite.
    assert leftover, "expected a non-empty already-reachable offline set"
    assert "curiosity" in leftover


def _fired_on_six_step_offline_explores() -> set[str]:
    from artificial_emotions.explore import explore

    fired: set[str] = set()
    for domain in _OFFLINE_EXPLORE_DOMAINS:
        out = explore(
            domain=domain,
            steps=6,
            n_return=5,
            use_literature=False,
            use_llm=False,
            seed=42,
            persist_memory=False,
        )
        for step in out["trajectory"]["steps"]:
            fired.update(a["emotion"] for a in step["appraisal"])
            assert not any(c.get("knob") == "use_literature" for c in step["modulation"]), (
                "offline explore must not enable literature via appraisal"
            )
    return fired


def test_plain_offline_runs_fire_a_variety_of_emotions():
    """Firable-in-principle is not enough; ordinary runs must feel more than one thing."""
    from artificial_emotions.appraisal import appraise_run

    fired: set[str] = set()
    for domain in _OFFLINE_EXPLORE_DOMAINS:
        items = CuriosityEngine(
            CuriosityConfig(domain=domain, use_llm=False, use_literature=False, n_return=5)
        ).run()
        fired |= {s.emotion for s in appraise_run(items)}
    assert len(fired) >= MIN_FIRING_OFFLINE, f"only {len(fired)} fire offline: {sorted(fired)}"


def test_six_step_explore_fires_recalibrated_offline_rules():
    """Lab-green FIRING_CONTEXTS is not enough — these must fire on real offline explores."""
    fired = _fired_on_six_step_offline_explores()
    missing = sorted(RECALIBRATED_OFFLINE_RULES - fired)
    assert not missing, f"recalibrated rules never fired offline: {missing}"
    faked_lit = sorted((LITERATURE_GATED_RULES | LITERATURE_GATED_CATALOG) & fired)
    faked_risk = sorted((RISK_FLAG_RULES | RISK_FLAG_CATALOG) & fired)
    faked_outcome = sorted(OUTCOME_EVENT_IDS & fired)
    assert not faked_lit, f"literature-gated rules must not be faked offline: {faked_lit}"
    assert not faked_risk, f"risk-flag rules must not be faked offline: {faked_risk}"
    assert not faked_outcome, f"outcome-gated rules must not be faked offline: {faked_outcome}"


def test_more_than_one_emotion_drives_change_across_a_real_loop():
    """Locks in the fix for the bug that made only the loudest emotion able to act."""
    from artificial_emotions.explore import explore

    out = explore(domain="ai", steps=4, n_return=4)
    drivers = {c["driver"] for s in out["trajectory"]["steps"] for c in s["modulation"]}
    assert len(drivers) >= MIN_DISTINCT_DRIVERS_PER_RUN, f"only {sorted(drivers)} ever drove change"


def test_a_secondary_signal_still_acts_beside_a_dominant_one():
    """The regression guard for normalisation.

    Modulation used to key off mix *percentages*, which shrink as more emotions
    fire — so a genuinely strong secondary signal fell under the action floor
    purely because something louder fired alongside it. Appraised strength must
    be what decides.
    """
    config = CuriosityConfig(domain="ai", use_literature=False)

    alone = modulate_config(config, {"anxiety": 0.4})[1]
    assert alone.require_review is True

    # Same anxiety, now beside a much louder curiosity. It must still act.
    beside = modulate_config(config, {"curiosity": 0.95, "anxiety": 0.4})[1]
    assert beside.require_review is True, (
        "anxiety stopped acting once a louder emotion fired — modulation is "
        "keying off relative share instead of appraised strength"
    )
    assert {c.driver for c in beside.changes} >= {"curiosity", "anxiety"}


# --- the consequences are real ---------------------------------------------------------


def _plan(weights: dict[str, float], **cfg):
    base = CuriosityConfig(domain="ai", use_literature=False, **cfg)
    return modulate_config(base, weights)[1]


def test_anxiety_tightens_the_risk_ceiling_and_demands_review():
    """Affect may make a safety gate stricter — never looser."""
    config = CuriosityConfig(domain="ai", use_literature=False)
    new_config, plan = modulate_config(config, {"anxiety": 0.8})
    assert plan.require_review is True
    assert new_config.value_profile.max_risk < config.value_profile.max_risk


def test_skepticism_forces_soundness_and_fetches_literature():
    config = CuriosityConfig(domain="ai", use_literature=False)
    new_config, plan = modulate_config(config, {"skepticism": 0.5})
    assert plan.force_soundness is True
    assert new_config.use_literature is True


def test_absorption_protects_a_live_thread_from_stopping():
    """Momentum must be able to veto the stop, or persistence means nothing."""
    assert _plan({"frustration": 0.6}).stop is True
    assert _plan({"frustration": 0.6, "absorption": 0.5}).stop is False


def test_persistence_earns_one_more_pass():
    assert _plan({"frustration": 0.6, "persistence": 0.4}).stop is False


def test_disappointment_changes_ground():
    assert _plan({"disappointment": 0.5}).suggest_domain_jump is True


def test_triumph_turns_a_result_into_a_plan():
    assert _plan({"triumph": 0.5}).force_decompose is True


def test_urgency_narrows_the_return():
    config = CuriosityConfig(domain="ai", n_return=10, use_literature=False)
    new_config, _ = modulate_config(config, {"urgency": 0.6})
    assert new_config.n_return < 10


def test_disorientation_shrinks_and_reframes():
    config = CuriosityConfig(domain="ai", n_return=10, use_literature=False)
    new_config, plan = modulate_config(config, {"disorientation": 0.6})
    assert new_config.n_return < 10
    assert plan.force_decompose is True


def test_observation_only_emotions_change_nothing():
    for emotion in ("elegance", "respect", "envy", "clarity", "wonder"):
        plan = _plan({emotion: 0.9})
        assert plan.changes == [], f"{emotion} should be observation-only"
        assert plan.stop is False


def test_safety_modulation_survives_the_default_no_weight_deltas_rule():
    """Tightening max_risk is a gate, not a scoring weight — it is always allowed."""
    config = CuriosityConfig(domain="ai", use_literature=False)
    _new, plan = modulate_config(config, {"anxiety": 0.8}, allow_weight_deltas=False)
    assert any(c.knob == "value_profile.max_risk" for c in plan.changes)
    assert all(not c.knob.startswith("value_profile.weight_") for c in plan.changes), (
        "scoring weights must stay untouched by default"
    )
