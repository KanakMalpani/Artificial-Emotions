"""Compare the same candidate pool under two ValueProfiles (F11 honesty).

Near-term constitutional curiosity (research/CONSTITUTIONAL_CURIOSITY.md):
show side-by-side ranks — never silent “consensus” merge.
"""

from __future__ import annotations

from typing import Any

from artificial_curiosity.generate import generate_candidates
from artificial_curiosity.models import (
    CuriosityConfig,
    GapEvidence,
    GapStatus,
    ValueProfile,
    resolve_value_profile,
)
from artificial_curiosity.scoring import aggregate_curiosity, heuristic_score


def _kendall_tau(rank_a: dict[str, int], rank_b: dict[str, int]) -> float | None:
    """Kendall τ on shared ids (None if fewer than 5 shared)."""
    ids = sorted(set(rank_a) & set(rank_b))
    n = len(ids)
    if n < 5:
        return None
    concordant = 0
    discordant = 0
    for i in range(n):
        for j in range(i + 1, n):
            da = rank_a[ids[i]] - rank_a[ids[j]]
            db = rank_b[ids[i]] - rank_b[ids[j]]
            if da == 0 or db == 0:
                continue
            if da * db > 0:
                concordant += 1
            else:
                discordant += 1
    denom = concordant + discordant
    if denom == 0:
        return 0.0
    return round((concordant - discordant) / denom, 4)


def _top_k_jaccard(ids_a: list[str], ids_b: list[str]) -> float:
    sa, sb = set(ids_a), set(ids_b)
    if not sa and not sb:
        return 1.0
    return round(len(sa & sb) / len(sa | sb), 4)


def compare_profiles(
    *,
    domain: str = "ai",
    topic: str = "",
    profile_a: str | ValueProfile = "humanity_default",
    profile_b: str | ValueProfile = "alignment_lab",
    n: int = 8,
    n_candidates: int = 16,
    seed: int = 42,
) -> dict[str, Any]:
    """
    Offline heuristic re-rank of one candidate pool under two profiles.

    Literature/LLM off — decision-aid comparison only. Safety veto tip:
    compose max_risk = min(profile_a.max_risk, profile_b.max_risk) when
    treating one profile as a hard ceiling.
    """
    pa = (
        profile_a
        if isinstance(profile_a, ValueProfile)
        else resolve_value_profile(profile_name=str(profile_a))
    )
    pb = (
        profile_b
        if isinstance(profile_b, ValueProfile)
        else resolve_value_profile(profile_name=str(profile_b))
    )
    cfg = CuriosityConfig(
        domain=domain,
        topic=topic,
        n_candidates=n_candidates,
        n_return=n,
        use_llm=False,
        use_literature=False,
        value_profile=pa,
        seed=seed,
    )
    candidates = generate_candidates(cfg)
    gap = GapEvidence(
        status=GapStatus.UNKNOWN_WITH_CAVEAT,
        confidence=0.25,
        notes="compare_profiles offline — no literature; gap provisional.",
        literature_backend="none",
    )

    def _rank(profile: ValueProfile) -> list[dict[str, Any]]:
        scored: list[tuple[float, dict[str, Any]]] = []
        for q in candidates:
            axes = heuristic_score(q, gap.status, 0, 0.0, profile, strong_match_count=0)
            score = aggregate_curiosity(axes, profile)
            scored.append(
                (
                    score,
                    {
                        "question_id": q.id,
                        "question": q.question,
                        "curiosity_score": round(float(score), 4),
                        "axes": {
                            "impact": axes.impact,
                            "neglectedness": axes.neglectedness,
                            "tractability": axes.tractability,
                            "surprise": axes.surprise,
                            "answerability": axes.answerability,
                            "risk": axes.risk,
                        },
                        "tags": list(q.tags or []),
                    },
                )
            )
        scored.sort(key=lambda t: t[0], reverse=True)
        out = []
        for i, (_s, row) in enumerate(scored[:n], start=1):
            row = dict(row)
            row["rank"] = i
            out.append(row)
        return out

    ranks_a = _rank(pa)
    ranks_b = _rank(pb)
    pos_a = {r["question_id"]: r["rank"] for r in ranks_a}
    pos_b = {r["question_id"]: r["rank"] for r in ranks_b}
    all_ids = sorted(set(pos_a) | set(pos_b))
    deltas = []
    for qid in all_ids:
        ra = pos_a.get(qid)
        rb = pos_b.get(qid)
        if ra is None or rb is None:
            continue
        deltas.append(
            {
                "question_id": qid,
                "rank_a": ra,
                "rank_b": rb,
                "delta_a_minus_b": ra - rb,
            }
        )
    deltas.sort(key=lambda d: (abs(d["delta_a_minus_b"]), d["question_id"]), reverse=True)

    tau = _kendall_tau(pos_a, pos_b)
    jaccard = _top_k_jaccard(
        [r["question_id"] for r in ranks_a],
        [r["question_id"] for r in ranks_b],
    )

    return {
        "domain": domain,
        "topic": topic,
        "n": n,
        "profile_a": pa.model_dump(mode="json"),
        "profile_b": pb.model_dump(mode="json"),
        "ranks_a": ranks_a,
        "ranks_b": ranks_b,
        "rank_deltas": deltas,
        "agreement": {
            "kendall_tau": tau,
            "top_k_jaccard": jaccard,
            "note": (
                "Kendall τ requires ≥5 shared ids; None means too few for a "
                "stable ordinal association. Not a claim either profile is correct."
            ),
        },
        "veto_tip": {
            "strictest_max_risk": min(pa.max_risk, pb.max_risk),
            "note": (
                "Hard-veto pattern: rank under primary profile, then drop/flag "
                "items exceeding the stricter max_risk. Do not silently merge "
                "weights into a fake consensus score."
            ),
        },
        "honesty": (
            "Side-by-side ValueProfile comparison — decision aids, not a "
            "value-free or constitutional optimum. Offline heuristic only."
        ),
        "flags": ["no_literature", "heuristic_scoring", "compare_profiles"],
    }
