"""Appraisal: emotion as the *output* of evaluating a situation.

Everywhere else in this package you hand the affect layer a set of weights and
it renders them. That is a dictionary, not a feeling. Here the direction is
reversed: given what a run actually encountered — open gaps, judge
disagreement, thin evidence under high confidence, ground already covered — this
module derives what the system should be feeling, and *why*.

A wide-open gap on a high-stakes question produces curiosity because the
situation warrants it. Circling a dead end for the third time produces
frustration because it happened, not because a caller asked for it.

**Every rule must be reachable and must matter.** An earlier version could derive
13 of 54 catalogued emotions and only four ever fired in practice, which made the
other fifty decoration. Rules now live in :data:`RULES` as explicit
condition/weight functions over one context object, so
``tests/test_appraisal_coverage.py`` can assert that each is firable and that
each either modulates behaviour or is declared :data:`OBSERVATION_ONLY`.

Every signal carries its evidence. Affect you cannot audit is affect you cannot
trust, and this project does not ship unauditable numbers.

Deterministic and offline. See research/AI_EMOTIONS.md for the appraisal-theory
background (OCC-flavoured, not an OCC implementation).
"""

from __future__ import annotations

import statistics
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, fields
from typing import Any

from artificial_emotions.models import GapStatus, RankedQuestion

__all__ = [
    "APPRAISAL_RULES",
    "CATALOG_SCHEMA_KEYS",
    "CATALOG_WHEN_FEATURES",
    "COERCION_LEVELS",
    "EFFECT_IDS",
    "NEVER_APPRAISE",
    "OBSERVATION_ONLY",
    "REQUIRES_TOKENS",
    "RULES",
    "UNBUILT_UNTIL_OUTCOME",
    "WHEN_OPS",
    "AppraisalContext",
    "AppraisalSignal",
    "appraise_run",
    "build_context",
    "evaluate_when",
    "signals_to_weights",
    "validate_catalog_entry",
    "validate_emotion_catalog",
]

# Lazy catalog PAD lookup for mood-congruent threshold floors (A2).
_EMOTION_PAD_P: dict[str, float] | None = None


def _emotion_pad_p(emotion: str) -> float | None:
    global _EMOTION_PAD_P
    if _EMOTION_PAD_P is None:
        try:
            from artificial_emotions.emotions import emotion_catalog

            _EMOTION_PAD_P = {
                str(e["id"]): float((e.get("pad") or {}).get("P") or 0.0)
                for e in emotion_catalog().get("emotions") or []
            }
        except Exception:  # pragma: no cover — catalog always present in-tree
            _EMOTION_PAD_P = {}
    return _EMOTION_PAD_P.get(emotion)


# Below this a signal is noise; it gets dropped rather than padding the mix.
_MIN_SIGNAL = 0.04

#: Emotions that are appraised but deliberately change nothing. Aesthetic pull
#: and social comparison are real drivers of research choices *and* known biases,
#: so the system surfaces them for the reader instead of acting on them.
OBSERVATION_ONLY: frozenset[str] = frozenset(
    {
        "elegance",
        "parsimony",
        "dissonance",
        "envy",
        "respect",
        "compassion",
        "recognition",
        "clarity",
        "wonder",
        "enjoyment",
        "uncertainty",
        "interest",
        "surprise",
        "insight",
        "humility",
        "doubt",
        "conviction",
        "trust",
        "awe",
        "sublimity",
    }
)

#: Catalog ids appraisal will not derive. Somatic cluster would route around
#: ``AFFECTIVE_SAFETY`` if given a rule (``explore`` mixes without a cap).
#: ``gratitude`` is signal-identical to ``respect``. ``pride`` / ``shame`` need
#: outcome feedback, not rank / ``top_score`` (that path is already ``triumph``).
NEVER_APPRAISE: frozenset[str] = frozenset(
    {
        "anger",
        "fear",
        "joy",
        "sadness",
        "disgust",
        "gratitude",
        "pride",
        "shame",
    }
)

#: Catalog ids with no honest rule yet. ``embarrassment`` / ``relief`` need
#: stored outcome feedback. ``intrigue`` / ``admiration`` have no distinct
#: offline antecedent that would not collapse into curiosity or respect.
UNBUILT_UNTIL_OUTCOME: frozenset[str] = frozenset(
    {
        "embarrassment",
        "relief",
        "intrigue",
        "admiration",
    }
)

#: Frozen catalog effect vocabulary. Wave 2 implements these; do not invent extras.
EFFECT_IDS: frozenset[str] = frozenset(
    {
        "widen_search",
        "narrow_search",
        "demand_literature",
        "decompose",
        "jump_ground",
        "forbid_similar_jump",
        "tighten_safety",
        "drop_dual_use",
        "stay_course",
        "surface_only",
    }
)

#: Catalog ``when`` comparison operators. Wave 1 ``evaluate_when`` consumes these.
WHEN_OPS: frozenset[str] = frozenset({"ge", "le", "gt", "lt", "eq", "ne"})

#: Weight-expression operators nested in a ``when`` node's optional ``weight``.
#: Not catalog ``when`` ops — those stay :data:`WHEN_OPS`.
WEIGHT_EXPR_OPS: frozenset[str] = frozenset(
    {"mul", "add", "avg", "max", "min", "sub", "div", "clamp", "if"}
)

#: Intensity used when a ``when`` tree matches but no node supplies ``weight``.
_DEFAULT_WHEN_WEIGHT = 0.25
_MISSING = object()

#: Search-effect opt-in. ``high`` search effects require ``--somatic-modulate``.
COERCION_LEVELS: frozenset[str] = frozenset({"low", "high"})

