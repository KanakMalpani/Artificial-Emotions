"""PAD mood, felt-simulation prose, and blend/tension structure.

The internals behind ``mix_emotions``: how a weighted set of catalog entries
becomes a mood reading, a third-person computational inner_monologue, a named
compound, and a measure of how much of the mix is in tension with itself.

Also owns A2 mood carryover decay and appraisal-threshold bias: session mood
survives the process, decays exponentially toward neutral, and may shift how
easily *supported* appraisal signals clear the floor — never inventing evidence.

Kept apart from ``emotions.py`` so the public affect API stays readable. Nothing
here claims biological emotion — see ``claims_not`` on every mix payload.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

__all__ = [
    "DEFAULT_MIN_SIGNAL",
    "MAX_MIN_SIGNAL_DELTA",
    "MOOD_HALF_LIFE_HOURS",
    "MoodThresholdBias",
    "build_felt_simulation",
    "decay_factor",
    "decay_mood_pad",
    "detect_ambivalence",
    "match_blend_triad",
    "match_plutchik_dyad",
    "pad_from_felt_or_mix",
    "pad_qualitative",
    "threshold_bias_from_pad",
]

#: Half-life for mood carryover decay — a few hours (PLAN_ALIVE A2).
MOOD_HALF_LIFE_HOURS = 4.0

#: Appraisal noise floor (mirrors ``appraisal._MIN_SIGNAL``).
DEFAULT_MIN_SIGNAL = 0.04

#: Carryover may nudge the floor by at most this much.
MAX_MIN_SIGNAL_DELTA = 0.015


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    text = str(ts).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def decay_factor(
    updated_at: str | None,
    *,
    now: datetime | None = None,
    half_life_hours: float = MOOD_HALF_LIFE_HOURS,
) -> float:
    """Exponential decay factor in ``[0, 1]`` from wall-clock elapsed time.

    Missing / unparseable timestamps keep factor ``1.0`` (hand-edited mood
    without a clock is treated as fresh). Negative elapsed clamps to ``1.0``.
    """
    half = max(1e-6, float(half_life_hours))
    then = _parse_iso(updated_at)
    if then is None:
        return 1.0
    when = now if now is not None else datetime.now(UTC)
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    elapsed_h = (when.astimezone(UTC) - then).total_seconds() / 3600.0
    if elapsed_h <= 0:
        return 1.0
    return float(0.5 ** (elapsed_h / half))


def decay_mood_pad(
    pleasure: float,
    arousal: float,
    dominance: float,
    updated_at: str | None,
    *,
    now: datetime | None = None,
    half_life_hours: float = MOOD_HALF_LIFE_HOURS,
) -> tuple[float, float, float, float]:
    """Decay PAD toward neutral. Returns ``(P, A, D, factor)``."""
    factor = decay_factor(updated_at, now=now, half_life_hours=half_life_hours)
    return (
        float(pleasure) * factor,
        float(arousal) * factor,
        float(dominance) * factor,
        factor,
    )


def pad_from_felt_or_mix(payload: dict[str, Any] | None) -> dict[str, float] | None:
    """Pull ``P/A/D`` from a ``felt_simulation`` mood block or a mix ``pad`` dict."""
    if not payload:
        return None
    mood = payload.get("mood") if isinstance(payload.get("mood"), dict) else None
    pad = mood if mood else payload.get("pad")
    if not isinstance(pad, dict):
        # bare {P,A,D} or {pleasure,arousal,dominance}
        pad = payload
    p = pad.get("P", pad.get("pleasure"))
    a = pad.get("A", pad.get("arousal"))
    d = pad.get("D", pad.get("dominance"))
    if p is None and a is None and d is None:
        return None
    return {
        "P": float(p or 0.0),
        "A": float(a or 0.0),
        "D": float(d or 0.0),
    }


@dataclass(frozen=True)
class MoodThresholdBias:
    """How decayed carryover mood nudges appraisal signal floors.

    Rules that return ``None`` (no run support) stay ``None``. Bias only moves
    the weight floor for signals that already carry evidence.
    """

    pleasure: float
    arousal: float
    dominance: float
    decay_factor: float
    base_min_signal: float = DEFAULT_MIN_SIGNAL

    @property
    def is_active(self) -> bool:
        return abs(self.pleasure) > 1e-6 or abs(self.arousal) > 1e-6 or abs(self.dominance) > 1e-6

    def floor_for(self, emotion_pad_p: float | None = None) -> float:
        """Effective ``min_signal`` for one emotion given its catalog pleasure.

        Congruent valence (same sign as carryover pleasure) lowers the floor
        slightly; incongruent raises it. Magnitude scales with residual |P|
        and arousal. Caps keep behaviour close to today's default.
        """
        if not self.is_active:
            return self.base_min_signal
        magnitude = min(
            MAX_MIN_SIGNAL_DELTA,
            0.55 * abs(self.pleasure) + 0.35 * abs(self.arousal) * MAX_MIN_SIGNAL_DELTA / 0.5,
        )
        magnitude = min(MAX_MIN_SIGNAL_DELTA, max(0.0, magnitude))
        if emotion_pad_p is None or abs(self.pleasure) < 1e-6:
            # Global arousal residual: mild floor softening when activated.
            delta = -0.4 * magnitude * (1.0 if self.arousal > 0 else 0.0)
        else:
            congruent = (self.pleasure * float(emotion_pad_p)) > 0
            delta = -magnitude if congruent else magnitude
        floor = self.base_min_signal + delta
        return max(0.01, min(0.08, floor))

    def to_dict(self) -> dict[str, Any]:
        return {
            "pleasure": round(float(self.pleasure), 4),
            "arousal": round(float(self.arousal), 4),
            "dominance": round(float(self.dominance), 4),
            "decay_factor": round(float(self.decay_factor), 4),
            "base_min_signal": float(self.base_min_signal),
            "active": self.is_active,
            "honesty": (
                "biases appraisal thresholds only — does not invent evidence "
                "or claim the system feels"
            ),
        }


def threshold_bias_from_pad(
    pleasure: float,
    arousal: float,
    dominance: float,
    *,
    updated_at: str | None = None,
    now: datetime | None = None,
    half_life_hours: float = MOOD_HALF_LIFE_HOURS,
    base_min_signal: float = DEFAULT_MIN_SIGNAL,
) -> MoodThresholdBias:
    """Build a threshold bias from stored PAD, applying exponential decay."""
    p, a, d, factor = decay_mood_pad(
        pleasure,
        arousal,
        dominance,
        updated_at,
        now=now,
        half_life_hours=half_life_hours,
    )
    return MoodThresholdBias(
        pleasure=p,
        arousal=a,
        dominance=d,
        decay_factor=factor,
        base_min_signal=float(base_min_signal),
    )


def pad_qualitative(pad: dict[str, float]) -> dict[str, str]:
    p, a, d = pad["P"], pad["A"], pad["D"]
    valence = "pleasant" if p >= 0.25 else "unpleasant" if p <= -0.25 else "ambivalent"
    arousal = "activated" if a >= 0.55 else "calm" if a <= 0.35 else "mid-arousal"
    dominance = "empowered" if d >= 0.25 else "overwhelmed" if d <= -0.25 else "balanced-agency"
    return {"valence": valence, "arousal": arousal, "dominance": dominance}


def simulation_prose(
    *,
    primary: str,
    primary_label: str,
    ordered: list[tuple[str, float]],
    by_id: dict[str, Any],
    pad: dict[str, float],
    intensity: float,
    dyad_name: str | None,
    triad_name: str | None = None,
    ambivalence: dict[str, Any] | None = None,
) -> str:
    """Third-person computational affect text (not phenomenal first-person)."""
    shown_primary = str((by_id.get(primary) or {}).get("id") or primary_label or primary).lower()
    qual = pad_qualitative(pad)
    parts = [
        f"Computational affect: primary={shown_primary}",
    ]
    if len(ordered) > 1:
        secondary = [f"{eid}={100 * w:.0f}%" for eid, w in ordered[1:3]]
        parts.append("; blend=" + " and ".join(secondary))
    parts.append(
        f"; mood={qual['valence']}, {qual['arousal']}, {qual['dominance']} "
        f"(intensity={intensity:.2f}"
    )
    if dyad_name:
        parts.append(f", compound={dyad_name}")
    if triad_name:
        parts.append(f", triad={triad_name}")
    parts.append(")")
    # Opposing entries held at once change how the stance should be used.
    tension = float((ambivalence or {}).get("score") or 0.0)
    top_pair = ((ambivalence or {}).get("pairs") or [{}])[0].get("components")
    if tension >= 0.35 and top_pair:
        parts.append(
            f"; ambivalence({top_pair[0]}, {top_pair[1]})={tension:.2f} "
            "— do not collapse the mix. Name the observation that would settle it."
        )
    elif tension > 0 and top_pair:
        parts.append(
            f"; ambivalence({top_pair[0]}, {top_pair[1]})={tension:.2f} "
            "— keep both weights visible rather than smoothing away."
        )
    # Investigation next-step hint from PAD (computational, not a felt urge).
    if pad["A"] >= 0.6 and pad["P"] >= 0.0:
        parts.append(" Next: name the incongruity and take one probing step.")
    elif pad["A"] >= 0.55 and pad["P"] < 0:
        parts.append(
            " High activation with negative valence — scaffold carefully; "
            "shrink the question before escalating stakes."
        )
    elif pad["A"] < 0.4:
        parts.append(
            " Low arousal — deepen the unknown with a concrete question rather than shock tactics."
        )
    else:
        parts.append(" Investigative stance: one experiment, one falsifier.")
    parts.append(" Honesty: computational_affect; does not feel.")
    return "".join(parts)


def build_felt_simulation(
    *,
    ordered: list[tuple[str, float]],
    by_id: dict[str, Any],
    pad: dict[str, float],
    dyad: dict[str, Any] | None,
    triad: dict[str, Any] | None = None,
    ambivalence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Computational affect layer: intensity, mood labels, third-person inner_monologue."""
    # Intensity: arousal + how peaked the mix is (low entropy → sharper “feeling”).
    masses = [w for _, w in ordered]
    peak = masses[0] if masses else 0.0
    concentration = peak  # 1/n would be flat; peak high = focused affect
    intensity = max(0.0, min(1.0, 0.55 * float(pad["A"]) + 0.45 * concentration))
    primary_id = ordered[0][0]
    primary_label = str(by_id[primary_id].get("label") or primary_id)
    qual = pad_qualitative(pad)
    dyad_name = str(dyad["name"]) if dyad and dyad.get("name") else None
    layers = [
        {
            "id": eid,
            "label": by_id[eid].get("label") or eid,
            "felt_weight": round(w, 4),
            "felt_percent": round(100.0 * w, 2),
            "family": by_id[eid].get("family"),
        }
        for eid, w in ordered
    ]
    prose = simulation_prose(
        primary=primary_id,
        primary_label=primary_label,
        ordered=ordered,
        by_id=by_id,
        pad=pad,
        intensity=intensity,
        dyad_name=dyad_name,
        triad_name=str(triad["name"]) if triad and triad.get("name") else None,
        ambivalence=ambivalence,
    )
    return {
        "mode": "computational_affect",
        "computational_only": True,
        "primary_feeling": primary_id,
        "primary_label": primary_label,
        "intensity": round(intensity, 4),
        "mood": {**{k: round(v, 4) for k, v in pad.items()}, "qualitative": qual},
        "layers": layers,
        "compound": dyad_name,
        "inner_monologue": prose,
        "embodiment_hint": {
            "valence": qual["valence"],
            "activation": qual["arousal"],
            "agency": qual["dominance"],
        },
        "not_claimed": [
            "biological emotion",
            "phenomenal consciousness",
            "user affect measurement",
        ],
    }


