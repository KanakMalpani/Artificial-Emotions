"""Literature-based discovery: questions nobody has written down.

Everything else in this package ranks questions that already exist — 58 curated
seeds and whatever the packs add. Ranking a list a human typed cannot surprise
you. This module generates candidates *from the literature itself*.

**Swanson ABC linking.** One body of work establishes that A relates to some
concept B. A separate body establishes that B relates to C. If A and C have
essentially never been studied together, then "does A affect C, via B?" is an
open, testable question that nobody has asked — and the bridging concept plus
the papers on either side are the evidence for asking it.

This is not a novel method. Swanson used exactly this to propose fish oil for
Raynaud's syndrome (1986) and magnesium for migraine (1988), both from
disconnected literatures and both later supported clinically. It is one of the
few discovery techniques with a real track record, and it happens to need
precisely what this package already had lying around: OpenAlex retrieval,
concept tagging, and ``cooccur_study.gap_score``.

**What this does not do.** It proposes; it does not confirm. A disconnect in
the literature is a reason to look, never evidence that a relationship exists.
Absence of co-occurrence can equally mean the pairing is nonsense, already ruled
out informally, or published in a venue OpenAlex indexes poorly. Every candidate
ships with its bridge, its counts, and that caveat attached.

Requires network (OpenAlex). Inject any client with ``.concept_counts()``,
``.cooccurrence_count()`` and ``.search_works()`` to run it offline.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from artificial_emotions.cooccur_study import gap_score
from artificial_emotions.logutil import get_logger, soft_fail
from artificial_emotions.models import Domain, UnansweredQuestion

logger = get_logger("discover")

__all__ = [
    "ABCLink",
    "CachedDiscoveryClient",
    "LocalCorpusClient",
    "DiscoveryClient",
    "discover_links",
    "links_to_questions",
]

# Concepts too broad to bridge anything. OpenAlex tags nearly everything with
# these, so they would dominate every result while carrying no information.
_STOP_CONCEPTS = frozenset(
    {
        "biology",
        "chemistry",
        "physics",
        "medicine",
        "computer science",
        "mathematics",
        "engineering",
        "psychology",
        "materials science",
        "biochemistry",
        "internal medicine",
        "molecular biology",
        "cell biology",
        "genetics",
        "artificial intelligence",
        "machine learning",
        "statistics",
        "economics",
        "political science",
        "sociology",
        "philosophy",
        "history",
        "geography",
        "environmental science",
        "neuroscience",
        "immunology",
        "microbiology",
        "pathology",
        "surgery",
        "physical chemistry",
        "organic chemistry",
        "quantum mechanics",
        "thermodynamics",
        "optics",
        "astrophysics",
        "art",
        "law",
        "business",
        "management",
        "geology",
        "ecology",
        "botany",
        "zoology",
        "anatomy",
        "physiology",
        "endocrinology",
        "cardiology",
        "oncology",
        "psychiatry",
        "pharmacology",
        "bioinformatics",
        "nanotechnology",
        "programming language",
        "operating system",
        "database",
        "telecommunications",
    }
)


class DiscoveryClient(Protocol):
    """What ``discover_links`` needs. ``OpenAlexClient`` satisfies it."""

    def concept_counts(
        self, query: str, *, per_page: int = 50, min_score: float = 0.3
    ) -> dict[str, float]: ...

    def cooccurrence_count(self, a: str, c: str) -> int: ...

    def search_works(self, query: str, per_page: int = 8) -> list[Any]: ...


@dataclass(frozen=True)
class ABCLink:
    """One proposed A–C connection, bridged by B."""

    a: str
    b: str
    c: str
    bridge_strength: float
    c_strength: float
    cooccurrence: int
    gap: float
    evidence_ab: list[str] = field(default_factory=list)
    evidence_bc: list[str] = field(default_factory=list)

    @property
    def question(self) -> str:
        return f"Does {self.a} influence {self.c}, and is {self.b} the mechanism linking them?"

    def to_dict(self) -> dict[str, Any]:
        return {
            "a": self.a,
            "b": self.b,
            "c": self.c,
            "question": self.question,
            "bridge_strength": round(self.bridge_strength, 4),
            "c_strength": round(self.c_strength, 4),
            "ac_cooccurrence": self.cooccurrence,
            "gap_score": round(self.gap, 6),
            "evidence_ab": list(self.evidence_ab),
            "evidence_bc": list(self.evidence_bc),
            "reasoning": (
                f"'{self.a}' and '{self.b}' are studied together; "
                f"'{self.b}' and '{self.c}' are studied together; "
                f"'{self.a}' and '{self.c}' co-occur in {self.cooccurrence} works."
            ),
            "caveat": (
                "A disconnect is a reason to look, not evidence of a relationship. "
                "It may equally mean the pairing is implausible, was ruled out "
                "without publication, or sits in poorly indexed venues."
            ),
        }


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip().lower()


def _is_useful_concept(name: str, *, exclude: set[str]) -> bool:
    low = _norm(name)
    if not low or len(low) < 4:
        return False
    if low in _STOP_CONCEPTS or low in exclude:
        return False
    # Single very common words rarely bridge anything meaningful.
    return not (low.isdigit() or len(low.split()) > 6)


def _titles(client: DiscoveryClient, query: str, limit: int) -> list[str]:
    try:
        hits = client.search_works(query, per_page=limit)
    except Exception as exc:  # noqa: BLE001 — evidence is a nicety, not required
        soft_fail(logger, "Skipping optional discovery evidence titles for %r", query, exc=exc)
        return []
    return [getattr(h, "title", "") or "" for h in hits][:limit]


def discover_links(
    a: str,
    *,
    client: DiscoveryClient,
    max_bridges: int = 4,
    max_links: int = 8,
    cooccurrence_ceiling: int = 400,
    a_side_strength: float = 0.05,
    evidence_per_side: int = 2,
) -> list[ABCLink]:
    """Find concepts C reachable from A through a bridge B but rarely studied with A.

    Args:
        a: the starting concept.
        client: anything satisfying :class:`DiscoveryClient`.
        max_bridges: how many B concepts to expand through.
        max_links: how many candidates to return.
        cooccurrence_ceiling: above this many A-and-C works, the link is already
            being studied and is not a gap.

    Returns:
        Candidates sorted by ``gap_score`` (highest = most disconnected relative
        to how strongly the bridge suggests them).
    """
    a_norm = _norm(a)
    if not a_norm:
        raise ValueError("a must be a non-empty concept")

    a_concepts = client.concept_counts(a)
    bridges = [
        (name, score)
        for name, score in sorted(a_concepts.items(), key=lambda kv: (-kv[1], kv[0]))
        if _is_useful_concept(name, exclude={a_norm})
    ][: max(1, max_bridges)]

    if not bridges:
        logger.warning("no usable bridging concepts for %r", a)
        return []

    # Concepts *strongly* co-tagged with A — a C drawn from here is not a gap.
    # Only the strong tail counts: a broad seed picks up a hundred-plus weak
    # associations, and excluding all of them leaves nothing to discover.
    strongest = max(a_concepts.values(), default=0.0)
    cutoff = strongest * float(a_side_strength)
    a_side = {_norm(n) for n, score in a_concepts.items() if score >= cutoff}
    links: list[ABCLink] = []
    seen_c: set[str] = set()

    for b_name, b_score in bridges:
        try:
            b_concepts = client.concept_counts(b_name)
        except Exception as exc:  # noqa: BLE001 — one bad bridge must not kill the run
            logger.warning("concept fetch failed for bridge %r: %s", b_name, exc)
            continue

        candidates = [
            (name, score)
            for name, score in sorted(b_concepts.items(), key=lambda kv: (-kv[1], kv[0]))
            if _is_useful_concept(name, exclude={a_norm, _norm(b_name)})
            and _norm(name) not in a_side
            and _norm(name) not in seen_c
        ][:6]

        for c_name, c_score in candidates:
            try:
                cooc = client.cooccurrence_count(a, c_name)
            except Exception as exc:  # noqa: BLE001
                logger.warning("co-occurrence check failed for %r/%r: %s", a, c_name, exc)
                continue
            if cooc > cooccurrence_ceiling:
                continue

            seen_c.add(_norm(c_name))
            # Similarity proxy: how strongly the bridge ties both sides together.
            sim = min(1.0, (b_score * c_score) ** 0.5 / 10.0)
            links.append(
                ABCLink(
                    a=a,
                    b=b_name,
                    c=c_name,
                    bridge_strength=float(b_score),
                    c_strength=float(c_score),
                    cooccurrence=int(cooc),
                    gap=gap_score(sim, float(cooc)),
                    evidence_ab=_titles(client, f"{a} {b_name}", evidence_per_side),
                    evidence_bc=_titles(client, f"{b_name} {c_name}", evidence_per_side),
                )
            )

    links.sort(key=lambda link: (-link.gap, link.a, link.c))
    return links[: max(1, max_links)]


def links_to_questions(
    links: list[ABCLink],
    *,
    domain: str | Domain = Domain.GENERAL,
) -> list[UnansweredQuestion]:
    """Turn discovered links into questions the existing pipeline can rank."""
    out: list[UnansweredQuestion] = []
    for i, link in enumerate(links):
        slug = re.sub(r"[^a-z0-9]+", "-", _norm(f"{link.a}-{link.c}")).strip("-")[:44]
        out.append(
            UnansweredQuestion(
                id=f"abc{i}-{slug or 'link'}",
                question=link.question,
                domain=domain,
                operationalization=(
                    f"Establish whether {link.a} measurably changes {link.c}. "
                    f"A first pass: test whether {link.b} mediates the effect — if "
                    f"controlling for {link.b} removes it, the bridge is the "
                    f"mechanism. Falsifier: no measurable association once "
                    f"{link.b} is held constant."
                ),
                why_it_matters=(
                    f"'{link.a}' and '{link.c}' share a well-studied bridge in "
                    f"'{link.b}' yet co-occur in only {link.cooccurrence} indexed "
                    "works — an untested link rather than a settled one."
                ),
                assumptions=[
                    f"OpenAlex indexing of '{link.a}' and '{link.c}' is representative.",
                    "Low co-occurrence reflects a genuine gap, not a naming mismatch.",
                ],
                enabling_questions=[
                    f"Is {link.b} measured consistently across both literatures?",
                    f"Has the {link.a}–{link.c} link been ruled out without publication?",
                ],
                tags=["literature_based_discovery", "swanson_abc", "generated"],
                source="discovery",
            )
        )
    return out


def discover(
    a: str,
    *,
    client: DiscoveryClient | None = None,
    domain: str | Domain = Domain.GENERAL,
    max_bridges: int = 4,
    max_links: int = 8,
    cooccurrence_ceiling: int = 400,
    cache_dir: str | Path | None = None,
    corpus: str | Path | None = None,
    timeout_s: float = 12.0,
) -> dict[str, Any]:
    """Run ABC discovery for concept ``a`` and return links plus questions."""
    source = "injected"
    if client is None:
        if corpus:
            # Offline path: your corpus, no provider, no rate limit.
            client = LocalCorpusClient.from_file(corpus)
            source = "local_corpus"
        else:
            from artificial_emotions.openalex import OpenAlexClient

            client = OpenAlexClient(timeout_s=timeout_s, max_retries=3)
            source = "openalex"
            if cache_dir:
                client = CachedDiscoveryClient(inner=client, cache_dir=Path(cache_dir))

    try:
        links = discover_links(
            a,
            client=client,
            max_bridges=max_bridges,
            max_links=max_links,
            cooccurrence_ceiling=cooccurrence_ceiling,
        )
    except Exception as exc:  # noqa: BLE001 — network path must degrade, not crash
        logger.warning("discovery failed for %r: %s", a, exc)
        return {
            "seed": a,
            "ok": False,
            "source": source,
            "error": str(exc),
            "links": [],
            "questions": [],
            "note": (
                "Discovery needs a source. Pass corpus=<file> to run entirely "
                "offline against your own documents, or retry the networked "
                "backend later — public APIs rate-limit."
            ),
        }

    questions = links_to_questions(links, domain=domain)
    return {
        "seed": a,
        "ok": True,
        "method": "swanson_abc",
        "source": source,
        "count": len(links),
        "links": [link.to_dict() for link in links],
        "questions": [q.model_dump(mode="json") for q in questions],
        "how_to_read": (
            "Each candidate says: A and B are studied together, B and C are "
            "studied together, but A and C are not. That is a place to look."
        ),
        "honesty": "generated_hypotheses",
        "claims_not": [
            "evidence that any proposed relationship exists",
            "a systematic or exhaustive search of the literature",
            "novelty — the link may exist in unindexed or differently-worded work",
            "a substitute for reading the papers",
        ],
        "docs": "research/LITGAP_CORRELATION_STUDY.md",
    }


@dataclass
class CachedDiscoveryClient:
    """Disk-cached wrapper so repeat discovery does not re-hit OpenAlex.

    ABC linking fans out into many small requests — one per bridge, one
    co-occurrence check per candidate — which is exactly the shape that trips
    rate limits. Caching makes the feature usable and is polite to a free
    public API.
    """

    inner: DiscoveryClient
    cache_dir: Path
    ttl_s: float = 604_800.0  # a week; the literature does not move that fast

    def _path(self, kind: str, key: str) -> Path:
        digest = hashlib.sha256(f"{kind}:{key}".encode()).hexdigest()[:20]
        return Path(self.cache_dir) / f"{kind}-{digest}.json"

    def _read(self, kind: str, key: str) -> Any | None:
        path = self._path(kind, key)
        if not path.is_file():
            return None
        if (time.time() - path.stat().st_mtime) > self.ttl_s:
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def _write(self, kind: str, key: str, value: Any) -> None:
        path = self._path(kind, key)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(value), encoding="utf-8")
        except OSError as exc:  # noqa: BLE001 — a cache miss must never fail a run
            logger.warning("discovery cache write failed: %s", exc)

    def concept_counts(
        self, query: str, *, per_page: int = 50, min_score: float = 0.3
    ) -> dict[str, float]:
        cached = self._read("concepts", f"{query}|{per_page}|{min_score}")
        if cached is not None:
            return {str(k): float(v) for k, v in cached.items()}
        fresh = self.inner.concept_counts(query, per_page=per_page, min_score=min_score)
        self._write("concepts", f"{query}|{per_page}|{min_score}", fresh)
        return fresh

    def cooccurrence_count(self, a: str, c: str) -> int:
        cached = self._read("cooccur", f"{a}|{c}")
        if cached is not None:
            return int(cached)
        fresh = self.inner.cooccurrence_count(a, c)
        self._write("cooccur", f"{a}|{c}", fresh)
        return fresh

    def search_works(self, query: str, per_page: int = 8) -> list[Any]:
        return self.inner.search_works(query, per_page=per_page)


@dataclass
class LocalCorpusClient:
    """Discovery over a corpus you supply — no network, no provider lock-in.

    ABC linking needs three things: what concepts a body of work is about, how
    often two concepts appear together, and some titles as evidence. None of
    that requires a specific vendor. Point this at your own corpus — a lab's
    reading list, a BibTeX export, a conference proceedings dump — and the same
    method runs offline.

    Corpus format is a list of documents::

        [{"title": "...", "concepts": ["Blood viscosity", "Fish oil"]}, ...]

    A corpus is only as good as what went into it. Co-occurrence counts here
    describe *your* corpus, not the literature, and the gap they reveal is a gap
    in what you fed it.
    """

    documents: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_file(cls, path: str | Path) -> LocalCorpusClient:
        """Load a corpus from a JSON list or a JSONL file."""
        p = Path(path)
        text = p.read_text(encoding="utf-8")
        if p.suffix == ".jsonl":
            docs = [json.loads(line) for line in text.splitlines() if line.strip()]
        else:
            docs = json.loads(text)
        if not isinstance(docs, list):
            raise ValueError(f"corpus must be a list of documents: {p}")
        return cls(documents=docs)

    def _matching(self, query: str) -> list[dict[str, Any]]:
        q = _norm(query)
        out = []
        for doc in self.documents:
            concepts = {_norm(c) for c in doc.get("concepts") or []}
            if q in concepts or q in _norm(doc.get("title") or ""):
                out.append(doc)
        return out

    def concept_counts(
        self, query: str, *, per_page: int = 50, min_score: float = 0.3
    ) -> dict[str, float]:
        counts: dict[str, float] = {}
        for doc in self._matching(query)[: max(1, per_page)]:
            for concept in doc.get("concepts") or []:
                name = str(concept).strip()
                if name:
                    counts[name] = counts.get(name, 0.0) + 1.0
        return counts

    def cooccurrence_count(self, a: str, c: str) -> int:
        a_n, c_n = _norm(a), _norm(c)
        total = 0
        for doc in self.documents:
            concepts = {_norm(x) for x in doc.get("concepts") or []}
            title = _norm(doc.get("title") or "")
            if (a_n in concepts or a_n in title) and (c_n in concepts or c_n in title):
                total += 1
        return total

    def search_works(self, query: str, per_page: int = 8) -> list[Any]:
        class _Hit:
            def __init__(self, title: str):
                self.title = title

        terms = [t for t in _norm(query).split() if t]
        scored = []
        for doc in self.documents:
            blob = (
                _norm(doc.get("title") or "")
                + " "
                + " ".join(_norm(c) for c in doc.get("concepts") or [])
            )
            hits = sum(1 for t in terms if t in blob)
            if hits:
                scored.append((hits, str(doc.get("title") or "Untitled")))
        scored.sort(key=lambda kv: (-kv[0], kv[1]))
        return [_Hit(title) for _score, title in scored[:per_page]]
