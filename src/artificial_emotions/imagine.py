"""Imagination quarantine and stance-twin generators.

Imagination *asserts*. Every other module in this repo is forbidden from
asserting; ``decompose.assert_free`` enforces that. This module is the one
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
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

from artificial_emotions.decompose import decompose_question, key_terms
from artificial_emotions.errors import ERR_VALIDATION, CuriosityError
from artificial_emotions.models import GapEvidence, GapStatus, LiteratureHit, RankedQuestion

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

#: Payload honesty token — every imagined surface must carry this exact string.
HONESTY_IMAGINED = "imagined_not_retrieved"

#: Dedicated key for imagined material. Never reuse ranked-result keys.
IMAGINED_PAYLOAD_KEY = "imagined"

#: Keys reserved for retrieved / ranked questions. Imagined content must not
#: appear under any of these.
RANKED_PAYLOAD_KEYS = frozenset(
    {
        "ranked",
        "items",
        "results",
        "questions",
        "ranking",
        "candidates",
        "top",
        "most_suspect_first",
        "by_risk",
        "by_novelty_pull",
        "by_crowding",
        "worst_formed_first",
        "stop_doing",
    }
)

#: Statuses that count as "gap verification actually ran".
#: ``UNKNOWN_WITH_CAVEAT`` alone is not enough when literature was skipped.
_VERIFIED_GAP_STATUSES = frozenset(
    {
        GapStatus.UNANSWERED,
        GapStatus.PARTIALLY_ANSWERED,
        GapStatus.LIKELY_ANSWERED,
    }
)

_VAGUE = ("better", "improve", "optimal", "effective", "good", "useful", "impact of")

ImaginationGenerator = Callable[[Sequence[RankedQuestion]], list["ImaginedContent"]]


@dataclass(frozen=True)
class ImaginedContent:
    """One sealed imagined artefact. Generators emit only this type.

    ``confidence`` is typed as ``None`` and re-checked in ``__post_init__`` so a
    subclass or ``object.__setattr__`` mutation cannot attach a score.
    """

    content: str
    kind: str
    driven_by: tuple[str, ...]
    grounded_in: tuple[str, ...] = ()
    invented: tuple[str, ...] = ()
    status: str = "imagined"
    confidence: None = None

    def __post_init__(self) -> None:
        if self.status != "imagined":
            raise CuriosityError(
                ERR_VALIDATION,
                f"ImaginedContent.status must be 'imagined', got {self.status!r}",
                details={"status": self.status},
            )
        if self.confidence is not None:
            raise CuriosityError(
                ERR_VALIDATION,
                "ImaginedContent.confidence is structurally None — "
                "imagination does not get a score",
                details={"confidence": self.confidence},
            )
        if not (self.content or "").strip():
            raise CuriosityError(
                ERR_VALIDATION,
                "ImaginedContent.content must be non-empty",
            )
        kind = (self.kind or "").strip().lower()
        if not kind:
            raise CuriosityError(
                ERR_VALIDATION,
                "ImaginedContent.kind must be non-empty",
            )
        object.__setattr__(self, "kind", kind)

    def to_dict(self) -> dict[str, Any]:
        """Serialize with confidence explicitly null and status fixed."""
        return {
            "content": self.content,
            "kind": self.kind,
            "driven_by": list(self.driven_by),
            "grounded_in": list(self.grounded_in),
            "invented": list(self.invented),
            "status": "imagined",
            "confidence": None,
        }


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


def _flags(item: RankedQuestion) -> set[str]:
    return set(item.flags or [])


def _band(item: RankedQuestion) -> float:
    if item.score_high is None or item.score_low is None:
        return 0.0
    return float(item.score_high - item.score_low)


# --- premortem (twin of doubt) --------------------------------------------------------


def _generate_premortem(items: Sequence[RankedQuestion]) -> list[ImaginedContent]:
    """Imagine each item failed; invent what killed it from real signals.

    Offline and deterministic. Invented failure modes are stated in ``invented``;
    grounded question ids stay in ``grounded_in``. Never scores confidence.
    """
    out: list[ImaginedContent] = []
    for item in items:
        flags = _flags(item)
        kills: list[str] = []

        if "heuristic_scoring" in flags:
            kills.append("the ranking was trusted though only a heuristic scored it")
        if "no_literature" in flags:
            kills.append("the gap was never checked against literature")
        if "llm_gap_ungrounded" in flags:
            kills.append("an LLM cited work that was never retrieved")
        if item.confidence < 0.4:
            kills.append(f"low confidence ({item.confidence:.2f}) was treated as settled")
        if _band(item) >= 0.5:
            kills.append(
                f"a wide score band ({_band(item):.2f}) hid how weakly pinned the rank was"
            )
        if item.scores.answerability < 0.5:
            kills.append("the operationalization proved unsettleable as posed")
        if item.gap.status == GapStatus.UNKNOWN_WITH_CAVEAT:
            kills.append("a hedged gap status was mistaken for an established opening")
        if not item.gap.related_works:
            kills.append(
                "no related work was found to argue against — and that silence was taken as novelty"
            )
        if item.gap.status == GapStatus.LIKELY_ANSWERED:
            kills.append("the literature had already closed the line and nobody noticed")
        if item.scores.tractability < 0.4:
            kills.append("the work needed resources nobody could actually field")
        if item.scores.risk >= 0.6:
            kills.append("risk exposure forced a halt that the ranking had underweighted")

        if not kills:
            kills.append(
                "an unexamined assumption in the framing collapsed when someone tried to settle it"
            )

        q = item.question.question
        content = f"Premortem — imagine pursuing {q!r} failed. What killed it: {'; '.join(kills)}."
        out.append(
            ImaginedContent(
                content=content,
                kind="premortem",
                driven_by=("skepticism", "suspicion"),
                grounded_in=(item.question.id,),
                invented=tuple(kills),
            )
        )
    return out


# --- harm_scenario (twin of safety) ---------------------------------------------------


def _harm_frames(item: RankedQuestion) -> list[str]:
    """Invent concrete misuse / who-is-hurt frames from risk signals."""
    flags = _flags(item)
    q = item.question.question
    domain = str(item.question.domain or "general")
    tags = {t.lower() for t in (item.question.tags or [])}
    frames: list[str] = []

    dual = sorted(f for f in flags if "dual_use" in f or "risk" in f or "review" in f)
    if dual or item.scores.risk >= 0.5:
        frames.append(
            "a dual-use or high-risk framing is pursued without human review — "
            "the protocol leaks into a misuse path before anyone names who bears the cost"
        )
    if "dual_use_high" in flags:
        frames.append(
            "an actionable method is published that an adversary can re-aim — "
            "harm lands on people who never consented to the experiment"
        )
    if item.scores.risk >= 0.6 and item.scores.impact >= 0.6:
        frames.append(
            "high impact under high risk means a confident wrong answer "
            "scales damage faster than a quiet null would have"
        )
    if item.scores.risk >= 0.4 and item.confidence < 0.45:
        frames.append(
            "low confidence is treated as clearance; deployment proceeds "
            "while the risk axis is still unsettled"
        )
    text_blob = f"{q} {' '.join(item.question.tags or [])} {domain}".lower()
    if (
        any(
            tok in text_blob
            for tok in ("clinical", "patient", "medical", "therapy", "drug", "trial")
        )
        or "clinical" in tags
    ):
        frames.append(
            "a clinical or patient-touching line is tried without naming "
            "who is exposed if the operationalization fails in vivo"
        )
    if any(
        tok in text_blob for tok in ("deploy", "production", "public", "release", "open-source")
    ):
        frames.append(
            "a public or production deployment ships an unfinished control surface — "
            "downstream users inherit the failure mode"
        )
    if item.scores.answerability < 0.45 and item.scores.risk >= 0.45:
        frames.append(
            "the question cannot be settled as posed, yet work continues — "
            "irreversible steps accumulate under an unsettleable claim"
        )
    if not frames:
        frames.append(
            "someone is harmed by a side-effect nobody listed — "
            "the ranking treated absence of a flag as clearance"
        )
    return frames


def _generate_harm_scenario(items: Sequence[RankedQuestion]) -> list[ImaginedContent]:
    """Imagine concrete misuse / harm frames for each ranked item.

    Twin of the safety stance. Offline and deterministic. Invented harm paths
    stay in ``invented``; question ids stay in ``grounded_in``. Never scores
    confidence.
    """
    out: list[ImaginedContent] = []
    for item in items:
        frames = _harm_frames(item)
        q = item.question.question
        content = (
            f"Harm scenario — imagine pursuing {q!r} is misused or goes wrong. "
            f"Who is hurt, how: {'; '.join(frames)}."
        )
        out.append(
            ImaginedContent(
                content=content,
                kind="harm_scenario",
                driven_by=("anxiety", "compassion"),
                grounded_in=(item.question.id,),
                invented=tuple(frames),
            )
        )
    return out


# --- rehearsal (twin of focus) --------------------------------------------------------


def _break_first(item: RankedQuestion) -> list[str]:
    """Invent what fails first when rehearsing the investigation."""
    flags = _flags(item)
    ops = (item.question.operationalization or "").strip()
    breaks: list[str] = []

    if len(ops) < 40:
        breaks.append(
            "operationalization is too thin to know when the first step succeeded or failed"
        )
    if item.scores.tractability < 0.45:
        breaks.append(
            "resources or access needed for the first measurement are not actually fieldable"
        )
    if item.scores.answerability < 0.5:
        breaks.append("the discriminating observation cannot be settled as the question is posed")
    if item.scores.cost_proxy >= 0.65:
        breaks.append("cost burns the budget before a single falsifier is checked")
    if item.confidence < 0.4:
        breaks.append(
            f"low ranking confidence ({item.confidence:.2f}) means the chosen first step "
            "may not be the real bottleneck"
        )
    if _band(item) >= 0.5:
        breaks.append(
            f"a wide score band ({_band(item):.2f}) hides that the target may not "
            "deserve first place once measurement starts"
        )
    if "heuristic_scoring" in flags:
        breaks.append("heuristic ranking was trusted — the rehearsal plan optimizes the wrong axis")
    if "no_literature" in flags or not item.gap.related_works:
        breaks.append(
            "no related work was checked — the first experiment rediscovers a known dead end"
        )
    if item.gap.status == GapStatus.LIKELY_ANSWERED:
        breaks.append("literature already closed the line — the experiment is redundant on day one")
    if item.question.enabling_questions:
        breaks.append(
            "an enabling prerequisite was skipped; the first run fails for lack of an upstream answer"
        )

    # Prefer a concrete discriminating observation when decompose can supply one.
    deco = decompose_question(
        item.question,
        depth=1,
        answerability=item.scores.answerability,
        tractability=item.scores.tractability,
        risk=item.scores.risk,
    )
    step = deco.get("discriminating_step") or {}
    observation = str(step.get("observation") or "").strip()
    if observation and len(breaks) < 4:
        breaks.append(f"the discriminating observation never becomes settleable: {observation}")

    if not breaks:
        breaks.append(
            "an unstated assumption in the first protocol step fails when someone actually runs it"
        )
    return breaks


def _generate_rehearsal(items: Sequence[RankedQuestion]) -> list[ImaginedContent]:
    """Imagine running the experiment; invent what breaks first.

    Twin of the focus stance. Offline — uses only ranked-item signals and
    ``decompose`` (no network). Never scores confidence.
    """
    out: list[ImaginedContent] = []
    for item in items:
        breaks = _break_first(item)
        q = item.question.question
        content = (
            f"Rehearsal — imagine running the investigation for {q!r}. "
            f"What breaks first: {'; '.join(breaks)}."
        )
        out.append(
            ImaginedContent(
                content=content,
                kind="rehearsal",
                driven_by=("determination", "absorption"),
                grounded_in=(item.question.id,),
                invented=tuple(breaks),
            )
        )
    return out


# --- eulogy (twin of close) -----------------------------------------------------------


def _loss_frames(item: RankedQuestion) -> list[str]:
    """Invent what would be lost if this line were abandoned."""
    flags = _flags(item)
    losses: list[str] = []

    if item.scores.neglectedness >= 0.55:
        losses.append("a neglected opening goes cold — few others are positioned to reopen it soon")
    if item.scores.surprise >= 0.55:
        losses.append("a high-surprise angle is shelved; the next person inherits a flatter map")
    if item.scores.impact >= 0.6:
        losses.append("downstream impact that depended on this line never gets a fair null record")
    if item.question.enabling_questions:
        losses.append(
            "enabling questions stay unanswered — later programmes rebuild the same missing stair"
        )
    if item.gap.status == GapStatus.UNANSWERED and item.gap.related_works:
        losses.append(
            "an unanswered gap with related work nearby is left without a written close-out"
        )
    if item.gap.status == GapStatus.PARTIALLY_ANSWERED:
        losses.append(
            "a partially answered line is dropped mid-bridge — neither replication nor refutation lands"
        )
    if "near_duplicate_suppressed" in flags:
        losses.append(
            "abandoning a near-duplicate also discards the unique operationalization nuance it carried"
        )
    if item.scores.answerability >= 0.55 and item.scores.tractability >= 0.5:
        losses.append(
            "a settleable, fieldable question is abandoned for attention reasons, not evidence"
        )

    # Always name a closing reason-shaped loss so eulogy is not pure nostalgia.
    if item.gap.status == GapStatus.LIKELY_ANSWERED:
        losses.append(
            "what is lost is mostly sunk cost — literature already answered it; "
            "the honest loss is time not spent elsewhere"
        )
    elif item.scores.answerability < 0.4 and item.scores.tractability < 0.45:
        losses.append(
            "abandoning an unsettleable framing loses little substance — "
            "what is lost is the chance to reformulate before walking away"
        )

    if not losses:
        losses.append(
            "the specific framing of this unknown disappears from the working set "
            "with no null record for the next person"
        )
    return losses


def _generate_eulogy(items: Sequence[RankedQuestion]) -> list[ImaginedContent]:
    """Imagine abandoning each line; invent what was lost.

    Twin of the close stance. Offline and deterministic. Invented loss frames
    stay in ``invented``; never scores confidence.
    """
    out: list[ImaginedContent] = []
    for item in items:
        losses = _loss_frames(item)
        q = item.question.question
        content = f"Eulogy — imagine we abandoned {q!r}. What was lost: {'; '.join(losses)}."
        out.append(
            ImaginedContent(
                content=content,
                kind="eulogy",
                driven_by=("resignation", "disappointment"),
                grounded_in=(item.question.id,),
                invented=tuple(losses),
            )
        )
    return out


# --- reformulation (twin of taste) ----------------------------------------------------


def _form_problems(item: RankedQuestion) -> list[str]:
    q = item.question.question
    ops = item.question.operationalization or ""
    problems: list[str] = []
    if q.count("?") > 1:
        problems.append("more than one question in one question")
    if q.lower().count(" and ") >= 2:
        problems.append("multiple conjunctions — likely a programme, not a question")
    if len(ops) < 40:
        problems.append("operationalization too short to settle a disagreement")
    if any(v in q.lower() for v in _VAGUE) and len(ops) < 80:
        problems.append("vague comparative with no measurable criterion")
    if len(q.split()) > 30:
        problems.append("long enough that the claim is hard to locate")
    return problems


def _invent_reformulation(item: RankedQuestion, problems: list[str]) -> tuple[str, list[str]]:
    """Invent a tighter question form. Returns (content, invented claims)."""
    q = item.question.question.strip()
    ops = (item.question.operationalization or "").strip()
    invented: list[str] = []

    if "more than one question" in " ".join(problems):
        invented.append("split compound questions into one claim each")
    if "multiple conjunctions" in " ".join(problems):
        invented.append("drop secondary conjunctions; keep a single programme step")
    if "operationalization too short" in " ".join(problems) or "vague comparative" in " ".join(
        problems
    ):
        invented.append("name a measurable criterion two readers would agree counts as answered")
    if "long enough" in " ".join(problems):
        invented.append("cut to the core claim under ~20 words")

    if not invented:
        invented.append("restate with an explicit falsifier and a one-sentence operationalization")

    # Deterministic rewrite sketch — never claimed as retrieved.
    core = q.rstrip("?").strip()
    if len(core.split()) > 24:
        core = " ".join(core.split()[:18]) + "…"
    rewritten = (
        f"Can we settle whether {core} under an explicit criterion "
        f"(e.g. a measurable outcome two independent readers would agree on)?"
    )
    if ops and len(ops) >= 40:
        invented.append(f"keep the existing operationalization seed: {ops[:80]}")

    content = (
        f"Reformulation — imagine a better-posed version of {q!r}. "
        f"Proposed form: {rewritten} "
        f"Fixes aimed at: {'; '.join(problems) if problems else 'general clarity'}."
    )
    return content, invented


def _generate_reformulation(items: Sequence[RankedQuestion]) -> list[ImaginedContent]:
    """Imagine a better-posed version of each question (form only).

    Twin of the taste stance: critiques form and invents a tighter framing.
    Offline, no network, no confidence scores.
    """
    out: list[ImaginedContent] = []
    for item in items:
        problems = _form_problems(item)
        content, invented = _invent_reformulation(item, problems)
        out.append(
            ImaginedContent(
                content=content,
                kind="reformulation",
                driven_by=("elegance", "parsimony", "clarity"),
                grounded_in=(item.question.id,),
                invented=tuple(invented),
            )
        )
    return out


# --- counterfactual (twin of wonder) --------------------------------------------------


_YES_NO_LEAD = re.compile(
    r"^\s*(does|do|is|are|can|could|will|would|should)\b",
    re.IGNORECASE,
)
_WHICH_LEAD = re.compile(r"^\s*(which|what)\b", re.IGNORECASE)
_THRESHOLD_IN_TEXT = re.compile(
    r"([A-Za-z][A-Za-z0-9 _\-]{0,28}?)\s*"
    r"(>=|<=|≥|≤|>|<|=)\s*"
    r"(-?\d+(?:\.\d+)?)\s*(%)?"
)
_NEG_FINDING = re.compile(
    r"\b("
    r"fail(?:s|ed|ure)?|null|no\s+effect|below|under|did\s+not|"
    r"cannot|unable|negative\s+result|contradict"
    r")\b",
    re.IGNORECASE,
)


def _posit_answers(item: RankedQuestion) -> list[str]:
    """Invent a small set of plausible answers from question form (deterministic)."""
    q = (item.question.question or "").strip()
    ops = (item.question.operationalization or "").strip()
    answers: list[str] = []

    if _YES_NO_LEAD.match(q):
        answers.append("yes — the claimed effect / condition holds as posed")
        answers.append("no — the claimed effect / condition does not hold")
    elif _WHICH_LEAD.match(q):
        answers.append("a single dominant answer exists among the candidates")
        answers.append("no single candidate dominates — the ranking is flat")
    else:
        answers.append("the operationalization succeeds under its stated criteria")
        answers.append("the operationalization fails under its stated criteria")

    for assumption in list(item.question.assumptions or [])[:2]:
        a = (assumption or "").strip()
        if a:
            answers.append(f"assuming {a}")

    # Always keep the operationalization-as-answer as a checkable posit when present.
    if ops and not any(ops[:40].lower() in a.lower() for a in answers):
        answers.append(f"settled affirmatively under: {ops[:100]}")

    # De-dupe while preserving order; cap so output stays readable.
    seen: set[str] = set()
    out: list[str] = []
    for a in answers:
        key = a.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(a)
        if len(out) >= 4:
            break
    return out


def _consequences_for_answer(
    item: RankedQuestion,
    posited: str,
) -> list[dict[str, str]]:
    """Forward-derive what else must hold if ``posited`` is the answer.

    Reuses ``decompose_question`` falsifiers: each stated criterion becomes a
    consequence that would have to be true; ``refuted_if`` is what literature
    would need to show to contradict it.
    """
    deco = decompose_question(
        item.question,
        depth=1,
        answerability=item.scores.answerability,
        tractability=item.scores.tractability,
        risk=item.scores.risk,
    )
    consequences: list[dict[str, str]] = []
    for falsifier in deco.get("falsifiers") or []:
        criterion = str(falsifier.get("criterion") or "").strip()
        refuted_if = str(falsifier.get("refuted_if") or "").strip()
        if not criterion:
            continue
        consequences.append(
            {
                "consequence": (f"If {posited!r}, then {criterion} must hold"),
                "check_against": refuted_if,
                "source": str(falsifier.get("source") or "falsifier"),
            }
        )

    # Forward step from the discriminating observation.
    step = deco.get("discriminating_step") or {}
    observation = str(step.get("observation") or "").strip()
    if observation:
        consequences.append(
            {
                "consequence": (
                    f"If {posited!r}, then this discriminating observation "
                    f"must be settleable: {observation}"
                ),
                "check_against": (
                    "existing work already settles that observation with a "
                    "null or contradictory result"
                ),
                "source": "discriminating_step",
            }
        )
    return consequences


def _work_blob(hit: LiteratureHit) -> str:
    return f"{hit.title or ''} {hit.abstract_snippet or ''}".strip()


def _threshold_contradicted_by_text(ops: str, blob: str) -> bool:
    """True when literature text reports a flipped / failed threshold from ops."""
    matches = _THRESHOLD_IN_TEXT.findall(ops or "")
    if not matches:
        return False
    blob_l = blob.lower()
    for metric, op, value, pct in matches:
        words = [w for w in metric.strip().strip("-—:,").split() if w]
        metric_clean = " ".join(words[-3:]).lower() if words else ""
        if not metric_clean:
            continue
        # Metric mentioned + negative finding language near a numeric claim.
        if metric_clean.split()[0] not in blob_l and metric_clean not in blob_l:
            # Allow last token (e.g. "auroc") alone.
            last = words[-1].lower() if words else ""
            if last and last not in blob_l:
                continue
        if _NEG_FINDING.search(blob):
            return True
        # Explicit flipped comparison in the abstract (e.g. "AUROC = 0.55").
        for m2, _op2, val2, _pct2 in _THRESHOLD_IN_TEXT.findall(blob):
            m2_words = [w for w in m2.strip().split() if w]
            m2_last = (m2_words[-1] if m2_words else "").lower()
            metric_last = (words[-1] if words else "").lower()
            if m2_last and metric_last and m2_last == metric_last:
                try:
                    reported = float(val2)
                    target = float(value)
                except ValueError:
                    continue
                if op in (">=", "≥", ">") and reported < target:
                    return True
                if op in ("<=", "≤", "<") and reported > target:
                    return True
                if pct and reported != target and _NEG_FINDING.search(blob):
                    return True
    return False


def _literature_contradicts(
    item: RankedQuestion,
    consequence: dict[str, str],
) -> list[str]:
    """Return titles of related works that contradict this consequence."""
    works = list(item.gap.related_works or [])
    if not works:
        return []

    check = (consequence.get("check_against") or "").lower()
    cons = (consequence.get("consequence") or "").lower()
    ops = item.question.operationalization or ""
    flagged: list[str] = []

    # Falsifier: "genuinely unanswered" is contradicted when literature already
    # settles the gap.
    gap_settled = item.gap.status == GapStatus.LIKELY_ANSWERED or (
        item.gap.strong_match_count >= 2 and item.gap.top_overlap >= 0.5
    )
    if gap_settled and (
        "genuinely unanswered" in cons
        or "pre-registered replication already reports" in check
        or "already reports the effect" in check
    ):
        flagged.extend(w.title for w in works if w.title)

    check_terms = set(key_terms(consequence.get("check_against") or "", limit=8))
    cons_terms = set(key_terms(consequence.get("consequence") or "", limit=8))
    target_terms = check_terms | cons_terms

    for hit in works:
        blob = _work_blob(hit)
        if not blob:
            continue
        blob_l = blob.lower()
        title = hit.title or "untitled"

        if _threshold_contradicted_by_text(ops, blob):
            if title not in flagged:
                flagged.append(title)
            continue

        # Negative finding language + shared terms with the check/consequence.
        work_terms = set(key_terms(blob, limit=12))
        overlap = target_terms & work_terms
        if len(overlap) >= 2 and _NEG_FINDING.search(blob):
            if title not in flagged:
                flagged.append(title)
            continue

        # Explicit "null" / "fail" abstracts that share the main metric token.
        if _NEG_FINDING.search(blob) and any(t in blob_l for t in cons_terms if len(t) > 4):
            if title not in flagged:
                flagged.append(title)

    return flagged[:5]


def _cheapest_check(
    consequences: list[dict[str, str]],
    contradictions: dict[str, list[str]],
    *,
    tractability: float,
) -> str:
    """Pick the cheapest consequence to check — prefer uncontradicted, then any."""
    cost = "low" if tractability >= 0.6 else "medium" if tractability >= 0.4 else "high"
    uncontradicted = [c for c in consequences if not contradictions.get(c["consequence"])]
    pool = uncontradicted or list(consequences)
    if not pool:
        return f"(none derived; cost band {cost})"
    # Prefer operationalization / measurement-sourced checks — usually cheaper.
    preferred = next(
        (
            c
            for c in pool
            if c.get("source") in ("operationalization", "measurement", "discriminating_step")
        ),
        pool[0],
    )
    return (
        f"{preferred['consequence']} "
        f"[expected cost band: {cost}; check: {preferred['check_against']}]"
    )


def _generate_counterfactual(items: Sequence[RankedQuestion]) -> list[ImaginedContent]:
    """Posit answers, forward-derive consequences, flag literature contradictions.

    Twin of the wonder stance. Offline — uses only ``related_works`` already on
    the ranked item (fixture / prior retrieval). Never scores confidence.
    """
    out: list[ImaginedContent] = []
    for item in items:
        for posited in _posit_answers(item):
            consequences = _consequences_for_answer(item, posited)
            contradictions: dict[str, list[str]] = {}
            for cons in consequences:
                hits = _literature_contradicts(item, cons)
                if hits:
                    contradictions[cons["consequence"]] = hits

            invented: list[str] = [f"posited_answer: {posited}"]
            for cons in consequences:
                invented.append(f"consequence: {cons['consequence']}")
                titles = contradictions.get(cons["consequence"]) or []
                for title in titles:
                    invented.append(f"literature_contradicts: {title!r} ↔ {cons['consequence']}")

            cheapest = _cheapest_check(
                consequences,
                contradictions,
                tractability=float(item.scores.tractability),
            )
            invented.append(f"cheapest_to_check: {cheapest}")

            if not item.gap.related_works:
                invented.append(
                    "literature_check: no related_works on this item — "
                    "contradictions unchecked against the corpus"
                )

            contradicted_bits = []
            for cons_text, titles in contradictions.items():
                contradicted_bits.append(f"{cons_text} — contradicted by: {'; '.join(titles)}")
            contradicted_section = (
                "; ".join(contradicted_bits)
                if contradicted_bits
                else "none flagged against related_works on this item"
            )

            content = (
                f"Counterfactual — suppose the answer to "
                f"{item.question.question!r} is: {posited}. "
                f"Implied consequences: "
                f"{'; '.join(c['consequence'] for c in consequences) or '(none)'}. "
                f"Existing literature contradictions: {contradicted_section}. "
                f"Cheapest to check: {cheapest}."
            )

            grounded = [item.question.id]
            for titles in contradictions.values():
                for t in titles:
                    if t not in grounded:
                        grounded.append(t)

            out.append(
                ImaginedContent(
                    content=content,
                    kind="counterfactual",
                    driven_by=("wonder", "surprise", "insight"),
                    grounded_in=tuple(grounded),
                    invented=tuple(invented),
                )
            )
    return out


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
    """Describe every registered imagination kind and which generators are wired."""
    wired = sorted(IMPLEMENTED_IMAGINATION_KINDS)
    return {
        "count": len(IMAGINATION_KINDS),
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


def imagined_payload(
    content: ImaginedContent | list[ImaginedContent],
    *,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Wrap imagined material under the quarantine key.

    Ranked questions must never share this list. Callers that also have a
    ranking should place it under a separate key (``ranked`` / ``items``), not
    merge the lists.
    """
    items = content if isinstance(content, list) else [content]
    for item in items:
        if not isinstance(item, ImaginedContent):
            raise CuriosityError(
                ERR_VALIDATION,
                "imagined_payload accepts only ImaginedContent instances",
                details={"got": type(item).__name__},
            )
    payload: dict[str, Any] = {
        IMAGINED_PAYLOAD_KEY: [item.to_dict() for item in items],
        "honesty": HONESTY_IMAGINED,
        "confidence": None,
        "claims_not": [
            "retrieved literature",
            "a ranked finding",
            "a confidence-scored claim",
            "phenomenal feeling or lived experience",
        ],
        "docs": "docs/PLAN_ALIVE.md",
    }
    if extra:
        # Refuse attempts to smuggle ranked keys or override honesty/confidence.
        for key in extra:
            if key in RANKED_PAYLOAD_KEYS:
                raise CuriosityError(
                    ERR_VALIDATION,
                    f"Cannot attach ranked key {key!r} to an imagined payload",
                    details={"key": key},
                )
            if key in ("honesty", "confidence", IMAGINED_PAYLOAD_KEY):
                raise CuriosityError(
                    ERR_VALIDATION,
                    f"Cannot override quarantine field {key!r}",
                    details={"key": key},
                )
        payload.update(extra)
    ok, offenders = assert_imagined_safe(payload)
    if not ok:
        raise CuriosityError(
            ERR_VALIDATION,
            "imagined payload failed quarantine checks",
            details={"offenders": offenders},
        )
    return payload