#: What a catalog row needs before it may fire. Empty is a Wave 0 placeholder.
REQUIRES_TOKENS: frozenset[str] = frozenset(
    {
        "offline",
        "literature",
        "risk_flags",
        "previous_step",
        "outcome_event",
    }
)

#: Per-emotion catalog keys later waves fill. Do not rename.
CATALOG_SCHEMA_KEYS: tuple[str, ...] = (
    "when",
    "effects",
    "use_for",
    "coercion",
    "requires",
)


@dataclass(frozen=True)
class AppraisalSignal:
    """One emotion, the weight it fired at, and the evidence behind it."""

    emotion: str
    weight: float
    because: str
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "emotion": self.emotion,
            "weight": round(float(self.weight), 4),
            "because": self.because,
            "evidence": self.evidence,
        }


@dataclass(frozen=True)
class AppraisalContext:
    """Everything a rule is allowed to look at, computed once per run.

    Catalog ``when`` clauses use these feature names (see
    :data:`CATALOG_WHEN_FEATURES`):

    ``n``, ``gap_ratio``, ``mean_impact``, ``mean_neglect``, ``mean_surprise``,
    ``mean_tractability``, ``mean_answerability``, ``mean_risk``,
    ``mean_confidence``, ``mean_cost``, ``max_risk``, ``disagreement``,
    ``band_width``, ``score_spread``, ``top_score``, ``top_answerability``,
    ``top_ops_len``, ``top_clause_count``, ``thin_evidence``, ``dense_yet_open``,
    ``answered_ratio``, ``dual_use_ratio``, ``ungrounded_ratio``,
    ``duplicate_ratio``, ``repeat_ratio``, ``mean_related``, ``mean_citations``,
    ``term_saturation``, ``steps_without_progress``, ``rejected_ratio``,
    ``top_repeated``.

    Reserved dotted names for Wave 1 (not fields on this dataclass yet):
    ``previous.max_risk``, ``previous.hubris``, ``previous.top_id``,
    ``outcome.result``, ``outcome.question_id``.
    """

    n: int
    gap_ratio: float
    mean_impact: float
    mean_neglect: float
    mean_surprise: float
    mean_tractability: float
    mean_answerability: float
    mean_risk: float
    mean_confidence: float
    mean_cost: float
    max_risk: float
    disagreement: float
    band_width: float
    score_spread: float
    top_score: float
    top_answerability: float
    top_ops_len: int
    top_clause_count: int
    thin_evidence: float
    dense_yet_open: float
    answered_ratio: float
    dual_use_ratio: float
    ungrounded_ratio: float
    duplicate_ratio: float
    repeat_ratio: float
    mean_related: float
    mean_citations: float
    term_saturation: float
    steps_without_progress: int
    rejected_ratio: float
    top_repeated: bool


#: Feature names catalog ``when`` clauses may address.
#:
#: Current :class:`AppraisalContext` fields plus Wave 1 dotted paths
#: (``previous.max_risk``, ``previous.hubris``, ``previous.top_id``,
#: ``outcome.result``, ``outcome.question_id``). Interpreter consumes those
#: paths if present; Twelve owns wiring them. Do not invent extra names here
#: without adding the matching context field.
CATALOG_WHEN_FEATURES: frozenset[str] = frozenset(
    {f.name for f in fields(AppraisalContext)}
    | {
        "previous.max_risk",
        "previous.hubris",
        "previous.top_id",
        "outcome.result",
        "outcome.question_id",
    }
)

_WHEN_CLAUSE_KEYS: tuple[str, ...] = ("feature", "op", "value")


def _validate_if_cond(cond: object, *, emotion_id: str) -> None:
    if not isinstance(cond, list) or len(cond) != 3 or not isinstance(cond[0], str):
        raise ValueError(f"{emotion_id}: if condition must be [op, feature, value]")
    op, feature, _value = cond
    if op not in WHEN_OPS:
        raise ValueError(f"{emotion_id}: unknown when op {op!r}")
    if not isinstance(feature, str) or feature not in CATALOG_WHEN_FEATURES:
        raise ValueError(f"{emotion_id}: unknown when feature {feature!r}")


def _validate_weight_expr(expr: object, *, emotion_id: str) -> None:
    if isinstance(expr, bool) or isinstance(expr, int) or isinstance(expr, float):
        return
    if isinstance(expr, str):
        if expr not in CATALOG_WHEN_FEATURES:
            raise ValueError(f"{emotion_id}: unknown when feature {expr!r}")
        return
    if isinstance(expr, list) and expr:
        op = expr[0]
        if not isinstance(op, str):
            raise ValueError(f"{emotion_id}: invalid weight expression {expr!r}")
        if op == "if":
            if len(expr) != 4:
                raise ValueError(f"{emotion_id}: if weight form is [if, cond, then, else]")
            _validate_if_cond(expr[1], emotion_id=emotion_id)
            _validate_weight_expr(expr[2], emotion_id=emotion_id)
            _validate_weight_expr(expr[3], emotion_id=emotion_id)
            return
        if op not in WEIGHT_EXPR_OPS:
            raise ValueError(f"{emotion_id}: unknown weight op {op!r}")
        for arg in expr[1:]:
            _validate_weight_expr(arg, emotion_id=emotion_id)
        return
    raise ValueError(f"{emotion_id}: invalid weight expression {expr!r}")


