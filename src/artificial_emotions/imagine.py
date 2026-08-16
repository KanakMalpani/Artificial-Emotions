"""Imagination quarantine and stance-twin generators.

Imagination *asserts*. Every other module in this repo is forbidden from
asserting; ``decompose.assert_free`` enforces that. This package is the one
place assertion is allowed — which makes it the one place that can poison the
repo's credibility.

B1 sealed the container. B4 wires premortem + reformulation. B2 wires
counterfactual (twin of ``wonder``). Harm scenario, rehearsal, and eulogy
complete the ranked-applicable stance twins (safety / focus / close).
B3 ships transfer as a corpus-gated path (``transfer.imagine_transfer``)
that must clear ``validate.py`` lift — not via ``apply_imagination`` over
ranked items. B5 dream is a separate explicit CLI
(``emotions dream`` / ``dream.reanalyze_history``) — offline reanalysis of
PersistentMemory, not a stance-twin generator.

Rules, enforced by tests:

* Imagined content never shares a list key with ranked questions.
* Every payload carries ``honesty: "imagined_not_retrieved"``.
* ``confidence`` is structurally ``None`` — no number next to a fantasy.
* A one-way valve refuses ranking injection without gap verification.
* Generators are offline and deterministic — no network.

Registry shape mirrors ``stances.py``.

Split: quarantine container in ``imagine_quarantine``; ranked twins in
``imagine_twins``; counterfactual in ``imagine_counterfactual``;
``imagine_lenses`` re-exports generators. This module is the registry,
``apply_imagination``, and public import path.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

from artificial_emotions.errors import ERR_VALIDATION, CuriosityError
from artificial_emotions.imagine_lenses import (
    _generate_counterfactual,
    _generate_eulogy,
    _generate_harm_scenario,
    _generate_premortem,
    _generate_reformulation,
    _generate_rehearsal,
)
from artificial_emotions.imagine_quarantine import (
    HONESTY_IMAGINED,
    IMAGINED_PAYLOAD_KEY,
    RANKED_PAYLOAD_KEYS,
    ImaginedContent,
    admit_imagined_as_candidate,
    assert_imagined_safe,
    imagined_payload,
    refuse_ranking_injection,
)
from artificial_emotions.models import RankedQuestion

__all__ = [
    "HONESTY_IMAGINED",
    "IMAGINED_PAYLOAD_KEY",
    "IMAGINATION_KINDS",
    "IMPLEMENTED_IMAGINATION_KINDS",
    "RANKED_PAYLOAD_KEYS",
    "ImaginedContent",
    "ImaginationKind",
    "admit_imagined_as_candidate",
    "apply_imagination",
    "assert_imagined_safe",
    "imagined_payload",
    "list_imagination_kinds",
    "refuse_ranking_injection",
]

ImaginationGenerator = Callable[[Sequence[RankedQuestion]], list["ImaginedContent"]]


@dataclass(frozen=True)
class ImaginationKind:
    """Registry entry for a generative twin of a stance.

    Mirrors ``Stance`` shape (name / asks / use_when / driving_emotions / lens)
    with ``generate`` instead of ``lens``. Unwired kinds keep ``generate=None``.
    """

    name: str
    asks: str
    use_when: str
    driving_emotions: tuple[str, ...]
    stance_twin: str = ""
    generate: ImaginationGenerator | None = field(default=None, repr=False)

    def describe(self) -> dict[str, Any]:
        if self.generate is not None:
            generator: str | None = "wired"
        elif self.name == "transfer":
            # B3: corpus-gated; ship status lives on transfer.TRANSFER_SHIP_STATUS.
            try:
                from artificial_emotions.transfer import TRANSFER_SHIP_STATUS

                generator = "corpus_gated" if TRANSFER_SHIP_STATUS == "shipped" else "cut"
            except ImportError:  # pragma: no cover — package always ships together
                generator = "corpus_gated"
        else:
            generator = None
        return {
            "kind": self.name,
            "asks": self.asks,
            "use_when": self.use_when,
            "driving_emotions": list(self.driving_emotions),
            "stance_twin": self.stance_twin or None,
            "generator": generator,
            "honesty": HONESTY_IMAGINED,
            "claims_not": [
                "retrieved literature or ranked findings",
                "a confidence score",
                "phenomenal feeling or lived experience",
            ],
        }


# Seven stance twins — six ranked-applicable generators wired; transfer corpus-gated.
IMAGINATION_KINDS: dict[str, ImaginationKind] = {
    k.name: k
    for k in (
        ImaginationKind(
            name="premortem",
            asks="Imagine this failed; what killed it?",
            use_when="Before acting on a ranking you might be wrong about.",
            driving_emotions=("skepticism", "suspicion"),
            stance_twin="doubt",
            generate=_generate_premortem,
        ),
        ImaginationKind(
            name="harm_scenario",
            asks="Imagine the misuse concretely — who is hurt, how?",
            use_when="Any set touching dual-use, clinical, or deployment territory.",
            driving_emotions=("anxiety", "compassion"),
            stance_twin="safety",
            generate=_generate_harm_scenario,
        ),
        ImaginationKind(
            name="rehearsal",
            asks="Imagine running the experiment; what breaks first?",
            use_when="You have decided and want failure modes before committing.",
            driving_emotions=("determination", "absorption"),
            stance_twin="focus",
            generate=_generate_rehearsal,
        ),
        ImaginationKind(
            name="eulogy",
            asks="Imagine we abandoned it; what was lost?",
            use_when="End of a sprint, or when a line has stopped paying.",
            driving_emotions=("resignation", "disappointment"),
            stance_twin="close",
            generate=_generate_eulogy,
        ),
        ImaginationKind(
            name="reformulation",
            asks="Imagine a better version of this question.",
            use_when="Editing a proposal, or when form is the blocker.",
            driving_emotions=("elegance", "parsimony", "clarity"),
            stance_twin="taste",
            generate=_generate_reformulation,
        ),
        ImaginationKind(
            name="counterfactual",
            asks="Imagine the answer is X; what else must be true?",
            use_when="You want cheap tests derived from a posited answer.",
            driving_emotions=("wonder", "surprise", "insight"),
            stance_twin="wonder",
            generate=_generate_counterfactual,
        ),
        ImaginationKind(
            name="transfer",
            asks="Imagine this mechanism in another field.",
            use_when=(
                "Before committing effort across domains. "
                "Corpus-gated: emotions imagine transfer --seed … --corpus … "
                "(must clear validate.py lift; not applied over ranked items)."
            ),
            driving_emotions=("respect", "envy", "recognition"),
            stance_twin="survey",
            # generate stays None — ranked apply_imagination cannot run transfer.
            # Corpus path: artificial_emotions.transfer.imagine_transfer.
        ),
    )
}

IMPLEMENTED_IMAGINATION_KINDS: frozenset[str] = frozenset(
    name for name, kind in IMAGINATION_KINDS.items() if kind.generate is not None
)


def list_imagination_kinds() -> dict[str, Any]:
    """Describe every registered imagination kind and which generators are wired.

    ``count`` is the number of ranked-applicable wired generators.
    ``catalog_count`` is the full registry size (includes corpus-gated transfer).
    """
    wired = sorted(IMPLEMENTED_IMAGINATION_KINDS)
    return {
        "count": len(IMPLEMENTED_IMAGINATION_KINDS),
        "catalog_count": len(IMAGINATION_KINDS),
        "kinds": [k.describe() for k in IMAGINATION_KINDS.values()],
        "implemented": wired,
        "honesty": HONESTY_IMAGINED,
        "note": (
            f"Generators wired for: {', '.join(wired) or '(none)'}. "
            "Outputs always travel under the 'imagined' payload key with "
            f"honesty={HONESTY_IMAGINED!r}; they never share a list with ranked "
            "questions and never carry a confidence score."
        ),
        "claims_not": [
            "retrieved findings",
            "a confidence-scored claim",
            "phenomenal feeling",
            "that unwired kinds have been generated",
        ],
    }


def apply_imagination(
    name: str,
    items: Sequence[RankedQuestion],
) -> dict[str, Any]:
    """Run one stance-twin generator over a ranked set.

    Returns a quarantine payload under ``imagined``. Never mutates ``items`` and
    never injects imagined material into a ranking list.
    """
    key = (name or "").strip().lower()
    kind = IMAGINATION_KINDS.get(key)
    if kind is None:
        raise CuriosityError(
            ERR_VALIDATION,
            f"Unknown imagination kind '{name}'. Known: {', '.join(sorted(IMAGINATION_KINDS))}",
            details={"known": sorted(IMAGINATION_KINDS)},
        )
    if kind.generate is None:
        raise CuriosityError(
            ERR_VALIDATION,
            (
                f"Imagination kind '{name}' has no generator yet. "
                f"Wired: {', '.join(sorted(IMPLEMENTED_IMAGINATION_KINDS))}"
            ),
            details={
                "kind": key,
                "implemented": sorted(IMPLEMENTED_IMAGINATION_KINDS),
            },
        )

    generated = kind.generate(items) if items else []
    # One-way valve: every artefact is refused from ranking injection (no gap
    # verification path here — B4 never feeds ranking).
    ranking_guard: list[Any] = []
    for artefact in generated:
        try:
            refuse_ranking_injection(artefact, ranking_guard, gap_verified=False)
        except CuriosityError as exc:
            if exc.details.get("valve") != "refuse_ranking_injection":
                raise
            # Expected refusal — quarantine holds.

    return imagined_payload(
        generated,
        extra={
            "kind": kind.name,
            "asks": kind.asks,
            "use_when": kind.use_when,
            "driving_emotions": list(kind.driving_emotions),
            "stance_twin": kind.stance_twin or None,
            "n_items": len(items),
            "n_imagined": len(generated),
            "offline": True,
            "network": False,
            "note": (
                "Imagined only — not retrieved, not ranked, not confidence-scored. "
                "Does not feel; computational generation under quarantine."
            ),
        },
    )