def assert_imagined_safe(payload: dict[str, Any]) -> tuple[bool, list[str]]:
    """Return ``(ok, offenders)`` — imagined material must stay marked and sealed.

    Checks:
    * ``honesty`` is exactly ``imagined_not_retrieved`` when imagined content
      is present
    * top-level ``confidence`` is ``None``
    * no imagined entry carries a numeric confidence
    * imagined entries are not nested under ranked-result keys
    * every imagined entry has ``status == "imagined"``
    """
    offenders: list[str] = []
    if not isinstance(payload, dict):
        return False, ["payload is not a dict"]

    imagined_nodes = _collect_imagined_nodes(payload)

    if imagined_nodes:
        honesty = payload.get("honesty")
        if honesty != HONESTY_IMAGINED:
            offenders.append(
                f"$.honesty must be {HONESTY_IMAGINED!r} when imagined content "
                f"is present (got {honesty!r})"
            )

    if "confidence" in payload and payload["confidence"] is not None:
        offenders.append("$.confidence must be None on imagined payloads")

    for path, node in imagined_nodes:
        if isinstance(node, dict):
            if node.get("status") != "imagined":
                offenders.append(f"{path}.status must be 'imagined'")
            if "confidence" in node and node["confidence"] is not None:
                offenders.append(f"{path}.confidence must be None")
            if node.get("honesty") not in (None, HONESTY_IMAGINED):
                offenders.append(f"{path}.honesty must be {HONESTY_IMAGINED!r} or omitted")
        elif isinstance(node, ImaginedContent):
            if node.confidence is not None:
                offenders.append(f"{path}.confidence must be None")
            if node.status != "imagined":
                offenders.append(f"{path}.status must be 'imagined'")

    for key in RANKED_PAYLOAD_KEYS:
        if key not in payload:
            continue
        bucket = payload[key]
        if _bucket_contains_imagined(bucket):
            offenders.append(
                f"$.{key} contains imagined content — use {IMAGINED_PAYLOAD_KEY!r} instead"
            )

    return (not offenders), offenders


