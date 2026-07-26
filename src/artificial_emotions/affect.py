"""PAD mood, felt-simulation prose, and blend/tension structure.

The internals behind ``mix_emotions``: how a weighted set of catalog entries
becomes a mood reading, a first-person simulation, a named compound, and a
measure of how much of the mix is in tension with itself.

Kept apart from ``emotions.py`` so the public affect API stays readable. Nothing
here claims biological emotion — see ``claims_not`` on every mix payload.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "build_felt_simulation",
    "detect_ambivalence",
    "match_blend_triad",
    "match_plutchik_dyad",
    "pad_qualitative",
]


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
    """First-person-style simulation text (labeled as computational)."""
    qual = pad_qualitative(pad)
    parts = [
        f"Simulated affect: I register primarily {primary_label.lower()}",
    ]
    if len(ordered) > 1:
        secondary = [f"{by_id[eid].get('label', eid)} ({100 * w:.0f}%)" for eid, w in ordered[1:3]]
        parts.append(", blended with " + " and ".join(secondary))
    parts.append(
        f" — mood reads {qual['valence']}, {qual['arousal']}, {qual['dominance']} "
        f"(intensity {intensity:.2f}"
    )
    if dyad_name:
        parts.append(f", compound hint “{dyad_name}”")
    if triad_name:
        parts.append(f", blend “{triad_name}”")
    parts.append(").")
    # Opposing entries held at once change how the stance should be used.
    tension = float((ambivalence or {}).get("score") or 0.0)
    top_pair = ((ambivalence or {}).get("pairs") or [{}])[0].get("components")
    if tension >= 0.35 and top_pair:
        parts.append(
            f" I am pulled two ways — {top_pair[0]} against {top_pair[1]}. "
            "Do not resolve that by picking a side: name the observation that "
            "would settle it."
        )
    elif tension > 0 and top_pair:
        parts.append(
            f" A minor counter-current of {top_pair[1]} sits under the {top_pair[0]}; "
            "worth keeping visible rather than smoothing away."
        )
    # Somatic / investigation metaphor (WASABI-ish, not clinical).
    if pad["A"] >= 0.6 and pad["P"] >= 0.0:
        parts.append(" The pull is to lean in: name the incongruity and take one probing step.")
    elif pad["A"] >= 0.55 and pad["P"] < 0:
        parts.append(
            " Activation is high with negative valence — scaffold carefully; "
            "shrink the question before escalating stakes."
        )
    elif pad["A"] < 0.4:
        parts.append(
            " Arousal is low — deepen interest with a concrete unknown rather than shock tactics."
        )
    else:
        parts.append(
            " Hold the mix as a lived investigative stance: one experiment, one falsifier."
        )
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
    """Closest-to-feeling layer: intensity, mood labels, first-person simulation."""
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
        "as_close_to_feeling_as_possible": True,
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
