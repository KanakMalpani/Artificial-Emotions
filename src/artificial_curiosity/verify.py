"""Gap verification against literature.

Important: related papers ≠ answered question.
OpenAlex relevance search returns a neighborhood; we only claim
partial/full answers when title(+abstract) overlap is high enough.
"""

from __future__ import annotations

import re

from artificial_curiosity.models import GapEvidence, GapStatus, LiteratureHit, UnansweredQuestion
from artificial_curiosity.openalex import OpenAlexClient


def _query_from_question(q: UnansweredQuestion) -> str:
    stop = {
        "what", "which", "when", "where", "why", "how", "does", "do", "is",
        "are", "the", "a", "an", "of", "in", "to", "for", "and", "or", "with",
        "most", "best", "can", "we", "our", "that", "this",
    }
    words = re.findall(r"[A-Za-z0-9\-]+", q.question.lower())
    keep = [w for w in words if w not in stop and len(w) > 2][:12]
    return " ".join(keep) or q.question[:120]


def _token_overlap(a: str, b: str) -> float:
    ta = set(re.findall(r"[a-z0-9]+", a.lower()))
    tb = set(re.findall(r"[a-z0-9]+", b.lower()))
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _content_overlap(question: str, hit: LiteratureHit) -> float:
    blob = hit.title
    if hit.abstract_snippet:
        blob = f"{blob} {hit.abstract_snippet}"
    return _token_overlap(question, blob)


def classify_gap(
    hits_count: int,
    avg_citations: float,
    top_overlap: float,
    strong_match_count: int,
) -> GapStatus:
    """
    Classify using overlap strength, not mere hit count.

    - No hits → unknown
    - Many strong overlaps + citations → likely answered
    - Some strong overlaps → partially answered
    - Hits but weak overlap → unanswered (adjacent literature only)
    """
    if hits_count == 0:
        return GapStatus.UNKNOWN_WITH_CAVEAT

    if strong_match_count >= 3 and top_overlap >= 0.45 and avg_citations >= 30:
        return GapStatus.LIKELY_ANSWERED
    if strong_match_count >= 2 and top_overlap >= 0.38:
        return GapStatus.PARTIALLY_ANSWERED
    if strong_match_count >= 1 and top_overlap >= 0.32:
        return GapStatus.PARTIALLY_ANSWERED
    # Neighborhood exists but does not tightly match the question.
    return GapStatus.UNANSWERED


def verify_gap(
    question: UnansweredQuestion,
    client: OpenAlexClient | None = None,
    use_literature: bool = True,
) -> GapEvidence:
    query = _query_from_question(question)
    if not use_literature or client is None:
        return GapEvidence(
            status=GapStatus.UNKNOWN_WITH_CAVEAT,
            confidence=0.25,
            related_works=[],
            notes="Literature verification disabled; treat gap status as provisional.",
            query_used=query,
        )

    try:
        hits = client.search_works(query, per_page=10)
    except Exception as exc:  # noqa: BLE001 — network/API soft-fail
        return GapEvidence(
            status=GapStatus.UNKNOWN_WITH_CAVEAT,
            confidence=0.2,
            related_works=[],
            notes=f"Literature fetch failed: {exc}",
            query_used=query,
        )

    overlaps = [_content_overlap(question.question, h) for h in hits]
    top_overlap = max(overlaps) if overlaps else 0.0
    strong_match_count = sum(1 for o in overlaps if o >= 0.28)
    cites = [h.cited_by_count or 0 for h in hits]
    avg_cites = sum(cites) / len(cites) if cites else 0.0
    status = classify_gap(len(hits), avg_cites, top_overlap, strong_match_count)

    # Confidence rises with strong matches, not raw hit volume.
    conf = 0.35 + 0.08 * min(strong_match_count, 5) + 0.1 * top_overlap
    if status == GapStatus.UNKNOWN_WITH_CAVEAT:
        conf = 0.25
    elif status == GapStatus.UNANSWERED and hits:
        conf = 0.45 + 0.05 * min(len(hits), 4)

    notes = (
        f"Found {len(hits)} neighborhood works; strong_matches={strong_match_count}; "
        f"top content overlap={top_overlap:.2f}; avg citations={avg_cites:.1f}. "
        f"Related ≠ answered: weak-overlap neighborhoods stay unanswered."
    )
    return GapEvidence(
        status=status,
        confidence=min(0.9, conf),
        related_works=hits[:8],
        notes=notes,
        query_used=query,
        strong_match_count=strong_match_count,
        top_overlap=top_overlap,
    )
