"""Track C: ambivalence is enacted in modulate, not stored then ignored.

When ``detect_ambivalence`` scores ≥ 0.35 on a named pair, exclusive expansions
must not both apply as if they agreed. Honesty: ambivalence_enacted,
pattern_not_motive — not a phenomenal state.
"""

from __future__ import annotations

import inspect

from artificial_emotions.emotions import mix_emotions
from artificial_emotions.explore import explore
from artificial_emotions.models import CuriosityConfig
from artificial_emotions.modulate import (
    AMBIVALENCE_ENACT_THRESHOLD,
    modulate_config,
)


def _curious_bored(*, curiosity: int, boredom: int) -> dict:
    mix = mix_emotions({"curiosity": curiosity, "boredom": boredom})
    return mix


def test_enact_threshold_is_the_plan_floor():
    assert AMBIVALENCE_ENACT_THRESHOLD == 0.35


def test_curiosity_vs_boredom_at_tension_does_not_follow_single_winner_n_candidates():
    mix = _curious_bored(curiosity=50, boredom=50)
    assert mix["ambivalence"]["score"] >= AMBIVALENCE_ENACT_THRESHOLD
    assert mix["ambivalence"]["pairs"][0]["components"] == ["curiosity", "boredom"]

    config = CuriosityConfig(domain="ai", n_candidates=16, use_literature=False)
    winner, _ = modulate_config(config, {"curiosity": mix["weights"]["curiosity"]})
    enacted, plan = modulate_config(config, mix["weights"], ambivalence=mix["ambivalence"])

    assert winner.n_candidates > config.n_candidates
    assert enacted.n_candidates == config.n_candidates
    assert plan.ambivalence_enacted is True
    assert "n_candidates" in plan.skipped_exclusive


def test_weight_deltas_do_not_follow_single_winner_path():
    mix = _curious_bored(curiosity=50, boredom=50)
    assert mix["ambivalence"]["score"] >= AMBIVALENCE_ENACT_THRESHOLD

    config = CuriosityConfig(domain="ai", n_candidates=16, use_literature=False)
    _winner_cfg, winner_plan = modulate_config(
        config, {"curiosity": mix["weights"]["curiosity"]}, allow_weight_deltas=True
    )
    _enacted_cfg, enacted_plan = modulate_config(
        config,
        mix["weights"],
        ambivalence=mix["ambivalence"],
        allow_weight_deltas=True,
    )

    winner_knobs = {c.knob for c in winner_plan.changes}
    enacted_knobs = {c.knob for c in enacted_plan.changes}
    assert "value_profile.weight_surprise" in winner_knobs
    assert "value_profile.weight_surprise" not in enacted_knobs
    assert "value_profile.weight_neglectedness" not in enacted_knobs
    assert not (
        "value_profile.weight_surprise" in enacted_knobs
        and "value_profile.weight_neglectedness" in enacted_knobs
    )


def test_apply_both_without_ambivalence_payload_is_the_single_winner_contrast():
    """Control: omitting ambivalence still applies each driver independently."""
    mix = _curious_bored(curiosity=50, boredom=50)
    config = CuriosityConfig(domain="ai", n_candidates=16, use_literature=False)
    naive, plan = modulate_config(config, mix["weights"])
    assert plan.ambivalence_enacted is False
    assert naive.n_candidates > config.n_candidates
    assert naive.diversity_threshold < config.diversity_threshold
    assert plan.suggest_domain_jump is True


def test_below_threshold_still_follows_the_louder_exclusive():
    mix = _curious_bored(curiosity=90, boredom=10)
    assert mix["ambivalence"]["score"] < AMBIVALENCE_ENACT_THRESHOLD

    config = CuriosityConfig(domain="ai", n_candidates=16, use_literature=False)
    new_config, plan = modulate_config(config, mix["weights"], ambivalence=mix["ambivalence"])
    assert plan.ambivalence_enacted is False
    assert new_config.n_candidates > config.n_candidates


def test_louder_curiosity_skips_widen_but_may_keep_quieter_boredom_move():
    mix = _curious_bored(curiosity=65, boredom=35)
    assert mix["ambivalence"]["score"] >= AMBIVALENCE_ENACT_THRESHOLD
    config = CuriosityConfig(domain="ai", n_candidates=16, use_literature=False)
    new_config, plan = modulate_config(config, mix["weights"], ambivalence=mix["ambivalence"])
    assert new_config.n_candidates == config.n_candidates
    assert plan.ambivalence_enacted is True
    # Quieter exclusive may still apply — both sides must not fire together.
    assert (
        new_config.diversity_threshold < config.diversity_threshold
        or plan.suggest_domain_jump is True
    )


def test_payload_honesty_is_pattern_not_motive():
    mix = _curious_bored(curiosity=50, boredom=50)
    _cfg, plan = modulate_config(
        CuriosityConfig(domain="ai", use_literature=False),
        mix["weights"],
        ambivalence=mix["ambivalence"],
    )
    payload = plan.to_dict()
    blob = " ".join(
        [
            payload.get("because", ""),
            " ".join(payload.get("claims") or []),
            payload.get("honesty", ""),
        ]
    ).lower()
    assert payload["ambivalence_enacted"] is True
    assert payload["pattern_not_motive"] is True
    assert "ambivalence_enacted" in payload["claims"]
    assert "pattern_not_motive" in payload["claims"]
    assert "feels torn" not in blob
    assert "i am pulled" not in blob
    assert "i register" not in blob
    assert "discriminating observation" in blob
    assert "curiosity" in blob and "boredom" in blob


def test_explore_forwards_mix_ambivalence_into_modulate():
    source = inspect.getsource(explore)
    assert "ambivalence=" in source
    assert 'mix.get("ambivalence")' in source
    assert "ambivalence" in inspect.signature(modulate_config).parameters