def match_blend_triad(
    ordered: list[tuple[str, float]],
    triads: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Named 3-component blend — the step past Plutchik's 2-component dyads.

    Matches exactly when the mix has three components, and otherwise on the
    three heaviest (reported as ``matched_on`` so the caller can tell).
    """
    if len(ordered) < 3 or not triads:
        return None
    exact = len(ordered) == 3
    top3 = sorted(eid for eid, _w in ordered[:3])
    for t in triads:
        comps = sorted(str(x).lower() for x in (t.get("components") or []))
        if comps == top3:
            return {
                "name": t.get("name"),
                "components": list(t.get("components") or []),
                "matched_on": "exact" if exact else "top_3_by_weight",
                "note": (
                    f"{t.get('note')} Named blend from the catalog's investigative "
                    "vocabulary — a taxonomic label, not a measured compound state."
                ),
            }
    return None


def detect_ambivalence(
    ordered: list[tuple[str, float]],
    opposite_pairs: list[dict[str, Any]],
) -> dict[str, Any]:
    """Find opposing emotions held simultaneously.

    A mix carrying both sides of an opposition is the interesting case — e.g.
    conviction with live doubt, or curiosity with boredom. Tension is the mass
    sitting in conflict scaled by how evenly it is split, so a 50/50 clash reads
    higher than a 90/10 one at equal mass.
    """
    weights = dict(ordered)
    tensions: list[dict[str, Any]] = []
    for pair in opposite_pairs or []:
        comps = [str(x).lower() for x in (pair.get("components") or [])]
        if len(comps) != 2:
            continue
        a, b = comps
        wa, wb = weights.get(a, 0.0), weights.get(b, 0.0)
        if wa <= 0.0 or wb <= 0.0:
            continue
        mass = wa + wb
        balance = min(wa, wb) / max(wa, wb)
        tensions.append(
            {
                "components": [a, b],
                "axis": pair.get("axis"),
                "mass": round(mass, 4),
                "balance": round(balance, 4),
                "tension": round(mass * balance, 4),
            }
        )
    tensions.sort(key=lambda t: (-t["tension"], t["components"]))
    score = tensions[0]["tension"] if tensions else 0.0
    return {
        "score": round(float(score), 4),
        "pairs": tensions,
        "note": (
            "Opposing catalog entries held at once. High tension is not an error — "
            "sustained ambivalence is often the honest state of an open question."
            if tensions
            else "No opposing pairs in this mix."
        ),
    }


def match_plutchik_dyad(
    ids: list[str],
    dyads: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if len(ids) != 2:
        return None
    a, b = sorted(ids)
    for d in dyads:
        comps = sorted(str(x).lower() for x in (d.get("components") or []))
        if comps == [a, b]:
            return {
                "name": d.get("name"),
                "components": list(d.get("components") or []),
                "note": (
                    "Optional Plutchik primary-dyad hint from wheel adjacency — "
                    "taxonomic metaphor, not a measured compound emotion."
                ),
            }
    return None