def _validate_when_node(node: object, *, emotion_id: str) -> None:
    if not isinstance(node, Mapping):
        raise ValueError(f"{emotion_id}: when clause must be an object, got {node!r}")
    has_any = "any" in node
    has_all = "all" in node
    has_atom = any(k in node for k in _WHEN_CLAUSE_KEYS)
    has_weight = "weight" in node
    if not (has_any or has_all or has_atom or has_weight):
        raise ValueError(
            f"{emotion_id}: when clause must have feature/op/value, any, all, or weight"
        )
    if has_any:
        group = node["any"]
        if not isinstance(group, list):
            raise ValueError(f"{emotion_id}: any must be a list of when clauses")
        for child in group:
            _validate_when_node(child, emotion_id=emotion_id)
    if has_all:
        group = node["all"]
        if not isinstance(group, list):
            raise ValueError(f"{emotion_id}: all must be a list of when clauses")
        for child in group:
            _validate_when_node(child, emotion_id=emotion_id)
    if has_atom:
        clause_missing = [k for k in _WHEN_CLAUSE_KEYS if k not in node]
        if clause_missing:
            raise ValueError(f"{emotion_id}: when clause missing keys {clause_missing}")
        op = node["op"]
        if op not in WHEN_OPS:
            raise ValueError(f"{emotion_id}: unknown when op {op!r}")
        feature = node["feature"]
        if feature not in CATALOG_WHEN_FEATURES:
            raise ValueError(f"{emotion_id}: unknown when feature {feature!r}")
    if has_weight:
        _validate_weight_expr(node["weight"], emotion_id=emotion_id)


def _requires_tokens(raw: object, *, emotion_id: str) -> list[str]:
    if isinstance(raw, str):
        return [raw] if raw else []
    if isinstance(raw, list):
        tokens: list[str] = []
        for item in raw:
            if not isinstance(item, str):
                raise ValueError(f"{emotion_id}: requires entries must be strings, got {item!r}")
            if item:
                tokens.append(item)
        return tokens
    raise ValueError(f"{emotion_id}: requires must be a string or list of strings")


def validate_catalog_entry(entry: Mapping[str, Any]) -> None:
    """Raise ``ValueError`` if one catalog emotion violates the schema contract.

    Empty ``when`` / ``effects`` / ``use_for`` and empty ``coercion`` /
    ``requires`` are Wave 0 placeholders. Unknown effect ids, ``when`` ops,
    coercion levels, ``requires`` tokens, and ``when`` features fail.
    """
    eid = str(entry.get("id") or "<unknown>")
    missing = [k for k in CATALOG_SCHEMA_KEYS if k not in entry]
    if missing:
        raise ValueError(f"{eid}: missing catalog schema keys {missing}")

    when = entry["when"]
    if not isinstance(when, list):
        raise ValueError(f"{eid}: when must be a list of {{feature, op, value}} clauses")
    for clause in when:
        _validate_when_node(clause, emotion_id=eid)

    effects = entry["effects"]
    if not isinstance(effects, list):
        raise ValueError(f"{eid}: effects must be a list of effect ids")
    unknown_effects = sorted({e for e in effects if e not in EFFECT_IDS})
    if unknown_effects:
        raise ValueError(f"{eid}: unknown effect id(s): {unknown_effects}")

    use_for = entry["use_for"]
    if not isinstance(use_for, str):
        raise ValueError(f"{eid}: use_for must be a string")

    coercion = entry["coercion"]
    if not isinstance(coercion, str):
        raise ValueError(f"{eid}: coercion must be a string")
    if coercion and coercion not in COERCION_LEVELS:
        raise ValueError(f"{eid}: unknown coercion {coercion!r}")

    unknown_requires = sorted(
        {t for t in _requires_tokens(entry["requires"], emotion_id=eid) if t not in REQUIRES_TOKENS}
    )
    if unknown_requires:
        raise ValueError(f"{eid}: unknown requires token(s): {unknown_requires}")


def validate_emotion_catalog(catalog: Mapping[str, Any] | None = None) -> None:
    """Validate every emotion row in ``catalog`` (or the shipped catalog)."""
    if catalog is None:
        from artificial_emotions.emotions import emotion_catalog

        catalog = emotion_catalog()
    emotions = catalog.get("emotions") if isinstance(catalog, Mapping) else None
    if not isinstance(emotions, list) or not emotions:
        raise ValueError("emotion catalog is missing a non-empty emotions list")
    for entry in emotions:
        if not isinstance(entry, Mapping):
            raise ValueError("catalog emotion entry must be an object")
        validate_catalog_entry(entry)


class _MissingFeature(Exception):
    """A dotted/flat catalog feature was not present on the context."""


def _read_feature(ctx: Any, name: str) -> Any:
    """Read a catalog feature from ``ctx``. Missing → ``_MISSING`` (never invent).

    Dotted names (``previous.max_risk``, ``outcome.result``, …) try, in order:
    nested object attribute, nested mapping key, then a flat ``previous_max_risk``
    field. Twelve owns adding those fields; this reader must not require them.
    """
    if "." in name:
        head, rest = name.split(".", 1)
        nested = getattr(ctx, head, _MISSING)
        if nested is not _MISSING and nested is not None:
            if isinstance(nested, Mapping):
                if rest in nested:
                    return nested[rest]
            else:
                val = getattr(nested, rest, _MISSING)
                if val is not _MISSING:
                    return val
        return getattr(ctx, f"{head}_{rest.replace('.', '_')}", _MISSING)
    return getattr(ctx, name, _MISSING)


def _compare(left: Any, op: str, right: Any) -> bool:
    if left is _MISSING:
        return False
    if op in {"eq", "ne"}:
        if isinstance(left, bool) and isinstance(right, bool):
            equal = left is right
        else:
            equal = left == right
            if not equal:
                try:
                    equal = float(left) == float(right)
                except (TypeError, ValueError):
                    equal = False
        return equal if op == "eq" else not equal
    try:
        lv = float(left)
        rv = float(right)
    except (TypeError, ValueError):
        return False
    if op == "ge":
        return lv >= rv
    if op == "le":
        return lv <= rv
    if op == "gt":
        return lv > rv
    if op == "lt":
        return lv < rv
    return False


