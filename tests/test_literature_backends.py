"""Literature adapters with a stubbed HTTP transport — no network.

Covers the Semantic Scholar backend (selectable via `--literature-backend s2`),
the factory that wires backends together, and the soft-fail contract that keeps
a flaky provider from taking down a run.
"""

from __future__ import annotations

import json
import urllib.error
from typing import Any

import pytest

from artificial_emotions.literature import (
    CachedLiteratureClient,
    MergedLiteratureClient,
    SemanticScholarClient,
    build_literature_client,
)

_SAMPLE = {
    "data": [
        {
            "paperId": "abc123",
            "title": "Scaling laws for sandbagging evaluations",
            "year": 2024,
            "citationCount": 41,
            "abstract": "  We study   whether models withhold capability. " + "word " * 80,
            "externalIds": {"DOI": "10.1000/xyz"},
        },
        {
            "paperId": "def456",
            "title": None,
            "year": None,
            "externalIds": {},
        },
    ]
}


class _FakeResponse:
    def __init__(self, body: dict[str, Any]):
        self._body = json.dumps(body).encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _install_urlopen(monkeypatch, handler):
    import artificial_emotions.literature as lit

    monkeypatch.setattr(lit.urllib.request, "urlopen", handler)


@pytest.fixture
def captured(monkeypatch):
    seen: dict[str, Any] = {}

    def handler(req, timeout=None):
        seen["url"] = req.full_url
        seen["headers"] = {k.lower(): v for k, v in req.headers.items()}
        seen["timeout"] = timeout
        return _FakeResponse(_SAMPLE)

    _install_urlopen(monkeypatch, handler)
    return seen


def test_s2_maps_fields_into_literature_hits(captured):
    hits = SemanticScholarClient().search_works("sandbagging", per_page=5)
    assert len(hits) == 2

    first = hits[0]
    assert first.title == "Scaling laws for sandbagging evaluations"
    assert first.year == 2024
    assert first.cited_by_count == 41
    assert first.source == "semantic_scholar"
    assert first.source_id == "abc123"
    assert first.doi == "https://doi.org/10.1000/xyz"
    assert first.url.endswith("abc123")
    # Abstract is collapsed and truncated to a snippet.
    assert first.abstract_snippet
    assert len(first.abstract_snippet.split()) <= 60
    assert "  " not in first.abstract_snippet


def test_s2_gives_untitled_papers_a_placeholder(captured):
    assert SemanticScholarClient().search_works("q")[1].title == "Untitled"


def test_s2_caps_the_page_size(captured):
    SemanticScholarClient().search_works("q", per_page=500)
    assert "limit=20" in captured["url"]


def test_s2_requests_the_fields_it_maps(captured):
    SemanticScholarClient().search_works("q")
    for field in ("title", "year", "externalIds", "citationCount", "abstract"):
        assert field in captured["url"]


def test_s2_sends_the_api_key_header_only_when_configured(monkeypatch, captured):
    monkeypatch.delenv("S2_API_KEY", raising=False)
    monkeypatch.delenv("SEMANTIC_SCHOLAR_API_KEY", raising=False)
    SemanticScholarClient().search_works("q")
    assert "x-api-key" not in captured["headers"]

    SemanticScholarClient(api_key="secret").search_works("q")
    assert captured["headers"]["x-api-key"] == "secret"


def test_s2_reads_the_api_key_from_either_env_name(monkeypatch, captured):
    monkeypatch.delenv("S2_API_KEY", raising=False)
    monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", "from-alias")
    assert SemanticScholarClient().api_key == "from-alias"

    monkeypatch.setenv("S2_API_KEY", "preferred")
    assert SemanticScholarClient().api_key == "preferred"


def test_s2_honors_the_configured_timeout(captured):
    SemanticScholarClient(timeout_s=3.5).search_works("q")
    assert captured["timeout"] == 3.5


def test_s2_wraps_http_errors_with_the_status_code(monkeypatch):
    def handler(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, 429, "rate limited", {}, None)

    _install_urlopen(monkeypatch, handler)
    with pytest.raises(RuntimeError, match="429"):
        SemanticScholarClient().search_works("q")


def test_s2_wraps_transport_errors(monkeypatch):
    def handler(req, timeout=None):
        raise TimeoutError("connection timed out")

    _install_urlopen(monkeypatch, handler)
    with pytest.raises(RuntimeError, match="fetch failed"):
        SemanticScholarClient().search_works("q")


def test_s2_tolerates_a_payload_with_no_data_key(monkeypatch):
    _install_urlopen(monkeypatch, lambda req, timeout=None: _FakeResponse({}))
    assert SemanticScholarClient().search_works("q") == []


# --- factory ------------------------------------------------------------------------


@pytest.mark.parametrize("backend", ["none", "off", "disabled"])
def test_factory_can_disable_literature(backend: str):
    assert build_literature_client(backend) is None


@pytest.mark.parametrize("backend", ["semantic_scholar", "s2", "semanticscholar"])
def test_factory_aliases_resolve_to_semantic_scholar(backend: str):
    assert isinstance(build_literature_client(backend), SemanticScholarClient)


@pytest.mark.parametrize("backend", ["both", "merge", "multi"])
def test_factory_aliases_resolve_to_merged(backend: str):
    assert isinstance(build_literature_client(backend), MergedLiteratureClient)


@pytest.mark.parametrize("backend", ["openalex", "", "something-unrecognized"])
def test_factory_defaults_to_openalex(backend: str):
    client = build_literature_client(backend)
    assert client is not None
    assert not isinstance(client, SemanticScholarClient | MergedLiteratureClient)


def test_factory_wraps_in_a_cache_when_a_directory_is_given(tmp_path):
    client = build_literature_client("openalex", cache_dir=tmp_path)
    assert isinstance(client, CachedLiteratureClient)


def test_factory_tags_openalex_hits_with_their_source(monkeypatch):
    import artificial_emotions.literature as lit
    from artificial_emotions.models import LiteratureHit

    class FakeOpenAlex:
        def __init__(self, *a, **k):
            pass

        def search_works(self, query: str, per_page: int = 8):
            return [LiteratureHit(title="Untagged", year=2024, openalex_id="W1")]

    monkeypatch.setattr(lit, "OpenAlexClient", FakeOpenAlex)
    hits = build_literature_client("openalex").search_works("q")
    assert hits[0].source == "openalex"
    assert hits[0].source_id == "W1"