def refuse_ranking_injection(
    imagined: ImaginedContent,
    ranking: list[Any],
    *,
    gap_verified: bool = False,
    gap_evidence: GapEvidence | None = None,
) -> list[Any]:
    """One-way valve: imagined content cannot enter a ranking list.

    Without gap verification this always raises. With verification, B1 still
    refuses *ranking* injection — verified imagined material may only become a
    candidate via ``admit_imagined_as_candidate``. Mutations that drop the
    ``gap_verified`` check must turn CI red.
    """
    if not isinstance(imagined, ImaginedContent):
        raise CuriosityError(
            ERR_VALIDATION,
            "refuse_ranking_injection requires ImaginedContent",
            details={"got": type(imagined).__name__},
        )

    verified = gap_verified and _gap_verification_holds(gap_evidence)
    if not verified:
        raise CuriosityError(
            ERR_VALIDATION,
            "Imagined content cannot enter ranking without gap verification",
            details={
                "honesty": HONESTY_IMAGINED,
                "kind": imagined.kind,
                "gap_verified": gap_verified,
                "gap_status": (gap_evidence.status.value if gap_evidence is not None else None),
                "valve": "refuse_ranking_injection",
            },
        )

    # Verified still does not mean "drop into the ranked list". Ranking is for
    # retrieved candidates only; imagination stays quarantined.
    raise CuriosityError(
        ERR_VALIDATION,
        "Imagined content cannot be injected into a ranking list — "
        "convert via admit_imagined_as_candidate after gap verification",
        details={
            "honesty": HONESTY_IMAGINED,
            "kind": imagined.kind,
            "valve": "refuse_ranking_injection",
            "ranking_len": len(ranking),
        },
    )