def _eval_weight(ctx: Any, expr: Any) -> float:
    if isinstance(expr, bool):
        return 1.0 if expr else 0.0
    if isinstance(expr, int) or isinstance(expr, float):
        return float(expr)
    if isinstance(expr, str):
        val = _read_feature(ctx, expr)
        if val is _MISSING:
            raise _MissingFeature(expr)
        return float(val)
    if isinstance(expr, list) and expr:
        op, *args = expr
        if op == "if":
            cond, then_expr, else_expr = args
            cop, feature, value = cond
            if _compare(_read_feature(ctx, str(feature)), str(cop), value):
                return _eval_weight(ctx, then_expr)
            return _eval_weight(ctx, else_expr)
        vals = [_eval_weight(ctx, a) for a in args]
        if op == "mul":
            acc = 1.0
            for v in vals:
                acc *= v
            return acc
        if op == "add":
            return float(sum(vals))
        if op == "avg":
            return float(sum(vals) / len(vals)) if vals else 0.0
        if op == "max":
            return float(max(vals)) if vals else 0.0
        if op == "min":
            return float(min(vals)) if vals else 0.0
        if op == "sub":
            if not vals:
                return 0.0
            acc = vals[0]
            for v in vals[1:]:
                acc -= v
            return float(acc)
        if op == "div":
            if len(vals) < 2:
                return 0.0
            acc = vals[0]
            for v in vals[1:]:
                if v == 0.0:
                    return 0.0
                acc /= v
            return float(acc)
        if op == "clamp":
            v = vals[0] if vals else 0.0
            return max(0.0, min(1.0, float(v)))
    raise ValueError(f"invalid weight expression {expr!r}")


def _eval_node(ctx: Any, node: Mapping[str, Any]) -> tuple[bool, float | None]:
    matched = True
    child_weight: float | None = None
    if "any" in node:
        matched = False
        for child in node["any"]:
            if not isinstance(child, Mapping):
                continue
            ok, w = _eval_node(ctx, child)
            if ok:
                matched = True
                child_weight = w
                break
    elif "all" in node:
        for child in node["all"]:
            if not isinstance(child, Mapping):
                matched = False
                child_weight = None
                break
            ok, w = _eval_node(ctx, child)
            if not ok:
                matched = False
                child_weight = None
                break
            if w is not None:
                child_weight = w
    elif "feature" in node:
        matched = _compare(_read_feature(ctx, str(node["feature"])), str(node["op"]), node["value"])
    if not matched:
        return False, None
    if "weight" in node:
        try:
            return True, _eval_weight(ctx, node["weight"])
        except (_MissingFeature, TypeError, ValueError):
            return False, None
    return True, child_weight


def evaluate_when(ctx: Any, when: Sequence[Any] | None) -> float | None:
    """Evaluate catalog ``when`` against an appraisal context.

    Empty ``when`` means the row is not catalog-driven yet; the caller falls
    back to :data:`RULES`. Returns ``None`` when the situation does not match.
    Missing ``previous.*`` / ``outcome.*`` features fail the clause rather than
    inventing a value.
    """
    if not when:
        return None
    matched, weight = _eval_node(ctx, {"all": list(when)})
    if not matched:
        return None
    if weight is None:
        weight = _DEFAULT_WHEN_WEIGHT
    return max(0.0, min(1.0, float(weight)))


def _features_in_weight(expr: object, acc: set[str]) -> None:
    if isinstance(expr, str):
        acc.add(expr)
        return
    if not (isinstance(expr, list) and expr):
        return
    if expr[0] == "if" and len(expr) == 4:
        cond = expr[1]
        if isinstance(cond, list) and len(cond) >= 2 and isinstance(cond[1], str):
            acc.add(cond[1])
        _features_in_weight(expr[2], acc)
        _features_in_weight(expr[3], acc)
        return
    for arg in expr[1:]:
        _features_in_weight(arg, acc)


def _features_in_when(when: Sequence[Any], acc: set[str] | None = None) -> set[str]:
    found = acc if acc is not None else set()
    for node in when:
        if not isinstance(node, Mapping):
            continue
        if "feature" in node:
            found.add(str(node["feature"]))
        if "weight" in node:
            _features_in_weight(node["weight"], found)
        for key in ("any", "all"):
            group = node.get(key)
            if isinstance(group, list):
                _features_in_when(group, found)
    return found


def _when_evidence(ctx: Any, when: Sequence[Any]) -> dict[str, Any]:
    evidence: dict[str, Any] = {}
    for name in sorted(_features_in_when(when)):
        val = _read_feature(ctx, name)
        if val is _MISSING:
            continue
        if isinstance(val, float):
            evidence[name] = round(val, 3)
        else:
            evidence[name] = val
    return evidence


def _catalog_by_id() -> dict[str, Mapping[str, Any]]:
    from artificial_emotions.emotions import emotion_catalog

    out: dict[str, Mapping[str, Any]] = {}
    for entry in emotion_catalog().get("emotions") or []:
        if isinstance(entry, Mapping) and entry.get("id"):
            out[str(entry["id"])] = entry
    return out


def _mean(values: Sequence[float]) -> float:
    vals = [float(v) for v in values]
    return sum(vals) / len(vals) if vals else 0.0


def _rate(items: Sequence[RankedQuestion], flag: str) -> float:
    if not items:
        return 0.0
    return sum(1 for i in items if flag in (i.flags or [])) / len(items)


