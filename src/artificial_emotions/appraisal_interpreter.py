"""Catalog ``when`` interpreter and appraisal context.

Callers import from ``artificial_emotions.appraisal`` (stable). This module is
the internal seam: schema vocabularies, :class:`AppraisalContext`, catalog
validation, and :func:`evaluate_when`. Production dispatch still lives in
``appraisal.appraise_run``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, fields
from typing import Any

__all__ = [
    "CATALOG_SCHEMA_KEYS",
    "CATALOG_WHEN_FEATURES",
    "COERCION_LEVELS",
    "EFFECT_IDS",
    "REQUIRES_TOKENS",
    "WEIGHT_EXPR_OPS",
    "WHEN_OPS",
    "AppraisalContext",
    "context_feature",
    "evaluate_when",
    "validate_catalog_entry",
    "validate_emotion_catalog",
    "when_evidence",
]

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

    Wave 1 previous/outcome fields (dotted catalog names in parentheses):
    ``previous_max_risk`` (``previous.max_risk``),
    ``previous_hubris`` (``previous.hubris``),
    ``previous_top_id`` (``previous.top_id``),
    ``outcome_result`` (``outcome.result``),
    ``outcome_question_id`` (``outcome.question_id``).
    Empty ``outcome_result`` / ``outcome_question_id`` means unset — do not
    treat them as a fabricated outcome. Read via :func:`context_feature`.
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
    previous_max_risk: float = 0.0
    previous_hubris: float = 0.0
    previous_top_id: str = ""
    outcome_result: str = ""
    outcome_question_id: str = ""


#: Dotted catalog ``when`` names → :class:`AppraisalContext` fields.
_DOTTED_FEATURE_FIELDS: dict[str, str] = {
    "previous.max_risk": "previous_max_risk",
    "previous.hubris": "previous_hubris",
    "previous.top_id": "previous_top_id",
    "outcome.result": "outcome_result",
    "outcome.question_id": "outcome_question_id",
}


#: Feature names catalog ``when`` clauses may address.
#:
#: :class:`AppraisalContext` fields plus dotted aliases for previous/outcome.
#: Interpreter reads these via :func:`context_feature`. Do not invent extra
#: names here without adding the matching context field.
CATALOG_WHEN_FEATURES: frozenset[str] = frozenset(
    {f.name for f in fields(AppraisalContext)} | set(_DOTTED_FEATURE_FIELDS)
)


def context_feature(ctx: AppraisalContext, name: str) -> Any:
    """Read a catalog ``when`` feature, including dotted previous/outcome paths.

    ``outcome.result`` is stripped and lowercased. Empty strings mean unset,
    not a fabricated outcome. This is a getter only — matching is
    :func:`evaluate_when`; run dispatch is ``appraisal.appraise_run``.

    ``eq`` / ``ne`` against a list ``value`` is membership (pride/shame
    result sets). :func:`evaluate_when` honours that when evaluating ``when``.
    """
    field_name = _DOTTED_FEATURE_FIELDS.get(name, name)
    value = getattr(ctx, field_name)
    if field_name == "outcome_result":
        return str(value or "").strip().lower()
    if field_name in {"outcome_question_id", "previous_top_id"}:
        return str(value or "").strip()
    return value


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

    :class:`AppraisalContext` goes through :func:`context_feature` (Twelve's
    previous/outcome fields, ``outcome.result`` normalized). Other objects try
    nested ``previous.*`` / ``outcome.*`` then a flat ``previous_max_risk``
    field so Interpreter tests can pass a SimpleNamespace.
    """
    if isinstance(ctx, AppraisalContext):
        try:
            return context_feature(ctx, name)
        except AttributeError:
            return _MISSING
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
        if isinstance(right, list):
            # Membership: pride (partial_progress|answered), shame
            # (contradicted|already_answered). A list ``value`` is a set of
            # allowed tokens, not a scalar to compare against.
            member = left in right
            if not member:
                for item in right:
                    try:
                        if float(left) == float(item):
                            member = True
                            break
                    except (TypeError, ValueError):
                        continue
            return member if op == "eq" else not member
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

    Empty ``when`` does not match. Returns ``None`` when the situation does not
    match. Missing ``previous.*`` / ``outcome.*`` features fail the clause rather
    than inventing a value. ``eq`` / ``ne`` against a list ``value`` is membership.
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


def when_evidence(ctx: Any, when: Sequence[Any]) -> dict[str, Any]:
    """Feature snapshot for a matching ``when`` tree (never invents missing values)."""
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
