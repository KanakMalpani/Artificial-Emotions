"""OpenAlex literature client for gap verification (no API key required)."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from artificial_emotions.models import LiteratureHit


class OpenAlexClient:
    BASE = "https://api.openalex.org"

    #: Off by default. The gap-verification path treats a rate limit as a soft
    #: failure and moves on, so retrying there only makes a slow run slower.
    #: Discovery opts in (``max_retries=3``) because it fans out into many small
    #: calls where one 429 would otherwise lose the whole fan-out.
    MAX_RETRIES = 0
    BACKOFF_S = 2.0

    def __init__(
        self,
        timeout_s: float = 12.0,
        mailto: str | None = None,
        *,
        max_retries: int | None = None,
    ):
        import os

        self.timeout_s = timeout_s
        self.mailto = mailto or os.environ.get("OPENALEX_MAILTO", "curiosity@localhost")
        self.max_retries = self.MAX_RETRIES if max_retries is None else int(max_retries)

    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        params = {**params, "mailto": self.mailto}
        qs = urllib.parse.urlencode(params)
        url = f"{self.BASE}{path}?{qs}"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": f"ArtificialEmotions/0.1 (mailto:{self.mailto})"},
        )
        attempt = 0
        while True:
            try:
                with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                if exc.code != 429 or attempt >= self.max_retries:
                    raise
                # Honour Retry-After when OpenAlex sends one; else exponential.
                retry_after = exc.headers.get("Retry-After") if exc.headers else None
                try:
                    delay = float(retry_after) if retry_after else self.BACKOFF_S * (2**attempt)
                except (TypeError, ValueError):
                    delay = self.BACKOFF_S * (2**attempt)
                time.sleep(min(delay, 30.0))
                attempt += 1

    def search_works(self, query: str, per_page: int = 8) -> list[LiteratureHit]:
        data = self._get(
            "/works",
            {
                "search": query,
                "per_page": per_page,
                "sort": "relevance_score:desc",
            },
        )
        hits: list[LiteratureHit] = []
        for w in data.get("results", []):
            abstract = None
            inv = w.get("abstract_inverted_index")
            if isinstance(inv, dict):
                # Reconstruct roughly for snippet
                pairs: list[tuple[int, str]] = []
                for word, positions in inv.items():
                    for p in positions:
                        pairs.append((p, word))
                pairs.sort()
                abstract = " ".join(word for _, word in pairs[:60])
            grants = w.get("grants") or []
            has_funder = bool(grants) if isinstance(grants, list) else None
            hits.append(
                LiteratureHit(
                    title=w.get("title") or "Untitled",
                    year=(w.get("publication_year")),
                    doi=(w.get("doi")),
                    openalex_id=w.get("id"),
                    cited_by_count=w.get("cited_by_count"),
                    abstract_snippet=abstract,
                    url=w.get("id"),
                    source="openalex",
                    has_funder=has_funder,
                )
            )
        return hits

    def concept_counts(
        self,
        query: str,
        *,
        per_page: int = 50,
        min_score: float = 0.3,
    ) -> dict[str, float]:
        """Concepts attached to the works matching ``query``, weighted by relevance.

        OpenAlex tags every work with scored concepts. Aggregating them across a
        result set is a far better description of "what this literature is about"
        than n-gramming titles, which is why ABC linking uses it.

        Returns ``{concept_name: summed_score}``.
        """
        data = self._get(
            "/works",
            {
                "search": query,
                "per_page": min(int(per_page), 200),
                "sort": "relevance_score:desc",
                "select": "id,concepts",
            },
        )
        counts: dict[str, float] = {}
        for work in data.get("results", []):
            for concept in work.get("concepts") or []:
                name = str(concept.get("display_name") or "").strip()
                score = float(concept.get("score") or 0.0)
                if not name or score < min_score:
                    continue
                counts[name] = counts.get(name, 0.0) + score
        return counts

    def cooccurrence_count(self, a: str, c: str) -> int:
        """How many works mention **both** terms in title or abstract.

        Zero (or near-zero) is the signal ABC linking is built on: two bodies of
        work that share a bridging concept but have never been connected
        directly.

        This must use ``filter=title_and_abstract.search:… AND …``. The plain
        ``search`` parameter scores by relevance rather than requiring both
        terms, which silently turns a co-occurrence count into "anything vaguely
        related" — ``gut microbiome Parkinson disease`` returns ~116k that way
        versus 179 here, and an absurd pairing returns 0 only under the filter.
        """
        return self._count(f"title_and_abstract.search:{a} AND {c}")

    def works_count(self, query: str) -> int:
        """Size of the literature mentioning ``query`` in title or abstract."""
        return self._count(f"title_and_abstract.search:{query}")

    def _count(self, filter_expr: str) -> int:
        data = self._get("/works", {"filter": filter_expr, "per_page": 1, "select": "id"})
        meta = data.get("meta") or {}
        return int(meta.get("count") or 0)
