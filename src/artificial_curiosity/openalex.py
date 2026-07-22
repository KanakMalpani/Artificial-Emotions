"""OpenAlex literature client for gap verification (no API key required)."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Any

from artificial_curiosity.models import LiteratureHit


class OpenAlexClient:
    BASE = "https://api.openalex.org"

    def __init__(self, timeout_s: float = 12.0, mailto: str | None = None):
        import os

        self.timeout_s = timeout_s
        self.mailto = mailto or os.environ.get("OPENALEX_MAILTO", "curiosity@localhost")

    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        params = {**params, "mailto": self.mailto}
        qs = urllib.parse.urlencode(params)
        url = f"{self.BASE}{path}?{qs}"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": f"ArtificialCuriosity/0.1 (mailto:{self.mailto})"},
        )
        with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
            return json.loads(resp.read().decode("utf-8"))

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
            hits.append(
                LiteratureHit(
                    title=w.get("title") or "Untitled",
                    year=(w.get("publication_year")),
                    doi=(w.get("doi")),
                    openalex_id=w.get("id"),
                    cited_by_count=w.get("cited_by_count"),
                    abstract_snippet=abstract,
                    url=w.get("id"),
                )
            )
        return hits