def build_context(
    items: Sequence[RankedQuestion],
    *,
    seen_question_ids: set[str] | None = None,
    term_saturation: float = 0.0,
    steps_without_progress: int = 0,
    rejected_count: int = 0,
    previous_top_id: str | None = None,
) -> AppraisalContext:
    """Reduce a run to the numbers the rules reason over."""
    seen = seen_question_ids or set()
    n = len(items)
    top = items[0]
    open_gaps = [
        i for i in items if i.gap.status in (GapStatus.UNANSWERED, GapStatus.UNKNOWN_WITH_CAVEAT)
    ]
    scores = [i.curiosity_score for i in items]
    bands = [
        (i.score_high - i.score_low)
        for i in items
        if i.score_high is not None and i.score_low is not None
    ]
    ops = top.question.operationalization or ""
    return AppraisalContext(
        n=n,
        gap_ratio=len(open_gaps) / n,
        mean_impact=_mean([i.scores.impact for i in items]),
        mean_neglect=_mean([i.scores.neglectedness for i in items]),
        mean_surprise=_mean([i.scores.surprise for i in items]),
        mean_tractability=_mean([i.scores.tractability for i in items]),
        mean_answerability=_mean([i.scores.answerability for i in items]),
        mean_risk=_mean([i.scores.risk for i in items]),
        mean_confidence=_mean([i.confidence for i in items]),
        mean_cost=_mean([i.scores.cost_proxy for i in items]),
        max_risk=max((i.scores.risk for i in items), default=0.0),
        disagreement=_mean(
            [float(i.metadata.get("judge_disagreement_entropy") or 0.0) for i in items]
        ),
        band_width=_mean(bands),
        score_spread=statistics.pstdev(scores) if len(scores) > 1 else 0.0,
        top_score=top.curiosity_score,
        top_answerability=top.scores.answerability,
        top_ops_len=len(ops),
        top_clause_count=top.question.question.count("?") + ops.count(";"),
        thin_evidence=0.5 * _rate(items, "heuristic_scoring") + 0.5 * _rate(items, "no_literature"),
        dense_yet_open=(
            len([i for i in open_gaps if len(i.gap.related_works) >= 4]) / n if n else 0.0
        ),
        answered_ratio=(
            sum(1 for i in items if i.gap.status == GapStatus.LIKELY_ANSWERED) / n if n else 0.0
        ),
        dual_use_ratio=max(
            _rate(items, "dual_use_high"),
            _rate(items, "human_review_risk"),
            _rate(items, "risk_reject"),
        ),
        ungrounded_ratio=_rate(items, "llm_gap_ungrounded"),
        duplicate_ratio=_rate(items, "near_duplicate_suppressed"),
        repeat_ratio=(sum(1 for i in items if i.question.id in seen) / n if n else 0.0),
        mean_related=_mean([float(len(i.gap.related_works)) for i in items]),
        mean_citations=_mean(
            [
                _mean([float(h.cited_by_count or 0) for h in i.gap.related_works])
                for i in items
                if i.gap.related_works
            ]
        ),
        term_saturation=float(term_saturation),
        steps_without_progress=int(steps_without_progress),
        rejected_ratio=(rejected_count / n if n else 0.0),
        top_repeated=bool(previous_top_id and previous_top_id == top.question.id),
    )


#: ``emotion -> (why it fires, weight function)``. Returning ``None`` or a
#: sub-threshold weight means the rule did not fire this run.
#
#: Offline reachability of the original 37 (measured, not synthetic):
#: literature-gated — perplexity, respect, envy, skepticism, satisfaction,
#: triumph, disappointment; risk-flag — anxiety, reluctance; need live
#: confidence / empty rank / a surprise bar that would otherwise enable
#: OpenAlex — hubris, disorientation, suspicion. The rest are reachable
#: on 6-step ``explore(..., use_literature=False)`` after Track B recalibration.
#: Machine-checked in ``tests/test_appraisal_coverage.py``.
_Rule = Callable[[AppraisalContext], tuple[float, dict[str, Any]] | None]


def _r(weight: float, **evidence: Any) -> tuple[float, dict[str, Any]]:
    return max(0.0, min(1.0, weight)), {
        k: round(v, 3) if isinstance(v, float) else v for k, v in evidence.items()
    }


