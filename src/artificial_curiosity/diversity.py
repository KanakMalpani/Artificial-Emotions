"""Near-duplicate filtering for mode-collapse defense.

Default backend is normalized Jaccard (offline, no extra deps).
Optional `embedding` backend uses sentence-transformers when installed
(`pip install artificial-curiosity[embeddings]`); otherwise falls back to Jaccard.
"""

from __future__ import annotations

import math
import re
import unicodedata
from typing import Literal

from artificial_curiosity.logutil import get_logger
from artificial_curiosity.models import RankedQuestion, UnansweredQuestion

logger = get_logger("diversity")

DiversityBackend = Literal["jaccard", "embedding"]

_embedding_model = None
_embedding_load_attempted = False


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = text.lower()
    text = text.replace("-", " ").replace("_", " ")
    text = re.sub(r"[^a-z0-9\s]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tokenize(text: str) -> set[str]:
    return set(normalize(text).split())


def jaccard(a: str, b: str) -> float:
    ta, tb = tokenize(a), tokenize(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def embedding_available() -> bool:
    """True if the optional sentence-transformers extra can be imported."""
    try:
        import sentence_transformers  # noqa: F401
    except ImportError:
        return False
    return True


def _get_embedding_model():
    global _embedding_model, _embedding_load_attempted
    if _embedding_model is not None:
        return _embedding_model
    if _embedding_load_attempted:
        return None
    _embedding_load_attempted = True
    try:
        from sentence_transformers import SentenceTransformer

        # Small, widely cached model — only loaded when embedding backend is requested.
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        return _embedding_model
    except Exception as exc:  # noqa: BLE001 — optional extras soft-fail
        logger.warning("Embedding model unavailable; Jaccard fallback will be used: %s", exc)
        return None


def similarity(
    a: str,
    b: str,
    *,
    backend: DiversityBackend = "jaccard",
) -> float:
    """Similarity in [0, 1]. Embedding path falls back to Jaccard if unavailable."""
    if backend == "embedding":
        model = _get_embedding_model()
        if model is not None:
            vectors = model.encode([a, b], normalize_embeddings=True)
            va = [float(x) for x in vectors[0]]
            vb = [float(x) for x in vectors[1]]
            # Normalized vectors → cosine ≡ dot product, already in ~[0, 1] for text.
            return max(0.0, min(1.0, _cosine(va, vb)))
    return jaccard(a, b)


def is_near_duplicate(
    a: UnansweredQuestion,
    b: UnansweredQuestion,
    threshold: float,
    *,
    backend: DiversityBackend = "jaccard",
) -> bool:
    return similarity(a.question, b.question, backend=backend) >= threshold


def diversify(
    ranked: list[RankedQuestion],
    threshold: float,
    n_return: int,
    *,
    backend: DiversityBackend = "jaccard",
) -> list[RankedQuestion]:
    """Greedy near-dup suppression. Jaccard is the default offline path (F4/F13)."""
    effective: DiversityBackend = backend
    if backend == "embedding" and _get_embedding_model() is None:
        effective = "jaccard"

    selected: list[RankedQuestion] = []
    for item in ranked:
        if any(
            is_near_duplicate(item.question, s.question, threshold, backend=effective)
            for s in selected
        ):
            flags = list(set(item.flags + ["near_duplicate_suppressed"]))
            if backend == "embedding" and effective == "jaccard":
                flags = list(set(flags + ["embedding_fallback_jaccard"]))
            item.flags = flags
            continue
        if backend == "embedding" and effective == "jaccard":
            item.flags = list(set(item.flags + ["embedding_fallback_jaccard"]))
        selected.append(item)
        if len(selected) >= n_return:
            break
    for i, item in enumerate(selected, start=1):
        item.rank = i
    return selected
