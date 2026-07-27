"""Swanson ABC linking — the discovery path, run entirely offline.

The headline test is `test_reproduces_the_historical_swanson_finding`: given the
literature structure Swanson faced in 1986, the algorithm must surface
fish oil → Raynaud's via blood viscosity as its top candidate. If a refactor
breaks the method, that is what catches it.

Every test here injects a stub client. Nothing touches OpenAlex.
"""

from __future__ import annotations

import json

import pytest

from artificial_emotions.discover import (
    ABCLink,
    CachedDiscoveryClient,
    discover,
    discover_links,
    links_to_questions,
)


class _Work:
    def __init__(self, title: str):
        self.title = title


class StubClient:
    """Two literatures sharing a bridge but never studied together.

    Mirrors the structure Swanson found: fish oil ↔ blood viscosity is studied,
    blood viscosity ↔ Raynaud's is studied, fish oil ↔ Raynaud's is not.
    """

    CONCEPTS = {
        "fish oil": {
            "Blood viscosity": 8.0,
            "Eicosapentaenoic acid": 6.0,
            "Biology": 9.0,  # stop-concept, must be ignored
            "Medicine": 9.5,  # stop-concept
        },
        "Blood viscosity": {
            "Raynaud disease": 7.0,
            "Vasospasm": 5.0,
            "Fish oil": 2.0,
            "Medicine": 9.0,
        },
        "Eicosapentaenoic acid": {
            "Platelet aggregation": 6.0,
            "Chemistry": 9.0,
        },
    }
    DISCONNECTED = {"Raynaud disease", "Vasospasm", "Platelet aggregation"}

    def __init__(self):
        self.concept_calls: list[str] = []
        self.cooccur_calls: list[tuple[str, str]] = []

    def concept_counts(self, query, *, per_page=50, min_score=0.3):
        self.concept_calls.append(query)
        return dict(self.CONCEPTS.get(query, {}))

    def cooccurrence_count(self, a, c):
        self.cooccur_calls.append((a, c))
        return 0 if c in self.DISCONNECTED else 5000

    def search_works(self, query, per_page=8):
        return [_Work(f"A study of {query}")]


# --- the method ----------------------------------------------------------------------


def test_reproduces_the_historical_swanson_finding():
    """Fish oil → Raynaud's, bridged by blood viscosity, must rank first."""
    links = discover_links("fish oil", client=StubClient())
    assert links
    top = links[0]
    assert top.a == "fish oil"
    assert top.b == "Blood viscosity"
    assert top.c == "Raynaud disease"
    assert top.cooccurrence == 0


def test_well_studied_pairs_are_excluded():
    """A link already being researched is not a gap."""
    links = discover_links("fish oil", client=StubClient())
    assert all(link.cooccurrence <= 400 for link in links)
    assert "Fish oil" not in {link.c for link in links}


def test_broad_concepts_never_become_bridges():
    """'Biology' and 'Medicine' tag half of OpenAlex — they bridge nothing."""
    links = discover_links("fish oil", client=StubClient())
    assert not {link.b.lower() for link in links} & {"biology", "medicine", "chemistry"}


def test_concepts_already_tied_to_a_are_not_candidates():
    links = discover_links("fish oil", client=StubClient())
    # Eicosapentaenoic acid is strongly tied to fish oil, so it cannot be a C.
    assert "Eicosapentaenoic acid" not in {link.c for link in links}


def test_ranking_prefers_the_larger_disconnect():
    links = discover_links("fish oil", client=StubClient())
    gaps = [link.gap for link in links]
    assert gaps == sorted(gaps, reverse=True)


def test_ceiling_controls_what_counts_as_a_gap():
    class Busy(StubClient):
        def cooccurrence_count(self, a, c):
            return 300

    assert discover_links("fish oil", client=Busy(), cooccurrence_ceiling=100) == []
    assert discover_links("fish oil", client=Busy(), cooccurrence_ceiling=500)


def test_max_links_is_respected():
    assert len(discover_links("fish oil", client=StubClient(), max_links=1)) == 1


def test_empty_seed_is_rejected():
    with pytest.raises(ValueError, match="non-empty"):
        discover_links("   ", client=StubClient())


def test_unknown_seed_yields_nothing_rather_than_crashing():
    assert discover_links("no such concept", client=StubClient()) == []


