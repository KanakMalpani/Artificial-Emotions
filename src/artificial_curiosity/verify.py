"""Gap verification against literature.

Important: related papers ≠ answered question.
Literature search (OpenAlex and/or Semantic Scholar) returns a neighborhood;
we only claim partial/full answers when title(+abstract) overlap is high enough,
tempered by lightweight abstract "reading" for claim vs open-gap language.
"""

from __future__ import annotations

import re

from artificial_curiosity.literature import LiteratureClient
from artificial_curiosity.models import GapEvidence, GapStatus, LiteratureHit, UnansweredQuestion

# Lightweight abstract reading (F7): not full NLP, but better than bag-of-tokens alone.
_ANSWER_CLAIM = (
    "we show", "we demonstrate", "we find that", "we prove", "results show",
    "our results", "we establish", "empirically show", "we solve",
    "definitively", "conclusively",
)
_OPEN_GAP = (
    "remains unknown", "open question", "poorly understood", "not well understood",
    "unresolved", "further research", "future work", "gap in", "little is known",
    "unclear whether", "still unknown", "to be determined",
)


def _query_from_question(q: UnansweredQuestion) -> str:
    stop = {
        "what", "which", "when", "where", "why", "how", "does", "do", "is",
        "are", "the", "a", "an", "of", "in", "to", "for", "and", "or", "with",
        "most", "best", "can", "we", "our", "that", "this", "under", "when",
        "appear", "increase", "reduce", "cause", "before",
    }
    words = re.findall(r"[A-Za-z0-9\-]+", q.question.lower())
    keep = [w for w in words if w not in stop and len(w) > 2]
    compounds = [w for w in keep if "-" in w]
    plain = [w for w in keep if "-" not in w]
    ordered = compounds + plain
    tags = [t.lower().replace("_", " ") for t in (q.tags or [])[:3]]
    core = " ".join(ordered[:10])
    if tags:
        core = f"{core} {' '.join(tags)}".strip()
    return core or q.question[:120]


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _token_overlap(a: str, b: str) -> float:
    ta = _tokens(a)
    tb = _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _bigrams(text: str) -> set[str]:
    toks = re.findall(r"[a-z0-9]+", text.lower())
    return {f"{toks[i]} {toks[i+1]}" for i in range(len(toks) - 1)}


def _bigram_overlap(a: str, b: str) -> float:
    ba = _bigrams(a)
    bb = _bigrams(b)
    if not ba or not bb:
        return 0.0
    return len(ba & bb) / len(ba | bb)


def _hit_blob(hit: LiteratureHit) -> str:
    blob = hit.title
    if hit.abstract_snippet:
        blob = f"{blob} {hit.abstract_snippet}"
    return blob


def _content_overlap(probe: str, hit: LiteratureHit, *, ops: str = "") -> float:
    """
    Title-weighted overlap of question (+ ops) against title/abstract.

    Operationalization tokens are weighted extra so phrase-gaming abstracts
    that share topic words but miss the measurement bar score lower (F7).
    """
    title_o = _token_overlap(probe, hit.title)
    blob_o = _token_overlap(probe, _hit_blob(hit))
    bi_o = _bigram_overlap(probe, _hit_blob(hit))
    base = 0.5 * title_o + 0.3 * blob_o + 0.2 * bi_o
    if ops.strip():
        ops_o = _token_overlap(ops, _hit_blob(hit))
        # Require some ops grounding for high overlaps — related ≠ answered.
        base = 0.7 * base + 0.3 * ops_o
    return float(max(0.0, min(1.0, base)))


def _abstract_claim_signal(hit: LiteratureHit) -> float:
    """
    Crude abstract reading: positive = paper claims an answer;
    negative = paper itself frames an open gap.
    Range roughly [-0.25, +0.35].
    """
    text = (_hit_blob(hit)).lower()
    claims = sum(1 for p in _ANSWER_CLAIM if p in text)
    gaps = sum(1 for p in _OPEN_GAP if p in text)
    # Extra claim phrases that often accompany concrete results.
    if "statistically significant" in text or "p <" in text or "p<" in text:
        claims += 1
    if "we conclude" in text or "this study shows" in text:
        claims += 1
    return min(0.35, 0.12 * claims) - min(0.25, 0.1 * gaps)


def _effective_overlap(base: float, claim_signal: float) -> float:
    """Boost overlap when abstract claims answers; dampen when it admits gaps."""
    return max(0.0, min(1.0, base + 0.5 * claim_signal))