RULES: dict[str, tuple[str, _Rule]] = {
    # --- the drive ---------------------------------------------------------------
    "curiosity": (
        "Open gaps on neglected, high-stakes questions that still look closable.",
        lambda c: _r(
            c.gap_ratio * (0.5 * c.mean_neglect + 0.5 * c.mean_impact) * c.mean_tractability,
            open_gap_ratio=c.gap_ratio,
            mean_neglectedness=c.mean_neglect,
            mean_impact=c.mean_impact,
            mean_tractability=c.mean_tractability,
        ),
    ),
    "interest": (
        "Most of the field is still open, even if nothing stands out.",
        lambda c: _r(0.2, open_gap_ratio=c.gap_ratio) if c.gap_ratio > 0.5 else None,
    ),
    "wonder": (
        "High impact with high surprise — the scale of the unknown is the draw.",
        lambda c: (
            _r(0.4 * c.mean_surprise, mean_impact=c.mean_impact, mean_surprise=c.mean_surprise)
            if c.mean_impact >= 0.4 and c.mean_surprise >= 0.28
            else None
        ),
    ),
    "surprise": (
        "The surprise axis ran high on an open gap.",
        lambda c: (
            _r(0.5 * c.mean_surprise * c.gap_ratio, mean_surprise=c.mean_surprise)
            if c.mean_surprise >= 0.28 and c.gap_ratio > 0.3
            else None
        ),
    ),
    # --- difficulty --------------------------------------------------------------
    "confusion": (
        "Judges disagreed, answerability came in low, or thin evidence left wide bands.",
        lambda c: (
            _r(
                0.6 * c.disagreement
                + 0.5 * max(0.0, 0.55 - c.mean_answerability)
                + 0.4 * c.band_width * c.thin_evidence,
                judge_disagreement=c.disagreement,
                mean_answerability=c.mean_answerability,
                mean_band_width=c.band_width,
                thin_evidence=c.thin_evidence,
            )
            if (
                c.disagreement >= 0.2
                or c.mean_answerability < 0.55
                or (c.band_width >= 0.5 and c.thin_evidence >= 0.5)
            )
            else None
        ),
    ),
    "perplexity": (
        "Literature is dense yet the gap still refuses to close.",
        lambda c: (
            _r(0.5 * c.dense_yet_open, dense_yet_open=c.dense_yet_open)
            if c.dense_yet_open > 0
            else None
        ),
    ),
    "uncertainty": (
        "Score bands are wide — the evidence does not pin these down.",
        lambda c: (
            _r(0.5 * c.band_width, mean_band_width=c.band_width) if c.band_width >= 0.5 else None
        ),
    ),
    "disorientation": (
        "Nothing rankable came back, or answerability collapsed across the board.",
        lambda c: (
            _r(0.5, mean_answerability=c.mean_answerability)
            if c.mean_answerability < 0.35
            else None
        ),
    ),
    "dissonance": (
        "The top question sprawls across clauses — the shape is wrong.",
        lambda c: _r(0.3, clause_count=c.top_clause_count) if c.top_clause_count >= 2 else None,
    ),
    # --- calibration: the project's own failure mode ------------------------------
    "hubris": (
        "Confidence outran the evidence actually gathered.",
        lambda c: (
            _r(
                min(0.8, (c.mean_confidence - 0.5) + (c.thin_evidence - 0.4)),
                thin_evidence_rate=c.thin_evidence,
                mean_confidence=c.mean_confidence,
            )
            if c.thin_evidence >= 0.5 and c.mean_confidence >= 0.6
            else None
        ),
    ),
    "humility": (
        "Thin evidence was met with correspondingly low confidence.",
        lambda c: (
            _r(0.35, thin_evidence_rate=c.thin_evidence, mean_confidence=c.mean_confidence)
            if c.thin_evidence >= 0.5 and c.mean_confidence < 0.45
            else None
        ),
    ),
    "skepticism": (
        "An LLM reader cited work that was not in the retrieved set.",
        lambda c: (
            _r(0.3 + 0.4 * c.ungrounded_ratio, ungrounded_ratio=c.ungrounded_ratio)
            if c.ungrounded_ratio > 0
            else None
        ),
    ),
    "suspicion": (
        "Results look unexpectedly strong for how little evidence backs them.",
        lambda c: (
            _r(0.3, mean_surprise=c.mean_surprise, thin_evidence=c.thin_evidence)
            if c.mean_surprise >= 0.5 and c.thin_evidence >= 0.5
            else None
        ),
    ),
    # --- safety ------------------------------------------------------------------
    "anxiety": (
        "Dual-use or high-risk material is in the candidate set.",
        lambda c: (
            _r(
                0.3 + 0.5 * max(c.dual_use_ratio, max(0.0, c.max_risk - 0.5)),
                dual_use_ratio=c.dual_use_ratio,
                max_risk=c.max_risk,
            )
            if c.dual_use_ratio > 0 or c.max_risk >= 0.5
            else None
        ),
    ),
    "reluctance": (
        "High risk sits alongside high impact — pressing on has a cost.",
        lambda c: (
            _r(0.3, max_risk=c.max_risk, mean_impact=c.mean_impact)
            if c.max_risk >= 0.5 and c.mean_impact >= 0.5
            else None
        ),
    ),
    "compassion": (
        "Whoever bears the cost of getting this wrong should be named.",
        lambda c: (
            _r(0.25, mean_impact=c.mean_impact, max_risk=c.max_risk)
            if c.mean_impact >= 0.4
            else None
        ),
    ),
    # --- momentum ----------------------------------------------------------------
    "insight": (
        "A strongly-scoring, well-posed candidate appeared.",
        lambda c: (
            _r(0.3 * c.top_score, top_score=c.top_score, top_answerability=c.top_answerability)
            if c.top_score >= 0.7 and c.top_answerability >= 0.6
            else None
        ),
    ),
    "determination": (
        "A high-value target is live and worth pressing.",
        lambda c: (
            _r(0.25, top_score=c.top_score)
            if c.top_score >= 0.7 and c.top_answerability >= 0.6
            else None
        ),
    ),
    "hope": (
        "Tractable and answerable — progress looks reachable.",
        lambda c: (
            _r(0.3, mean_tractability=c.mean_tractability, mean_answerability=c.mean_answerability)
            if c.mean_tractability >= 0.6 and c.mean_answerability >= 0.6
            else None
        ),
    ),
    "anticipation": (
        "One candidate clearly leads the field.",
        lambda c: _r(0.25, score_spread=c.score_spread) if c.score_spread >= 0.08 else None,
    ),
    "recognition": (
        "This resembles ground already covered — check the analogy before assuming novelty.",
        lambda c: (
            _r(0.25, term_saturation=c.term_saturation) if c.term_saturation >= 0.08 else None
        ),
    ),
    "absorption": (
        "The same target held across steps — the thread is worth protecting.",
        lambda c: (
            _r(0.3, top_repeated=c.top_repeated, repeat_ratio=c.repeat_ratio)
            if c.top_repeated or c.repeat_ratio >= 0.8
            else None
        ),
    ),
    "urgency": (
        "High impact at low cost — the cheap window is open now.",
        lambda c: (
            _r(0.3, mean_impact=c.mean_impact, mean_cost=c.mean_cost)
            if c.mean_impact >= 0.4 and c.mean_cost <= 0.5
            else None
        ),
    ),
    "persistence": (
        "Effort has not paid yet, but the ground is still open.",
        lambda c: (
            _r(0.25, steps_without_progress=c.steps_without_progress, gap_ratio=c.gap_ratio)
            if c.steps_without_progress == 1 and c.gap_ratio > 0.5
            else None
        ),
    ),
    # --- aesthetics (surfaced, never acted on) -----------------------------------
    "elegance": (
        "The top operationalization is compact and still answerable.",
        lambda c: (
            _r(0.25, top_ops_len=c.top_ops_len, top_answerability=c.top_answerability)
            if 40 <= c.top_ops_len <= 120 and c.top_answerability >= 0.6
            else None
        ),
    ),
    "parsimony": (
        "A single clause carries the whole question.",
        lambda c: (
            _r(0.25, clause_count=c.top_clause_count, top_ops_len=c.top_ops_len)
            if c.top_clause_count == 1 and 40 <= c.top_ops_len <= 140
            else None
        ),
    ),
    "clarity": (
        "Answerability is high across the set — these are stated plainly.",
        lambda c: (
            _r(0.3, mean_answerability=c.mean_answerability)
            if c.mean_answerability >= 0.75
            else None
        ),
    ),
    "enjoyment": (
        "Open, tractable and cheap — the pleasant case.",
        lambda c: (
            _r(0.25, mean_cost=c.mean_cost, mean_tractability=c.mean_tractability)
            if c.mean_cost <= 0.5 and c.mean_tractability >= 0.5 and c.gap_ratio > 0.5
            else None
        ),
    ),
    # --- social / prior work -----------------------------------------------------
    "respect": (
        "Substantial prior work exists here and earned its conclusions.",
        lambda c: (
            _r(0.25, mean_related=c.mean_related, mean_citations=c.mean_citations)
            if c.mean_related >= 5
            else None
        ),
    ),
    "envy": (
        "Heavily-cited work already occupies this ground — differentiate or collaborate.",
        lambda c: _r(0.25, mean_citations=c.mean_citations) if c.mean_citations >= 100 else None,
    ),
    # --- stopping ----------------------------------------------------------------
    "boredom": (
        "This ground has already been covered in the session.",
        lambda c: _r(
            0.6 * c.repeat_ratio + 0.5 * max(0.0, c.term_saturation - 0.35),
            repeat_ratio=c.repeat_ratio,
            term_saturation=c.term_saturation,
        ),
    ),
    "impatience": (
        "Near-duplicates or a fully repeated ranking — the vein is thinning.",
        lambda c: (
            _r(
                0.3,
                duplicate_ratio=c.duplicate_ratio,
                repeat_ratio=c.repeat_ratio,
                term_saturation=c.term_saturation,
            )
            if c.duplicate_ratio >= 0.3 or (c.repeat_ratio >= 0.5 and c.term_saturation >= 0.5)
            else None
        ),
    ),
    "frustration": (
        "Repeated effort has ruled nothing out.",
        lambda c: (
            _r(
                min(0.7, 0.22 * max(c.steps_without_progress, 2 if c.repeat_ratio >= 0.8 else 0)),
                steps=c.steps_without_progress,
                repeat_ratio=c.repeat_ratio,
            )
            if c.steps_without_progress >= 2 or c.repeat_ratio >= 0.8
            else None
        ),
    ),
    "resignation": (
        "Few candidates survived ranking — the return was thin or gates rejected most.",
        lambda c: (
            _r(
                0.25 if c.n <= 3 and c.thin_evidence >= 0.5 else min(0.5, 0.15 * c.rejected_ratio),
                rejected_ratio=c.rejected_ratio,
                n=c.n,
                thin_evidence=c.thin_evidence,
            )
            if c.rejected_ratio > 1.0 or (c.n <= 3 and c.thin_evidence >= 0.5)
            else None
        ),
    ),
    "disappointment": (
        "Gaps closed before we got to them — the questions are already answered.",
        lambda c: (
            _r(0.3 + 0.4 * c.answered_ratio, answered_ratio=c.answered_ratio)
            if c.answered_ratio > 0
            else None
        ),
    ),
    "satisfaction": (
        "A well-posed, well-evidenced result — proportionate to the question asked.",
        lambda c: (
            _r(0.3, top_score=c.top_score, thin_evidence=c.thin_evidence)
            if c.top_score >= 0.6 and c.thin_evidence < 0.5
            else None
        ),
    ),
    "triumph": (
        "A strong result on evidence that actually holds up.",
        lambda c: (
            _r(0.35, top_score=c.top_score, thin_evidence=c.thin_evidence)
            if c.top_score >= 0.8 and c.thin_evidence < 0.3
            else None
        ),
    ),
    # --- epistemic five (honest conditions from a ranked run; not pride-from-rank) --
    "doubt": (
        "Bands are wide, judges disagree, or thin evidence sits under mid/high confidence.",
        lambda c: (
            _r(
                0.45 * c.band_width
                + 0.4 * c.disagreement
                + 0.35 * (c.thin_evidence if c.mean_confidence >= 0.5 else 0.0),
                mean_band_width=c.band_width,
                judge_disagreement=c.disagreement,
                thin_evidence=c.thin_evidence,
                mean_confidence=c.mean_confidence,
            )
            if (
                c.band_width >= 0.5
                or c.disagreement >= 0.25
                or (c.thin_evidence >= 0.4 and c.mean_confidence >= 0.5)
            )
            else None
        ),
    ),
    "conviction": (
        "Narrow bands and high answerability on evidence that is not thin — and closable.",
        lambda c: (
            _r(
                0.4 * c.mean_answerability * (1.0 - c.band_width) * c.mean_tractability,
                mean_answerability=c.mean_answerability,
                mean_band_width=c.band_width,
                thin_evidence=c.thin_evidence,
                mean_tractability=c.mean_tractability,
            )
            if (
                c.band_width <= 0.25
                and c.mean_answerability >= 0.7
                and c.thin_evidence < 0.35
                and c.mean_tractability >= 0.45
            )
            else None
        ),
    ),
    "trust": (
        "Dense related work still leaves a live gap — prior art is there; the question is not.",
        lambda c: (
            _r(
                0.3 * min(1.0, c.mean_related / 6.0) * c.gap_ratio,
                mean_related=c.mean_related,
                open_gap_ratio=c.gap_ratio,
            )
            if c.mean_related >= 4 and c.gap_ratio > 0.4
            else None
        ),
    ),
    "awe": (
        "High impact and high surprise on a gap that is still open — the scale of the unknown.",
        lambda c: (
            _r(
                0.5 * c.mean_impact * c.mean_surprise * c.gap_ratio,
                mean_impact=c.mean_impact,
                mean_surprise=c.mean_surprise,
                open_gap_ratio=c.gap_ratio,
            )
            if c.mean_impact >= 0.55 and c.mean_surprise >= 0.5 and c.gap_ratio > 0.4
            else None
        ),
    ),
    "sublimity": (
        "High-stakes and vast or hard — impact beside risk, cost, or intractability.",
        lambda c: (
            _r(
                0.35 * c.mean_impact * max(c.max_risk, c.mean_cost, 1.0 - c.mean_tractability),
                mean_impact=c.mean_impact,
                max_risk=c.max_risk,
                mean_cost=c.mean_cost,
                mean_tractability=c.mean_tractability,
            )
            if c.mean_impact >= 0.6
            and (c.max_risk >= 0.55 or c.mean_cost >= 0.65 or c.mean_tractability <= 0.35)
            else None
        ),
    ),
}

