"""Ranked stance-twin generators except counterfactual.

Callers import from ``artificial_emotions.imagine_lenses`` (stable) or
``artificial_emotions.imagine`` (public registry). Each ``_generate_*`` emits
``ImaginedContent`` only. No network. No confidence scores. No new kinds.
"""

from __future__ import annotations

from collections.abc import Sequence

from artificial_emotions.decompose import decompose_question
from artificial_emotions.imagine_quarantine import ImaginedContent
from artificial_emotions.models import GapStatus, RankedQuestion

__all__ = [
    "_generate_eulogy",
    "_generate_harm_scenario",
    "_generate_premortem",
    "_generate_reformulation",
    "_generate_rehearsal",
]

_VAGUE = ("better", "improve", "optimal", "effective", "good", "useful", "impact of")


# --- premortem (twin of doubt) --------------------------------------------------------


def _generate_premortem(items: Sequence[RankedQuestion]) -> list[ImaginedContent]:
    """Imagine each item failed; invent what killed it from real signals.

    Offline and deterministic. Invented failure modes are stated in ``invented``;
    grounded question ids stay in ``grounded_in``. Never scores confidence.
    """
    out: list[ImaginedContent] = []
    for item in items:
        flags = item.flag_set()
        kills: list[str] = []

        if "heuristic_scoring" in flags:
            kills.append("the ranking was trusted though only a heuristic scored it")
        if "no_literature" in flags:
            kills.append("the gap was never checked against literature")
        if "llm_gap_ungrounded" in flags:
            kills.append("an LLM cited work that was never retrieved")
        if item.confidence < 0.4:
            kills.append(f"low confidence ({item.confidence:.2f}) was treated as settled")
        width = item.score_band_width()
        if width >= 0.5:
            kills.append(f"a wide score band ({width:.2f}) hid how weakly pinned the rank was")
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
    flags = item.flag_set()
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
    flags = item.flag_set()
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
    width = item.score_band_width()
    if width >= 0.5:
        breaks.append(
            f"a wide score band ({width:.2f}) hides that the target may not "
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
    flags = item.flag_set()
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