def _recency_weight(year: int | None, *, current_year: int = 2026) -> float:
    """F12: recent answering literature weighs more than stale neighbors."""
    if year is None:
        return 0.7
    age = max(0, current_year - int(year))
    if age <= 3:
        return 1.0
    if age <= 10:
        return 0.85
    if age <= 20:
        return 0.7
    return 0.55


def classify_gap(
    hits_count: int,
    avg_citations: float,
    top_overlap: float,
    strong_match_count: int,
    *,
    recent_strong_count: int = 0,
) -> GapStatus:
    """
    Classify using overlap strength, not mere hit count (F1/F7).

    - No hits → unknown
    - Many strong overlaps + citations (+ recent signal) → likely answered
    - Some strong overlaps → partially answered
    - Hits but weak overlap → unanswered (adjacent literature only)
    """
    if hits_count == 0:
        return GapStatus.UNKNOWN_WITH_CAVEAT

    if (
        strong_match_count >= 3
        and top_overlap >= 0.45
        and avg_citations >= 30
        and recent_strong_count >= 1
    ):
        return GapStatus.LIKELY_ANSWERED
    if strong_match_count >= 2 and top_overlap >= 0.38:
        return GapStatus.PARTIALLY_ANSWERED
    if strong_match_count >= 1 and top_overlap >= 0.32:
        return GapStatus.PARTIALLY_ANSWERED
    return GapStatus.UNANSWERED


def verify_gap(
    question: UnansweredQuestion,
    client: LiteratureClient | None = None,
    use_literature: bool = True,
    *,
    literature_backend: str | None = None,
) -> GapEvidence:
    query = _query_from_question(question)
    if not use_literature or client is None:
        return GapEvidence(
            status=GapStatus.UNKNOWN_WITH_CAVEAT,
            confidence=0.25,
            related_works=[],
            notes="Literature verification disabled; treat gap status as provisional.",
            query_used=query,
            literature_backend=literature_backend or "none",
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
            literature_backend=literature_backend,
        )

    probe = f"{question.question} {question.operationalization}"
    ops = question.operationalization or ""
    base_overlaps = [_content_overlap(probe, h, ops=ops) for h in hits]
    claim_signals = [_abstract_claim_signal(h) for h in hits]
    overlaps = [
        _effective_overlap(b, c) for b, c in zip(base_overlaps, claim_signals)
    ]
    weighted = [
        o * _recency_weight(h.year) for o, h in zip(overlaps, hits)
    ]
    top_overlap = max(weighted) if weighted else 0.0
    strong_idxs = [i for i, o in enumerate(overlaps) if o >= 0.28]
    strong_match_count = len(strong_idxs)
    recent_strong_count = sum(
        1
        for i in strong_idxs
        if _recency_weight(hits[i].year) >= 0.85
    )
    open_gap_hits = sum(1 for c in claim_signals if c < -0.05)
    claim_hits = sum(1 for c in claim_signals if c > 0.1)
    cites = [h.cited_by_count or 0 for h in hits]
    avg_cites = sum(cites) / len(cites) if cites else 0.0
    status = classify_gap(
        len(hits),
        avg_cites,
        top_overlap,
        strong_match_count,
        recent_strong_count=recent_strong_count,
    )

    conf = 0.35 + 0.08 * min(strong_match_count, 5) + 0.1 * top_overlap
    if status == GapStatus.UNKNOWN_WITH_CAVEAT:
        conf = 0.25
    elif status == GapStatus.UNANSWERED and hits:
        conf = 0.45 + 0.05 * min(len(hits), 4)
        conf += 0.03 * min(open_gap_hits, 3)
    if claim_hits and status in (GapStatus.PARTIALLY_ANSWERED, GapStatus.LIKELY_ANSWERED):
        conf = min(0.9, conf + 0.04 * min(claim_hits, 3))
    if recent_strong_count == 0 and strong_match_count >= 2:
        conf = max(0.2, conf - 0.05)

    backend_note = literature_backend or "literature"
    notes = (
        f"Found {len(hits)} neighborhood works via {backend_note}; "
        f"strong_matches={strong_match_count}; "
        f"recent_strong={recent_strong_count}; "
        f"top recency-weighted overlap={top_overlap:.2f}; avg citations={avg_cites:.1f}; "
        f"abstract claim_hits={claim_hits}, open_gap_hits={open_gap_hits}. "
        f"Related ≠ answered: weak-overlap neighborhoods stay unanswered. "
        f"Abstract reading is phrase-level, not full-text comprehension."
    )
    return GapEvidence(
        status=status,
        confidence=min(0.9, conf),
        related_works=hits[:8],
        notes=notes,
        query_used=query,
        strong_match_count=strong_match_count,
        top_overlap=top_overlap,
        literature_backend=literature_backend,
    )