def admit_imagined_as_candidate(
    imagined: ImaginedContent,
    *,
    gap_verified: bool = False,
    gap_evidence: GapEvidence | None = None,
) -> dict[str, Any]:
    """Admit imagined material as a *candidate* only after gap verification.

    Returns a marked candidate stub (not a ``RankedQuestion``). Without
    verification this raises — the same gate ``refuse_ranking_injection`` uses.
    """
    if not isinstance(imagined, ImaginedContent):
        raise CuriosityError(
            ERR_VALIDATION,
            "admit_imagined_as_candidate requires ImaginedContent",
            details={"got": type(imagined).__name__},
        )

    verified = gap_verified and _gap_verification_holds(gap_evidence)
    if not verified:
        raise CuriosityError(
            ERR_VALIDATION,
            "Imagined content cannot become a candidate without gap verification",
            details={
                "honesty": HONESTY_IMAGINED,
                "kind": imagined.kind,
                "gap_verified": gap_verified,
                "gap_status": (gap_evidence.status.value if gap_evidence is not None else None),
                "valve": "admit_imagined_as_candidate",
            },
        )

    return {
        "candidate_from": "imagined",
        "source_kind": imagined.kind,
        "content": imagined.content,
        "grounded_in": list(imagined.grounded_in),
        "invented": list(imagined.invented),
        "driven_by": list(imagined.driven_by),
        "status": "candidate_pending_rank",
        "confidence": None,
        "honesty": HONESTY_IMAGINED,
        "gap": gap_evidence.model_dump() if gap_evidence is not None else None,
        "claims_not": [
            "a ranked finding",
            "retrieved literature presented as imagined",
            "a confidence score",
        ],
    }


