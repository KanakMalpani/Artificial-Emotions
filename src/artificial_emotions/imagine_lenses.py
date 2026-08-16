"""Stance-twin imagination generators (offline, deterministic).

Each ``_generate_*`` emits ``ImaginedContent`` only. No network. No confidence
scores. Registry wiring and ``apply_imagination`` live in ``imagine.py``.

Ranked twins (premortem, harm_scenario, rehearsal, eulogy, reformulation)
live in ``imagine_twins``; counterfactual lives in ``imagine_counterfactual``.
This module is the stable re-export so ``imagine.py`` does not churn.
"""

from __future__ import annotations

from artificial_emotions.imagine_counterfactual import _generate_counterfactual
from artificial_emotions.imagine_twins import (
    _generate_eulogy,
    _generate_harm_scenario,
    _generate_premortem,
    _generate_reformulation,
    _generate_rehearsal,
)

__all__ = [
    "_generate_counterfactual",
    "_generate_eulogy",
    "_generate_harm_scenario",
    "_generate_premortem",
    "_generate_reformulation",
    "_generate_rehearsal",
]