def test_a_failing_bridge_does_not_kill_the_run():
    class Flaky(StubClient):
        def concept_counts(self, query, *, per_page=50, min_score=0.3):
            if query == "Blood viscosity":
                raise RuntimeError("rate limited")
            return super().concept_counts(query, per_page=per_page, min_score=min_score)

    links = discover_links("fish oil", client=Flaky())
    assert links  # the other bridge still produced candidates
    assert "Blood viscosity" not in {link.b for link in links}


def test_a_failing_cooccurrence_check_skips_only_that_candidate():
    class Flaky(StubClient):
        def cooccurrence_count(self, a, c):
            if c == "Raynaud disease":
                raise RuntimeError("rate limited")
            return super().cooccurrence_count(a, c)

    links = discover_links("fish oil", client=Flaky())
    assert "Raynaud disease" not in {link.c for link in links}


def test_evidence_failure_degrades_to_no_titles():
    class NoSearch(StubClient):
        def search_works(self, query, per_page=8):
            raise RuntimeError("down")

    links = discover_links("fish oil", client=NoSearch())
    assert links
    assert links[0].evidence_ab == []


def test_discovery_is_deterministic():
    a = [link.to_dict() for link in discover_links("fish oil", client=StubClient())]
    b = [link.to_dict() for link in discover_links("fish oil", client=StubClient())]
    assert a == b


# --- output contract -------------------------------------------------------------------


def test_link_payload_shows_its_reasoning_and_caveat():
    link = discover_links("fish oil", client=StubClient())[0]
    payload = link.to_dict()
    assert "co-occur in 0 works" in payload["reasoning"]
    assert "not evidence of a relationship" in payload["caveat"]
    assert payload["evidence_ab"] and payload["evidence_bc"]


def test_links_become_pipeline_questions():
    links = discover_links("fish oil", client=StubClient())
    questions = links_to_questions(links)
    assert len(questions) == len(links)
    q = questions[0]
    assert q.source == "discovery"
    assert "swanson_abc" in q.tags
    assert q.operationalization
    assert q.enabling_questions


def test_generated_questions_carry_a_falsifier():
    q = links_to_questions(discover_links("fish oil", client=StubClient()))[0]
    assert "falsifier" in q.operationalization.lower()


def test_generated_question_ids_are_unique():
    questions = links_to_questions(discover_links("fish oil", client=StubClient()))
    ids = [q.id for q in questions]
    assert len(ids) == len(set(ids))


def test_discover_wraps_everything_with_honesty():
    out = discover("fish oil", client=StubClient())
    assert out["ok"] is True
    assert out["method"] == "swanson_abc"
    assert out["links"] and out["questions"]
    joined = " ".join(out["claims_not"]).lower()
    assert "evidence that any proposed relationship exists" in joined
    assert "exhaustive" in joined


def test_discover_degrades_instead_of_raising():
    class Dead:
        def concept_counts(self, *a, **k):
            raise RuntimeError("HTTP 429")

        def cooccurrence_count(self, a, c):
            return 0

        def search_works(self, q, per_page=8):
            return []

    out = discover("fish oil", client=Dead())
    assert out["ok"] is False
    assert "429" in out["error"]
    assert out["links"] == []
    # The failure note must point at the offline escape hatch, not at a vendor.
    assert "corpus" in out["note"].lower()


def test_discover_output_is_json_serialisable():
    json.dumps(discover("fish oil", client=StubClient()))


# --- caching ---------------------------------------------------------------------------


def test_cache_avoids_repeat_network_calls(tmp_path):
    inner = StubClient()
    cached = CachedDiscoveryClient(inner=inner, cache_dir=tmp_path)

    first = cached.concept_counts("fish oil")
    calls_after_first = len(inner.concept_calls)
    second = cached.concept_counts("fish oil")

    assert first == second
    assert len(inner.concept_calls) == calls_after_first  # served from disk


def test_cache_stores_cooccurrence_counts(tmp_path):
    inner = StubClient()
    cached = CachedDiscoveryClient(inner=inner, cache_dir=tmp_path)
    assert cached.cooccurrence_count("fish oil", "Raynaud disease") == 0
    assert cached.cooccurrence_count("fish oil", "Raynaud disease") == 0
    assert len(inner.cooccur_calls) == 1