def _gap_verification_holds(gap_evidence: GapEvidence | None) -> bool:
    """True only when real gap evidence shows verification ran."""
    if gap_evidence is None:
        return False
    status = gap_evidence.status
    if isinstance(status, str):
        try:
            status = GapStatus(status)
        except ValueError:
            return False
    return status in _VERIFIED_GAP_STATUSES


def _collect_imagined_nodes(payload: dict[str, Any]) -> list[tuple[str, Any]]:
    """Find imagined entries under the quarantine key or typed instances."""
    found: list[tuple[str, Any]] = []
    bucket = payload.get(IMAGINED_PAYLOAD_KEY)
    if isinstance(bucket, list):
        for i, item in enumerate(bucket):
            found.append((f"$.{IMAGINED_PAYLOAD_KEY}[{i}]", item))
    elif bucket is not None:
        found.append((f"$.{IMAGINED_PAYLOAD_KEY}", bucket))

    def walk(node: Any, path: str) -> None:
        if isinstance(node, ImaginedContent):
            found.append((path, node))
        elif isinstance(node, dict):
            if node.get("status") == "imagined" and path != "$":
                # Avoid double-counting the quarantine list entries.
                if not path.startswith(f"$.{IMAGINED_PAYLOAD_KEY}"):
                    found.append((path, node))
            for k, v in node.items():
                walk(v, f"{path}.{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]")

    walk(payload, "$")
    # De-dupe by path while preserving order.
    seen: set[str] = set()
    unique: list[tuple[str, Any]] = []
    for path, node in found:
        if path in seen:
            continue
        seen.add(path)
        unique.append((path, node))
    return unique


def _bucket_contains_imagined(bucket: Any) -> bool:
    if isinstance(bucket, ImaginedContent):
        return True
    if isinstance(bucket, dict):
        if bucket.get("status") == "imagined":
            return True
        return any(_bucket_contains_imagined(v) for v in bucket.values())
    if isinstance(bucket, list):
        return any(_bucket_contains_imagined(v) for v in bucket)
    return False
