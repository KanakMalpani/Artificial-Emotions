"""Literature backends for gap verification (OpenAlex + Semantic Scholar).

Default remains OpenAlex (no API key). Semantic Scholar is optional behind
`literature_backend` config. Offline (`use_literature=False`) never calls either.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from artificial_curiosity.logutil import get_logger
from artificial_curiosity.models import LiteratureHit
from artificial_curiosity.openalex import OpenAlexClient

logger = get_logger("literature")


@runtime_checkable
class LiteratureClient(Protocol):
    """Minimal search interface shared by all literature adapters."""

    def search_works(self, query: str, per_page: int = 8) -> list[LiteratureHit]: ...


def _cache_key(backend: str, query: str, per_page: int) -> str:
    raw = f"{backend}|{query}|{per_page}".encode()
    return hashlib.sha256(raw).hexdigest()[:32]


class CachedLiteratureClient:
    """Disk cache wrapper (opt-in) to soften rate limits / repeat queries."""

    def __init__(
        self,
        inner: LiteratureClient,
        *,
        backend_name: str,
        cache_dir: str | Path | None = None,
        ttl_s: float = 86_400.0,
    ):
        self.inner = inner
        self.backend_name = backend_name
        self.ttl_s = ttl_s
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self._lock = threading.Lock()
        if self.cache_dir is not None:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def search_works(self, query: str, per_page: int = 8) -> list[LiteratureHit]:
        if self.cache_dir is None:
            return self.inner.search_works(query, per_page=per_page)
        path = self.cache_dir / f"{_cache_key(self.backend_name, query, per_page)}.json"
        now = time.time()
        with self._lock:
            if path.exists():
                try:
                    payload = json.loads(path.read_text(encoding="utf-8"))
                    if now - float(payload.get("ts", 0)) <= self.ttl_s:
                        return [
                            LiteratureHit.model_validate(h) for h in payload.get("hits", [])
                        ]
                except Exception as exc:  # noqa: BLE001 — corrupt cache → refetch
                    logger.warning("Literature cache read failed; refetching: %s", exc)
        hits = self.inner.search_works(query, per_page=per_page)
        try:
            tmp = path.with_suffix(".json.tmp")
            payload = json.dumps(
                {
                    "ts": now,
                    "backend": self.backend_name,
                    "query": query,
                    "hits": [h.model_dump(mode="json") for h in hits],
                },
                indent=0,
            )
            with self._lock:
                tmp.write_text(payload, encoding="utf-8")
                tmp.replace(path)
        except Exception as exc:  # noqa: BLE001 — cache write is best-effort
            logger.warning("Literature cache write failed: %s", exc)
        return hits


class SemanticScholarClient:
    """Semantic Scholar Graph API (optional second backend; no key required for low volume)."""

    BASE = "https://api.semanticscholar.org/graph/v1"

    def __init__(self, timeout_s: float = 12.0, api_key: str | None = None):
        import os

        self.timeout_s = timeout_s
        self.api_key = (
            api_key or os.environ.get("S2_API_KEY") or os.environ.get("SEMANTIC_SCHOLAR_API_KEY")
        )

    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        qs = urllib.parse.urlencode(params)
        url = f"{self.BASE}{path}?{qs}"
        headers = {
            "User-Agent": "ArtificialCuriosity/0.3 (research; mailto:curiosity@localhost)",
        }
        if self.api_key:
            headers["x-api-key"] = self.api_key
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def search_works(self, query: str, per_page: int = 8) -> list[LiteratureHit]:
        try:
            data = self._get(
                "/paper/search",
                {
                    "query": query,
                    "limit": min(per_page, 20),
                    "fields": "title,year,externalIds,citationCount,abstract,url",
                },
            )
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"Semantic Scholar HTTP {exc.code}") from exc
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"Semantic Scholar fetch failed: {exc}") from exc

        hits: list[LiteratureHit] = []
        for w in data.get("data") or []:
            ext = w.get("externalIds") or {}
            doi = ext.get("DOI")
            abstract = w.get("abstract")
            snippet = None
            if isinstance(abstract, str) and abstract.strip():
                snippet = " ".join(abstract.split()[:60])
            paper_id = w.get("paperId")
            url = w.get("url") or (
                f"https://www.semanticscholar.org/paper/{paper_id}" if paper_id else None
            )
            hits.append(
                LiteratureHit(
                    title=w.get("title") or "Untitled",
                    year=w.get("year"),
                    doi=f"https://doi.org/{doi}"
                    if doi and not str(doi).startswith("http")
                    else doi,
                    openalex_id=None,
                    cited_by_count=w.get("citationCount"),
                    abstract_snippet=snippet,
                    url=url,
                    source="semantic_scholar",
                    source_id=paper_id,
                )
            )
        return hits


class MergedLiteratureClient:
    """Query primary then optional secondary; merge by normalized title, prefer richer abstracts."""

    def __init__(
        self,
        primary: LiteratureClient,
        secondary: LiteratureClient | None = None,
        *,
        primary_name: str = "openalex",
        secondary_name: str = "semantic_scholar",
    ):
        self.primary = primary
        self.secondary = secondary
        self.primary_name = primary_name
        self.secondary_name = secondary_name

    @staticmethod
    def _norm_title(t: str) -> str:
        return " ".join(
            "".join(c.lower() if c.isalnum() or c.isspace() else " " for c in t).split()
        )

    def search_works(self, query: str, per_page: int = 8) -> list[LiteratureHit]:
        primary_hits = self.primary.search_works(query, per_page=per_page)
        for h in primary_hits:
            if not h.source:
                h.source = self.primary_name
        if self.secondary is None:
            return primary_hits

        try:
            secondary_hits = self.secondary.search_works(query, per_page=per_page)
        except Exception as exc:  # noqa: BLE001 — soft-fail secondary
            logger.warning(
                "Secondary literature backend %s soft-fail; using %s only: %s",
                self.secondary_name,
                self.primary_name,
                exc,
            )
            return primary_hits

        for h in secondary_hits:
            if not h.source:
                h.source = self.secondary_name

        by_title: dict[str, LiteratureHit] = {}
        order: list[str] = []
        for h in primary_hits + secondary_hits:
            key = self._norm_title(h.title)
            if not key:
                continue
            if key not in by_title:
                by_title[key] = h
                order.append(key)
            else:
                existing = by_title[key]
                # Prefer hit with abstract / higher cites.
                if (not existing.abstract_snippet) and h.abstract_snippet:
                    by_title[key] = h
                elif (h.cited_by_count or 0) > (existing.cited_by_count or 0) + 5:
                    if h.abstract_snippet or not existing.abstract_snippet:
                        by_title[key] = h
        return [by_title[k] for k in order][: max(per_page, 8)]


def build_literature_client(
    backend: str = "openalex",
    *,
    timeout_s: float = 12.0,
    cache_dir: str | Path | None = None,
    cache_ttl_s: float = 86_400.0,
) -> LiteratureClient | None:
    """
    Factory for literature adapters.

    backend:
      - openalex (default)
      - semantic_scholar | s2
      - both | merge (OpenAlex primary + S2 secondary)
    """
    key = (backend or "openalex").strip().lower()
    oa = OpenAlexClient(timeout_s=timeout_s)

    # Tag OpenAlex hits with source for multi-backend transparency.
    class _TaggedOpenAlex:
        def search_works(self, query: str, per_page: int = 8) -> list[LiteratureHit]:
            hits = oa.search_works(query, per_page=per_page)
            for h in hits:
                if not h.source:
                    h.source = "openalex"
                if not h.source_id and h.openalex_id:
                    h.source_id = h.openalex_id
            return hits

    if key in ("none", "off", "disabled"):
        return None

    if key in ("semantic_scholar", "s2", "semanticscholar"):
        inner: LiteratureClient = SemanticScholarClient(timeout_s=timeout_s)
        name = "semantic_scholar"
    elif key in ("both", "merge", "multi"):
        inner = MergedLiteratureClient(
            _TaggedOpenAlex(),
            SemanticScholarClient(timeout_s=timeout_s),
        )
        name = "both"
    else:
        inner = _TaggedOpenAlex()
        name = "openalex"

    if cache_dir:
        return CachedLiteratureClient(
            inner, backend_name=name, cache_dir=cache_dir, ttl_s=cache_ttl_s
        )
    return inner
