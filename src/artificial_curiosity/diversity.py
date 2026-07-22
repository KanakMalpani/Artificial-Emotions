"""Near-duplicate filtering for mode-collapse defense."""

from __future__ import annotations

import re
import unicodedata

from artificial_curiosity.models import RankedQuestion, UnansweredQuestion


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


def is_near_duplicate(
    a: UnansweredQuestion,
    b: UnansweredQuestion,
    threshold: float,
) -> bool:
    return jaccard(a.question, b.question) >= threshold


def diversify(
    ranked: list[RankedQuestion],
    threshold: float,
    n_return: int,
) -> list[RankedQuestion]:
    selected: list[RankedQuestion] = []
    for item in ranked:
        if any(
            is_near_duplicate(item.question, s.question, threshold) for s in selected
        ):
            item.flags = list(set(item.flags + ["near_duplicate_suppressed"]))
            continue
        selected.append(item)
        if len(selected) >= n_return:
            break
    for i, item in enumerate(selected, start=1):
        item.rank = i
    return selected
