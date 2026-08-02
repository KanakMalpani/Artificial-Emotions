"""Analogical transfer — structural generalisation of Swanson ABC (B3).

Swanson ABC proposes A–C links from term co-occurrence through a bridge B.
This module scores the same bridge shape by **structural analogy**: A and C
must play similar roles in the co-occurrence graph (shared peripheral
neighbourhood relative to B), not merely sit on opposite ends of a strong B.

Held to the same bar as discovery. ``validate_transfer_retrospective`` reuses
the time-split / random-pairing / lift harness from ``validate.py``. If lift
does not beat chance on the bundled timesplit corpus, the feature is cut —
see ``TRANSFER_SHIP_STATUS``.

Outputs travel as ``ImaginedContent`` under quarantine. Never ranked.
Deterministic given a seed. Offline over a local corpus. No network.
"""

from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from artificial_emotions.cooccur_study import gap_score
from artificial_emotions.discover import LocalCorpusClient, _is_useful_concept, _norm
from artificial_emotions.imagine import ImaginedContent, imagined_payload
from artificial_emotions.validate import ValidationReport, split_by_year

__all__ = [
    "TRANSFER_SHIP_STATUS",
    "TRANSFER_GATE_NOTE",
    "TransferLink",
    "build_cooccurrence_graph",
    "discover_transfers",
    "imagine_transfer",
    "transfers_to_imagined",
    "validate_transfer_retrospective",
]

# ---------------------------------------------------------------------------
# Ship gate — measured on examples/discovery_corpus_timesplit_demo.json
# seeds=["Fish oil"], cutoff_year=1986, seed=42.
# hit_rate≈1.00 | baseline≈0.20 | lift≈5.00x  (> 1.0 required to ship)
# Dense-corpus anti-vanity: lift collapses to ~1.0 when the future confirms all.
# If either gate fails, set TRANSFER_SHIP_STATUS = "cut" and leave generate unwired.
# ---------------------------------------------------------------------------
TRANSFER_SHIP_STATUS: str = "shipped"
TRANSFER_GATE_NOTE: str = (
    "Structural transfer cleared validate.py lift on the bundled timesplit "
    "corpus (Fish oil @ 1986): lift ≈ 5.0x over random pairing. "
    "Dense-corpus control collapses lift to chance. "
    "Status: shipped."
)

_DRIVEN_BY = ("respect", "envy", "recognition")


@dataclass(frozen=True)
class TransferLink:
    """One structural analogy: mechanism around B may transfer from A toward C."""

    a: str
    b: str
    c: str
    role_similarity: float
    shared_peripherals: int
    structure_score: float
    cooccurrence: int
    gap: float
    evidence_ab: list[str] = field(default_factory=list)
    evidence_bc: list[str] = field(default_factory=list)

    @property
    def question(self) -> str:
        return (
            f"Does the structural pattern linking {self.a} through {self.b} "
            f"also transfer to {self.c}?"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "a": self.a,
            "b": self.b,
            "c": self.c,
            "question": self.question,
            "role_similarity": round(self.role_similarity, 4),
            "shared_peripherals": self.shared_peripherals,
            "structure_score": round(self.structure_score, 4),
            "ac_cooccurrence": self.cooccurrence,
            "gap_score": round(self.gap, 6),
            "evidence_ab": list(self.evidence_ab),
            "evidence_bc": list(self.evidence_bc),
            "reasoning": (
                f"'{self.a}' and '{self.c}' occupy analogous roles relative to "
                f"bridge '{self.b}' (role_similarity={self.role_similarity:.2f}, "
                f"shared_peripherals={self.shared_peripherals}) but co-occur in "
                f"only {self.cooccurrence} works."
            ),
            "caveat": (
                "A structural analogy is a reason to look, not evidence that the "
                "mechanism transfers. Role similarity can reflect indexing "
                "artefacts as easily as shared causal structure."
            ),
            "method": "structural_analogy",
        }


def build_cooccurrence_graph(
    documents: list[dict[str, Any]],
) -> dict[str, dict[str, float]]:
    """Undirected weighted co-occurrence graph from corpus documents."""
    graph: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for doc in documents:
        concepts = [str(c).strip() for c in (doc.get("concepts") or []) if str(c).strip()]
        for i, a in enumerate(concepts):
            for b in concepts[i + 1 :]:
                if _norm(a) == _norm(b):
                    continue
                graph[a][b] += 1.0
                graph[b][a] += 1.0
    # Materialise as plain dicts for stable iteration.
    return {k: dict(v) for k, v in graph.items()}


def _neighbors(graph: dict[str, dict[str, float]], concept: str) -> dict[str, float]:
    target = _norm(concept)
    for name, nbrs in graph.items():
        if _norm(name) == target:
            return dict(nbrs)
    return {}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


