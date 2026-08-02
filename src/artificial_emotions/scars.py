"""A4 Scars and affinities — idiosyncrasy from history.

A scar: domain/question where runs repeatedly went nowhere. Raises the bar
for returning. Decays slowly.

An affinity: ground that repeatedly paid off. Slight pull back toward it.

Both are biases with stated magnitude, capped like ``MAX_WEIGHT_DELTA``, and
always disclosed in the run payload when they influence behaviour.
``CURIOSITY_NO_MEMORY=1`` / empty history keep today's byte-identical path.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from artificial_emotions.models import CuriosityConfig
from artificial_emotions.modulate import MAX_WEIGHT_DELTA

__all__ = [
    "MAX_AFFINITY_BIAS",
    "MAX_SCAR_BIAS",
    "MIN_ACTIVE_STRENGTH",
    "MIN_HITS_FOR_AFFINITY",
    "MIN_HITS_FOR_SCAR",
    "SCAR_HALF_LIFE_HOURS",
    "BiasApplication",
    "apply_history_biases",
    "decay_factor",
    "decayed_strength",
    "disclosure_payload",
    "next_domain_biased",
    "plain_affinity",
    "plain_scar",
    "update_from_explore_result",
]

#: Same ceiling as modulate weight deltas — scars nudge; they never dominate.
MAX_SCAR_BIAS = MAX_WEIGHT_DELTA  # 0.08

#: Affinities are a slight pull — half the scar ceiling.
MAX_AFFINITY_BIAS = MAX_WEIGHT_DELTA / 2.0  # 0.04

#: Slow decay — weeks, not hours (mood is hours; scars linger).
SCAR_HALF_LIFE_HOURS = 24.0 * 21.0  # three weeks

#: Below this residual strength the entry stops mattering.
MIN_ACTIVE_STRENGTH = 0.02

#: "Repeatedly" — one bad/good session never scars or binds.
MIN_HITS_FOR_SCAR = 2
MIN_HITS_FOR_AFFINITY = 2

_LOW_SCORE = 0.40
_HIGH_SCORE = 0.70
_JUMP_ORDER: dict[str, str] = {
    "ai": "biology",
    "biology": "materials",
    "materials": "climate",
    "climate": "energy",
    "energy": "physics",
    "physics": "medicine",
    "medicine": "social",
    "social": "ai",
    "general": "ai",
}


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _parse_iso(stamp: str | None) -> datetime | None:
    if not stamp:
        return None
    try:
        dt = datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


def decay_factor(
    updated_at: str | None,
    *,
    now: datetime | None = None,
    half_life_hours: float = SCAR_HALF_LIFE_HOURS,
) -> float:
    """Exponential decay factor toward zero (1.0 = fresh, →0 over half-lives)."""
    stamped = _parse_iso(updated_at)
    if stamped is None:
        return 1.0
    at = now or _utc_now()
    elapsed_h = max(0.0, (at - stamped).total_seconds() / 3600.0)
    half = max(1e-6, float(half_life_hours))
    return float(math.pow(0.5, elapsed_h / half))


def decayed_strength(
    strength: float,
    updated_at: str | None,
    *,
    now: datetime | None = None,
    half_life_hours: float = SCAR_HALF_LIFE_HOURS,
) -> tuple[float, float]:
    """Return ``(decayed_strength, decay_factor)``."""
    factor = decay_factor(updated_at, now=now, half_life_hours=half_life_hours)
    return max(0.0, float(strength) * factor), factor


def plain_scar(entry: dict[str, Any], *, strength: float | None = None) -> str:
    """Plain-language description of a scar for ``emotions memory show``."""
    target = str(entry.get("target") or "?")
    kind = str(entry.get("kind") or "domain")
    hits = int(entry.get("hits") or 0)
    residual = float(strength) if strength is not None else float(entry.get("strength") or 0.0)
    where = f"Domain '{target}'" if kind == "domain" else f"Question '{target}'"
    return (
        f"{where} went nowhere {hits} time(s) "
        f"(residual strength {residual:.2f}) — raising the bar to return."
    )


def plain_affinity(entry: dict[str, Any], *, strength: float | None = None) -> str:
    """Plain-language description of an affinity."""
    target = str(entry.get("target") or "?")
    kind = str(entry.get("kind") or "domain")
    hits = int(entry.get("hits") or 0)
    residual = float(strength) if strength is not None else float(entry.get("strength") or 0.0)
    where = f"Domain '{target}'" if kind == "domain" else f"Question '{target}'"
    return (
        f"{where} paid off {hits} time(s) "
        f"(residual strength {residual:.2f}) — slight pull to return."
    )


@dataclass(frozen=True)
class BiasApplication:
    """One disclosed scar/affinity nudge applied to this run."""

    kind: str  # "scar" | "affinity"
    target: str
    target_kind: str  # "domain" | "question"
    magnitude: float
    knob: str
    before: Any
    after: Any
    plain: str
    decay_factor: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "target": self.target,
            "target_kind": self.target_kind,
            "magnitude": round(float(self.magnitude), 6),
            "knob": self.knob,
            "before": self.before,
            "after": self.after,
            "plain": self.plain,
            "decay_factor": round(float(self.decay_factor), 6),
            "bounded_by": f"|magnitude| <= {MAX_SCAR_BIAS}",
        }


def _active(
    entries: list[dict[str, Any]],
    *,
    now: datetime | None,
    half_life_hours: float,
    min_hits: int = 1,
) -> list[tuple[dict[str, Any], float, float]]:
    out: list[tuple[dict[str, Any], float, float]] = []
    for entry in entries or []:
        if not isinstance(entry, dict):
            continue
        if int(entry.get("hits") or 0) < int(min_hits):
            continue
        strength, factor = decayed_strength(
            float(entry.get("strength") or 0.0),
            entry.get("updated_at"),
            now=now,
            half_life_hours=half_life_hours,
        )
        if strength < MIN_ACTIVE_STRENGTH:
            continue
        out.append((entry, strength, factor))
    return out


def _magnitude(strength: float, ceiling: float) -> float:
    return min(float(ceiling), max(0.0, float(strength) * float(ceiling)))


def apply_history_biases(
    config: CuriosityConfig,
    scars: list[dict[str, Any]] | None,
    affinities: list[dict[str, Any]] | None,
    *,
    now: datetime | None = None,
    half_life_hours: float = SCAR_HALF_LIFE_HOURS,
) -> tuple[CuriosityConfig, list[BiasApplication]]:
    """Raise the bar on scarred ground; slight pull on affinities. Bounded + listed."""
    domain = str(config.domain).lower()
    profile = config.value_profile
    updates: dict[str, Any] = {}
    applied: list[BiasApplication] = []

    for entry, strength, factor in _active(
        list(scars or []),
        now=now,
        half_life_hours=half_life_hours,
        min_hits=MIN_HITS_FOR_SCAR,
    ):
        target = str(entry.get("target") or "").lower()
        kind = str(entry.get("kind") or "domain")
        if kind != "domain" or target != domain:
            continue
        mag = _magnitude(strength, MAX_SCAR_BIAS)
        if mag <= 0:
            continue
        before = float(profile.min_answerability)
        after = round(min(1.0, before + mag), 6)
        if after == before:
            continue
        profile = profile.model_copy(update={"min_answerability": after})
        updates["value_profile"] = profile
        # Fewer candidates = higher bar for what surfaces from scarred ground.
        before_n = int(config.n_candidates)
        after_n = max(4, before_n - max(1, int(round(mag / MAX_SCAR_BIAS * 2))))
        if after_n != before_n:
            updates["n_candidates"] = after_n
            applied.append(
                BiasApplication(
                    kind="scar",
                    target=target,
                    target_kind="domain",
                    magnitude=mag,
                    knob="n_candidates",
                    before=before_n,
                    after=after_n,
                    plain=plain_scar(entry, strength=strength),
                    decay_factor=factor,
                )
            )
        applied.append(
            BiasApplication(
                kind="scar",
                target=target,
                target_kind="domain",
                magnitude=mag,
                knob="value_profile.min_answerability",
                before=before,
                after=after,
                plain=plain_scar(entry, strength=strength),
                decay_factor=factor,
            )
        )

    for entry, strength, factor in _active(
        list(affinities or []),
        now=now,
        half_life_hours=half_life_hours,
        min_hits=MIN_HITS_FOR_AFFINITY,
    ):
        target = str(entry.get("target") or "").lower()
        kind = str(entry.get("kind") or "domain")
        if kind != "domain" or target != domain:
            continue
        mag = _magnitude(strength, MAX_AFFINITY_BIAS)
        if mag <= 0:
            continue
        before = float(profile.min_answerability)
        after = round(max(0.0, before - mag), 6)
        if after == before:
            continue
        profile = profile.model_copy(update={"min_answerability": after})
        updates["value_profile"] = profile
        applied.append(
            BiasApplication(
                kind="affinity",
                target=target,
                target_kind="domain",
                magnitude=mag,
                knob="value_profile.min_answerability",
                before=before,
                after=after,
                plain=plain_affinity(entry, strength=strength),
                decay_factor=factor,
            )
        )

    if not updates:
        return config, applied
    return config.model_copy(update=updates), applied


def next_domain_biased(
    current: str,
    visited: list[str],
    *,
    scars: list[dict[str, Any]] | None = None,
    affinities: list[dict[str, Any]] | None = None,
    now: datetime | None = None,
    half_life_hours: float = SCAR_HALF_LIFE_HOURS,
) -> tuple[str, BiasApplication | None]:
    """Pick next ground: prefer affinities, avoid scars when alternatives exist."""
    scarred = {
        str(e.get("target") or "").lower()
        for e, _s, _f in _active(
            list(scars or []),
            now=now,
            half_life_hours=half_life_hours,
            min_hits=MIN_HITS_FOR_SCAR,
        )
        if str(e.get("kind") or "domain") == "domain"
    }
    preferred = {
        str(e.get("target") or "").lower()
        for e, _s, _f in _active(
            list(affinities or []),
            now=now,
            half_life_hours=half_life_hours,
            min_hits=MIN_HITS_FOR_AFFINITY,
        )
        if str(e.get("kind") or "domain") == "domain"
    }

    def _default_next(cur: str, seen: list[str]) -> str:
        candidate = _JUMP_ORDER.get(str(cur).lower(), "general")
        for _ in range(len(_JUMP_ORDER)):
            if candidate not in seen:
                return candidate
            candidate = _JUMP_ORDER.get(candidate, "general")
        return candidate

    default = _default_next(current, visited)

    # Affinity pull: first unvisited preferred domain in jump order from current.
    if preferred:
        probe = _JUMP_ORDER.get(str(current).lower(), "general")
        for _ in range(len(_JUMP_ORDER)):
            if probe in preferred and probe not in visited:
                if probe != default:
                    return probe, BiasApplication(
                        kind="affinity",
                        target=probe,
                        target_kind="domain",
                        magnitude=_magnitude(1.0, MAX_AFFINITY_BIAS),
                        knob="domain",
                        before=default,
                        after=probe,
                        plain=(
                            f"Domain '{probe}' paid off before — slight pull "
                            f"away from default jump '{default}'."
                        ),
                        decay_factor=1.0,
                    )
                return probe, None
            probe = _JUMP_ORDER.get(probe, "general")

    # Scar avoidance: skip scarred candidates when another unvisited option exists.
    candidate = _JUMP_ORDER.get(str(current).lower(), "general")
    chosen = default
    for _ in range(len(_JUMP_ORDER)):
        if candidate not in visited and candidate not in scarred:
            chosen = candidate
            break
        if candidate not in visited and not scarred:
            chosen = candidate
            break
        candidate = _JUMP_ORDER.get(candidate, "general")
    else:
        # All remaining are scarred (or none left) — fall back to default.
        chosen = default
        for alt in _JUMP_ORDER:
            if alt not in visited and alt not in scarred:
                chosen = alt
                break

    if chosen != default and default in scarred:
        # Find strength of the scar that blocked the default.
        block_strength = 1.0
        block_factor = 1.0
        block_entry: dict[str, Any] = {"target": default, "kind": "domain", "hits": 0}
        for entry, strength, factor in _active(
            list(scars or []),
            now=now,
            half_life_hours=half_life_hours,
            min_hits=MIN_HITS_FOR_SCAR,
        ):
            if (
                str(entry.get("kind") or "domain") == "domain"
                and str(entry.get("target") or "").lower() == default
            ):
                block_strength = strength
                block_factor = factor
                block_entry = entry
                break
        mag = _magnitude(block_strength, MAX_SCAR_BIAS)
        return chosen, BiasApplication(
            kind="scar",
            target=default,
            target_kind="domain",
            magnitude=mag,
            knob="domain",
            before=default,
            after=chosen,
            plain=plain_scar(block_entry, strength=block_strength) + f" Skipping to '{chosen}'.",
            decay_factor=block_factor,
        )
    return chosen, None


def disclosure_payload(applications: list[BiasApplication]) -> dict[str, Any] | None:
    """Run-payload block. ``None`` when nothing influenced the run (byte-identical)."""
    if not applications:
        return None
    mags = [abs(float(a.magnitude)) for a in applications]
    return {
        "biases": [a.to_dict() for a in applications],
        "max_bias": MAX_SCAR_BIAS,
        "max_affinity_bias": MAX_AFFINITY_BIAS,
        "half_life_hours": SCAR_HALF_LIFE_HOURS,
        "peak_magnitude": round(max(mags), 6),
        "honesty": "history_bias_not_evidence",
        "claims_not": [
            "that past failure proves a domain is empty",
            "phenomenal feeling or lived reluctance",
            "biological emotion",
        ],
    }


def _session_quality(result: dict[str, Any]) -> tuple[str, float, bool]:
    """Return ``(domain, best_score, went_nowhere)`` for scar/affinity updates."""
    domain = str(result.get("domain_started") or "general").lower()
    best = result.get("best_found") or {}
    score = float(best.get("curiosity_score") or 0.0)
    steps = (result.get("trajectory") or {}).get("steps") or []
    if steps:
        progress = sum(1 for s in steps if s.get("made_progress"))
        stagnant = progress == 0 or progress < max(1, len(steps) // 2)
    else:
        stagnant = True
    stopped = str(result.get("stopped_because") or "").lower()
    dead_stop = any(
        token in stopped for token in ("dead end", "frustration", "resignation", "exhaust")
    )
    went_nowhere = stagnant or dead_stop or score < _LOW_SCORE
    paid_off = (not went_nowhere) and score >= _HIGH_SCORE and not stagnant
    # paid_off wins over nowhere when score is strong and there was progress.
    if paid_off:
        went_nowhere = False
    return domain, score, went_nowhere


def _bump_entry(
    entries: list[dict[str, Any]],
    *,
    target: str,
    kind: str,
    now_iso: str,
    delta_strength: float = 0.35,
) -> list[dict[str, Any]]:
    """Increment hits / strength for matching target, or append."""
    out = [dict(e) for e in entries if isinstance(e, dict)]
    for entry in out:
        if (
            str(entry.get("target") or "").lower() == target
            and str(entry.get("kind") or "domain") == kind
        ):
            entry["hits"] = int(entry.get("hits") or 0) + 1
            entry["strength"] = min(
                1.0, float(entry.get("strength") or 0.0) + float(delta_strength)
            )
            entry["updated_at"] = now_iso
            return out
    out.append(
        {
            "target": target,
            "kind": kind,
            "hits": 1,
            "strength": min(1.0, float(delta_strength)),
            "updated_at": now_iso,
        }
    )
    return out


def _prune_inactive(
    entries: list[dict[str, Any]],
    *,
    min_hits: int,
    now: datetime | None,
    half_life_hours: float,
) -> list[dict[str, Any]]:
    """Keep entries that either are not yet mature or still have residual strength."""
    kept: list[dict[str, Any]] = []
    for entry in entries:
        hits = int(entry.get("hits") or 0)
        strength, _ = decayed_strength(
            float(entry.get("strength") or 0.0),
            entry.get("updated_at"),
            now=now,
            half_life_hours=half_life_hours,
        )
        if hits < min_hits:
            # Immature — keep counting toward the threshold.
            kept.append(entry)
        elif strength >= MIN_ACTIVE_STRENGTH:
            kept.append(entry)
        # else: fully decayed mature entry — drop
    return kept


def update_from_explore_result(
    scars: list[dict[str, Any]],
    affinities: list[dict[str, Any]],
    result: dict[str, Any],
    *,
    now: datetime | None = None,
    half_life_hours: float = SCAR_HALF_LIFE_HOURS,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Fold one explore result into scar/affinity lists (domain-level)."""
    at = now or _utc_now()
    now_iso = at.isoformat()
    domain, _score, went_nowhere = _session_quality(result)

    new_scars = list(scars or [])
    new_affinities = list(affinities or [])

    if went_nowhere:
        new_scars = _bump_entry(
            new_scars, target=domain, kind="domain", now_iso=now_iso, delta_strength=0.4
        )
        # Opposing signal: a nowhere run slightly weakens affinity on same ground.
        for entry in new_affinities:
            if (
                str(entry.get("target") or "").lower() == domain
                and str(entry.get("kind") or "domain") == "domain"
            ):
                entry["strength"] = max(0.0, float(entry.get("strength") or 0.0) - 0.15)
                entry["updated_at"] = now_iso
    else:
        new_affinities = _bump_entry(
            new_affinities,
            target=domain,
            kind="domain",
            now_iso=now_iso,
            delta_strength=0.35,
        )
        for entry in new_scars:
            if (
                str(entry.get("target") or "").lower() == domain
                and str(entry.get("kind") or "domain") == "domain"
            ):
                entry["strength"] = max(0.0, float(entry.get("strength") or 0.0) - 0.15)
                entry["updated_at"] = now_iso

    # Prune fully decayed mature rows; immature hits stay so the next tip works.
    matured_scars = _prune_inactive(
        new_scars, min_hits=MIN_HITS_FOR_SCAR, now=at, half_life_hours=half_life_hours
    )
    matured_affinities = _prune_inactive(
        new_affinities,
        min_hits=MIN_HITS_FOR_AFFINITY,
        now=at,
        half_life_hours=half_life_hours,
    )
    return matured_scars, matured_affinities


def active_for_influence(
    scars: list[dict[str, Any]] | None,
    affinities: list[dict[str, Any]] | None,
    *,
    now: datetime | None = None,
    half_life_hours: float = SCAR_HALF_LIFE_HOURS,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Mature + non-decayed entries only (hits threshold met)."""
    live_scars = [
        e
        for e, _s, _f in _active(
            list(scars or []),
            now=now,
            half_life_hours=half_life_hours,
            min_hits=MIN_HITS_FOR_SCAR,
        )
    ]
    live_aff = [
        e
        for e, _s, _f in _active(
            list(affinities or []),
            now=now,
            half_life_hours=half_life_hours,
            min_hits=MIN_HITS_FOR_AFFINITY,
        )
    ]
    return live_scars, live_aff
