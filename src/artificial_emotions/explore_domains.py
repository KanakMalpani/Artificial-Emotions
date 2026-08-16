"""Domain jump order and similarity clusters for the explore loop.

Callers import from ``artificial_emotions.explore`` (stable). This module
picks the next domain: ordered hops, optional similar-cluster forbid, and
scar/affinity bias. It does not invent domains. Cluster membership is
unchanged — energy sits in both physical and earth clusters.
"""

from __future__ import annotations

from typing import Any

from artificial_emotions.models import Domain

__all__ = ["domains"]

# Where boredom sends it next. Ordered so a jump lands somewhere genuinely
# different rather than an adjacent field.
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

# Jump-with-forbid skips the current domain's cluster. energy sits in both
# physical and earth, so it is similar to physics, materials, *and* climate.
_CLUSTERS: tuple[frozenset[str], ...] = (
    frozenset({"biology", "medicine"}),
    frozenset({"physics", "materials", "energy"}),
    frozenset({"climate", "energy"}),
    frozenset({"ai", "social"}),
    frozenset({"general"}),
)


def _domain_cluster(domain: str) -> frozenset[str]:
    """Domains similar to ``domain`` (including itself). Unknown → only itself."""
    key = str(domain).lower()
    similar: set[str] = {key}
    for cluster in _CLUSTERS:
        if key in cluster:
            similar.update(cluster)
    return frozenset(similar)


def _next_domain(
    current: str,
    visited: list[str],
    forbid_similar: bool = False,
) -> str:
    """Pick unvisited ground, following the jump order.

    When ``forbid_similar``, skip candidates in the current domain's cluster.
    If no dissimilar unvisited domain remains, stay (return current) — do not
    invent a domain.
    """
    current_key = str(current).lower()
    forbidden = _domain_cluster(current_key) if forbid_similar else frozenset()
    candidate = _JUMP_ORDER.get(current_key, "general")
    for _ in range(len(_JUMP_ORDER)):
        if candidate not in visited and candidate not in forbidden:
            return candidate
        candidate = _JUMP_ORDER.get(candidate, "general")
    if forbid_similar:
        return current_key
    return candidate


def _resolve_jump(
    current: str,
    visited: list[str],
    *,
    forbid_similar: bool,
    mem_scars: list[dict[str, Any]],
    mem_affinities: list[dict[str, Any]],
) -> tuple[str, Any | None, bool]:
    """Next domain, optional scar bias, and whether a similar hop was skipped."""
    similar_jump_skipped = False
    jump_bias: Any | None = None
    if mem_scars or mem_affinities:
        from artificial_emotions.scars import next_domain_biased

        nxt, jump_bias = next_domain_biased(
            current,
            visited,
            scars=mem_scars,
            affinities=mem_affinities,
        )
        if forbid_similar and nxt != current and nxt in _domain_cluster(current):
            similar_jump_skipped = True
            nxt = _next_domain(current, visited, forbid_similar=True)
            jump_bias = None
    else:
        nxt = _next_domain(current, visited, forbid_similar=forbid_similar)
        if forbid_similar:
            unconstrained = _next_domain(current, visited, forbid_similar=False)
            if unconstrained != nxt:
                similar_jump_skipped = True
    return nxt, jump_bias, similar_jump_skipped


def domains() -> list[str]:
    """Domains the loop can jump between."""
    return [d.value for d in Domain]