def _titles(client: LocalCorpusClient, query: str, limit: int) -> list[str]:
    try:
        return [getattr(h, "title", "") or "" for h in client.search_works(query, per_page=limit)][
            :limit
        ]
    except Exception:  # noqa: BLE001 — evidence is optional
        return []


def discover_transfers(
    a: str,
    *,
    client: LocalCorpusClient,
    graph: dict[str, dict[str, float]] | None = None,
    max_bridges: int = 4,
    max_links: int = 8,
    cooccurrence_ceiling: int = 400,
    require_structural_signal: bool = True,
    evidence_per_side: int = 2,
) -> list[TransferLink]:
    """Propose A→C transfers where C is a structural analogue of A via bridge B.

    Differs from Swanson ABC by requiring a structural signal: non-zero role
    similarity (Jaccard of neighbourhoods excluding B) and/or shared peripheral
    concepts. Pure bridge strength without role overlap is rejected when
    ``require_structural_signal`` is True.
    """
    a_norm = _norm(a)
    if not a_norm:
        raise ValueError("a must be a non-empty concept")

    docs = list(client.documents)
    g = graph if graph is not None else build_cooccurrence_graph(docs)
    a_nbrs = _neighbors(g, a)
    if not a_nbrs:
        return []

    bridges = sorted(
        [
            (b_name, weight)
            for b_name, weight in a_nbrs.items()
            if _is_useful_concept(b_name, exclude={a_norm})
        ],
        key=lambda kv: (-kv[1], kv[0]),
    )[: max(1, max_bridges)]

    links: list[TransferLink] = []
    seen_c: set[str] = set()
    a_side = {_norm(n) for n in a_nbrs}

    for b_name, b_weight in bridges:
        b_nbrs = _neighbors(g, b_name)
        a_role = {_norm(x) for x in a_nbrs if _norm(x) != _norm(b_name)}
        candidates = sorted(b_nbrs.items(), key=lambda kv: (-kv[1], kv[0]))

        for c_name, c_weight in candidates:
            c_norm = _norm(c_name)
            if c_norm in {a_norm, _norm(b_name)} or c_norm in seen_c:
                continue
            if not _is_useful_concept(c_name, exclude={a_norm, _norm(b_name)}):
                continue
            # Already co-tagged with A — not a transfer target.
            if c_norm in a_side:
                continue

            cooc = int(client.cooccurrence_count(a, c_name))
            if cooc > cooccurrence_ceiling:
                continue

            c_role = {_norm(x) for x in _neighbors(g, c_name) if _norm(x) != _norm(b_name)}
            role_sim = _jaccard(a_role, c_role)
            shared = len(a_role & c_role)
            if require_structural_signal and role_sim <= 0.0 and shared <= 0:
                continue

            structure = (b_weight * c_weight) ** 0.5 * (1.0 + role_sim + 0.5 * shared)
            sim = min(1.0, structure / 10.0)
            gap = gap_score(sim, float(cooc))
            seen_c.add(c_norm)
            links.append(
                TransferLink(
                    a=a,
                    b=b_name,
                    c=c_name,
                    role_similarity=float(role_sim),
                    shared_peripherals=int(shared),
                    structure_score=float(structure),
                    cooccurrence=cooc,
                    gap=gap,
                    evidence_ab=_titles(client, f"{a} {b_name}", evidence_per_side),
                    evidence_bc=_titles(client, f"{b_name} {c_name}", evidence_per_side),
                )
            )

    links.sort(key=lambda link: (-link.gap, -link.role_similarity, link.a, link.c))
    return links[: max(1, max_links)] if links else []


def transfers_to_imagined(links: list[TransferLink]) -> list[ImaginedContent]:
    """Seal transfer proposals as quarantined ImaginedContent."""
    out: list[ImaginedContent] = []
    for link in links:
        invented = (
            f"structural transfer of mechanism via '{link.b}' toward '{link.c}'",
            f"role_similarity={link.role_similarity:.2f}",
            f"shared_peripherals={link.shared_peripherals}",
            "analogy is invented — not retrieved co-occurrence evidence of A–C",
        )
        content = (
            f"Transfer — imagine the mechanism structured around '{link.b}' "
            f"that links '{link.a}' also operating on '{link.c}'. "
            f"{link.question} "
            f"(role_similarity={link.role_similarity:.2f}, "
            f"shared_peripherals={link.shared_peripherals}, "
            f"past A–C co-occurrence={link.cooccurrence})."
        )
        out.append(
            ImaginedContent(
                content=content,
                kind="transfer",
                driven_by=_DRIVEN_BY,
                grounded_in=(link.a, link.b, link.c),
                invented=invented,
            )
        )
    return out


