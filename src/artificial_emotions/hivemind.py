"""Top-n similarity / hivemind detector (offline Jaccard default).

research/HIVEMIND.md — embedding cosine is optional; Jaccard is CI-safe.
"""

from __future__ import annotations

from typing import Any

from artificial_emotions.diversity import similarity


def top_n_pairwise_similarity(
    texts: list[str],
    *,
    backend: str = "jaccard",
) -> dict[str, Any]:
    """
    Mean / max pairwise similarity among top-n question texts.

    High mean ≈ hivemind / near-duplicate cluster risk. Not a novelty oracle.
    """
    clean = [str(t or "").strip() for t in texts if str(t or "").strip()]
    n = len(clean)
    if n < 2:
        return {
            "n": n,
            "backend": backend,
            "mean_pairwise": None,
            "max_pairwise": None,
            "n_pairs": 0,
            "honesty": "Need ≥2 texts for pairwise similarity.",
        }
    used = backend if backend in ("jaccard", "embedding") else "jaccard"
    sims = []
    for i in range(n):
        for j in range(i + 1, n):
            sims.append(float(similarity(clean[i], clean[j], backend=used)))  # type: ignore[arg-type]
    mean = round(sum(sims) / len(sims), 4) if sims else None
    mx = round(max(sims), 4) if sims else None
    return {
        "n": n,
        "backend": used,
        "mean_pairwise": mean,
        "max_pairwise": mx,
        "n_pairs": len(sims),
        "hivemind_warn": bool(mean is not None and mean >= 0.45),
        "honesty": (
            "Offline top-n similarity — high mean suggests near-duplicate / "
            "hivemind risk. Not embedding novelty science; not a claim the "
            "questions are bad."
        ),
    }