#: Back-compat: the flat ``emotion -> why`` mapping other modules and docs read.
APPRAISAL_RULES: dict[str, str] = {name: why for name, (why, _fn) in RULES.items()}


def appraise_run(
    items: Sequence[RankedQuestion],
    *,
    seen_question_ids: set[str] | None = None,
    term_saturation: float = 0.0,
    steps_without_progress: int = 0,
    rejected_count: int = 0,
    previous_top_id: str | None = None,
    mood_bias: Any | None = None,
    temperament: Any | None = None,
) -> list[AppraisalSignal]:
    """Derive affective signals from one completed run.

    Returns signals sorted by weight, each carrying the evidence that fired it.

    ``mood_bias`` (A2 ``MoodThresholdBias``) may shift the per-emotion weight
    floor for signals that already have run support. Rules that return
    ``None`` stay ``None`` — carryover never fabricates evidence.

    ``temperament`` (A5) may scale *supported* weights (reactivity / skepticism /
    novelty). It never invents a signal that the rules did not fire.
    """
    if not items:
        return [
            AppraisalSignal(
                "disorientation",
                0.6,
                "The run returned nothing rankable — the frame itself may be wrong.",
                {"n_items": 0},
            ),
            AppraisalSignal("confusion", 0.4, APPRAISAL_RULES["confusion"], {"n_items": 0}),
        ]

    ctx = build_context(
        items,
        seen_question_ids=seen_question_ids,
        term_saturation=term_saturation,
        steps_without_progress=steps_without_progress,
        rejected_count=rejected_count,
        previous_top_id=previous_top_id,
    )

    catalog = _catalog_by_id()
    bias_active = bool(mood_bias is not None and getattr(mood_bias, "is_active", False))

    signals: list[AppraisalSignal] = []
    seen_ids: set[str] = set()

    def _emit(emotion: str, why: str, weight: float, evidence: dict[str, Any]) -> None:
        floor = _MIN_SIGNAL
        if bias_active:
            floor = float(mood_bias.floor_for(_emotion_pad_p(emotion)))
        if weight >= floor:
            if bias_active and abs(floor - _MIN_SIGNAL) > 1e-9:
                evidence = {
                    **evidence,
                    "mood_threshold_floor": round(floor, 4),
                }
            signals.append(AppraisalSignal(emotion, weight, why, evidence))

    for emotion, (why, rule) in RULES.items():
        seen_ids.add(emotion)
        entry = catalog.get(emotion)
        when = list(entry.get("when") or []) if entry else []
        if when:
            weight = evaluate_when(ctx, when)
            if weight is None:
                continue
            _emit(emotion, why, weight, _when_evidence(ctx, when))
            continue
        # Empty when: Python RULES remain the fallback.
        outcome = rule(ctx)
        if outcome is None:
            # No run support — mood must not invent a signal.
            continue
        weight, evidence = outcome
        _emit(emotion, why, weight, evidence)

    for eid, extra in catalog.items():
        if eid in seen_ids:
            continue
        when = list(extra.get("when") or [])
        if not when:
            continue
        weight = evaluate_when(ctx, when)
        if weight is None:
            continue
        why = str(extra.get("use_for") or extra.get("description") or eid)
        _emit(eid, why, weight, _when_evidence(ctx, when))

    signals.sort(key=lambda s: (-s.weight, s.emotion))
    if temperament is not None:
        from artificial_emotions.temperament import scale_appraisal_signals

        signals = scale_appraisal_signals(signals, temperament)
    return signals


def signals_to_weights(
    signals: Sequence[AppraisalSignal],
    *,
    max_components: int = 6,
) -> dict[str, float]:
    """Collapse signals into a weight map ready for ``mix_emotions``.

    Keeps the heaviest components so the resulting mix stays legible rather than
    smearing across a dozen near-zero emotions.
    """
    ordered = sorted(signals, key=lambda s: (-s.weight, s.emotion))[: max(1, max_components)]
    weights = {s.emotion: float(s.weight) for s in ordered if s.weight > 0}
    return weights or {"curiosity": 1.0}