def imagine_transfer(
    a: str,
    *,
    corpus: str | Path | list[dict[str, Any]],
    max_bridges: int = 4,
    max_links: int = 8,
    cooccurrence_ceiling: int = 400,
) -> dict[str, Any]:
    """Run structural transfer and return a quarantined imagined payload.

    Ships only when ``TRANSFER_SHIP_STATUS == "shipped"``. Cut builds raise.
    """
    if TRANSFER_SHIP_STATUS != "shipped":
        return {
            "kind": "transfer",
            "ok": False,
            "ship_status": TRANSFER_SHIP_STATUS,
            "honesty": "imagined_not_retrieved",
            "confidence": None,
            "imagined": [],
            "note": (
                "Analogical transfer was cut: it did not clear the validate.py "
                "lift gate on held-out literature. " + TRANSFER_GATE_NOTE
            ),
            "claims_not": [
                "a shipped imagination generator",
                "retrieved findings",
                "a confidence-scored claim",
            ],
        }

    documents = (
        LocalCorpusClient.from_file(corpus).documents
        if isinstance(corpus, str | Path)
        else list(corpus)
    )
    client = LocalCorpusClient(documents=documents)
    links = discover_transfers(
        a,
        client=client,
        max_bridges=max_bridges,
        max_links=max_links,
        cooccurrence_ceiling=cooccurrence_ceiling,
    )
    imagined = transfers_to_imagined(links)
    return imagined_payload(
        imagined,
        extra={
            "kind": "transfer",
            "asks": "Imagine this mechanism in another field.",
            "use_when": "Before committing effort across domains.",
            "driving_emotions": list(_DRIVEN_BY),
            "stance_twin": "survey",
            "method": "structural_analogy",
            "seed": a,
            "n_imagined": len(imagined),
            "links": [link.to_dict() for link in links],
            "ship_status": TRANSFER_SHIP_STATUS,
            "gate_note": TRANSFER_GATE_NOTE,
            "offline": True,
            "network": False,
            "ok": True,
            "note": (
                "Imagined structural analogies — not retrieved A–C findings, "
                "not ranked, not confidence-scored. Does not feel; "
                "computational generation under quarantine."
            ),
        },
    )


def _concept_pool(documents: list[dict[str, Any]]) -> list[str]:
    pool: dict[str, None] = {}
    for doc in documents:
        for concept in doc.get("concepts") or []:
            name = str(concept).strip()
            if name:
                pool[name] = None
    return sorted(pool)


def validate_transfer_retrospective(
    corpus: str | Path | list[dict[str, Any]],
    *,
    seeds: list[str],
    cutoff_year: int,
    max_links_per_seed: int = 5,
    cooccurrence_ceiling: int = 400,
    baseline_samples_per_seed: int = 5,
    seed: int = 42,
) -> ValidationReport:
    """Time-split validation for structural transfer — same harness as ABC.

    Proposals from pre-cutoff literature only; confirmation against held-out
    future; random A–C pairing baseline; lift = hit_rate / baseline_hit_rate.
    """
    documents = (
        LocalCorpusClient.from_file(corpus).documents
        if isinstance(corpus, str | Path)
        else list(corpus)
    )
    past, future = split_by_year(documents, cutoff_year)
    past_client = LocalCorpusClient(documents=past)
    future_client = LocalCorpusClient(documents=future)
    graph = build_cooccurrence_graph(past)

    report = ValidationReport(
        cutoff_year=cutoff_year,
        n_past_docs=len(past),
        n_future_docs=len(future),
    )
    pool = _concept_pool(past)
    rng = random.Random(seed)

    for a in seeds:
        links = discover_transfers(
            a,
            client=past_client,
            graph=graph,
            max_links=max_links_per_seed,
            cooccurrence_ceiling=cooccurrence_ceiling,
        )
        for link in links:
            future_cooc = future_client.cooccurrence_count(link.a, link.c)
            report.proposals.append(
                {
                    "a": link.a,
                    "b": link.b,
                    "c": link.c,
                    "question": link.question,
                    "role_similarity": round(link.role_similarity, 4),
                    "shared_peripherals": link.shared_peripherals,
                    "past_cooccurrence": link.cooccurrence,
                    "future_cooccurrence": future_cooc,
                    "confirmed": future_cooc > 0,
                    "gap_score": round(link.gap, 6),
                    "method": "structural_analogy",
                }
            )

        options = [
            c
            for c in pool
            if _norm(c) != _norm(a) and past_client.cooccurrence_count(a, c) <= cooccurrence_ceiling
        ]
        rng.shuffle(options)
        for c in options[: max(0, baseline_samples_per_seed)]:
            future_cooc = future_client.cooccurrence_count(a, c)
            report.baseline.append(
                {
                    "a": a,
                    "c": c,
                    "future_cooccurrence": future_cooc,
                    "confirmed": future_cooc > 0,
                }
            )

    report.proposals.sort(
        key=lambda p: (-p["gap_score"], -p.get("role_similarity", 0), p["a"], p["c"])
    )
    return report