def test_expired_cache_entries_are_refetched(tmp_path):
    inner = StubClient()
    cached = CachedDiscoveryClient(inner=inner, cache_dir=tmp_path, ttl_s=-1)
    cached.concept_counts("fish oil")
    cached.concept_counts("fish oil")
    assert len(inner.concept_calls) == 2


def test_cache_is_transparent_to_the_algorithm(tmp_path):
    plain = discover_links("fish oil", client=StubClient())
    through_cache = discover_links(
        "fish oil", client=CachedDiscoveryClient(inner=StubClient(), cache_dir=tmp_path)
    )
    assert [x.to_dict() for x in plain] == [x.to_dict() for x in through_cache]


# --- CLI --------------------------------------------------------------------------------


def test_cli_discover_reports_failure_without_network(monkeypatch, capsys):
    """No network in CI — the command must fail cleanly, not traceback."""
    import artificial_emotions.discover as disc

    class Dead:
        def concept_counts(self, *a, **k):
            raise RuntimeError("HTTP 429")

        def cooccurrence_count(self, a, c):
            return 0

        def search_works(self, q, per_page=8):
            return []

    original = disc.discover  # capture before patching, or the lambda recurses
    monkeypatch.setattr(disc, "discover", lambda *a, **k: original(*a, **{**k, "client": Dead()}))
    from artificial_emotions.cli import main

    rc = main(["discover", "fish oil"])
    assert rc == 1
    assert "Discovery failed" in capsys.readouterr().out


def test_abc_link_question_names_all_three_terms():
    link = ABCLink("A", "B", "C", 1.0, 1.0, 0, 0.5)
    assert "A" in link.question and "B" in link.question and "C" in link.question


# --- offline corpus backend -------------------------------------------------------------

_CORPUS = [
    {"title": "Fish oil reduces blood viscosity", "concepts": ["Fish oil", "Blood viscosity"]},
    {"title": "Blood viscosity in Raynaud's", "concepts": ["Blood viscosity", "Raynaud disease"]},
    {"title": "Rheology of small vessels", "concepts": ["Blood viscosity"]},
]


def test_local_corpus_needs_no_network():
    """The method must not be married to any one provider."""
    from artificial_emotions.discover import LocalCorpusClient

    links = discover_links("Fish oil", client=LocalCorpusClient(documents=_CORPUS))
    assert [(link.b, link.c) for link in links] == [("Blood viscosity", "Raynaud disease")]


def test_local_corpus_counts_cooccurrence_within_the_corpus():
    from artificial_emotions.discover import LocalCorpusClient

    client = LocalCorpusClient(documents=_CORPUS)
    assert client.cooccurrence_count("Fish oil", "Blood viscosity") == 1
    assert client.cooccurrence_count("Fish oil", "Raynaud disease") == 0


def test_local_corpus_loads_json_and_jsonl(tmp_path):
    from artificial_emotions.discover import LocalCorpusClient

    as_json = tmp_path / "c.json"
    as_json.write_text(json.dumps(_CORPUS), encoding="utf-8")
    assert len(LocalCorpusClient.from_file(as_json).documents) == 3

    as_jsonl = tmp_path / "c.jsonl"
    as_jsonl.write_text("\n".join(json.dumps(d) for d in _CORPUS), encoding="utf-8")
    assert len(LocalCorpusClient.from_file(as_jsonl).documents) == 3


def test_local_corpus_rejects_a_non_list(tmp_path):
    from artificial_emotions.discover import LocalCorpusClient

    bad = tmp_path / "bad.json"
    bad.write_text('{"not": "a list"}', encoding="utf-8")
    with pytest.raises(ValueError, match="list of documents"):
        LocalCorpusClient.from_file(bad)


def test_discover_reports_which_source_it_used(tmp_path):
    corpus = tmp_path / "c.json"
    corpus.write_text(json.dumps(_CORPUS), encoding="utf-8")
    out = discover("Fish oil", corpus=corpus)
    assert out["ok"] is True
    assert out["source"] == "local_corpus"


def test_bundled_demo_corpus_reproduces_swanson():
    """The shipped example must actually demonstrate the method."""
    from artificial_emotions.discover import LocalCorpusClient
    from artificial_emotions.resources import find_data_file

    path = find_data_file("examples/discovery_corpus_demo.json")
    links = discover_links("Fish oil", client=LocalCorpusClient.from_file(path))
    assert "Raynaud disease" in {link.c for link in links}
