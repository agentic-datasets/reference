"""A TF-IDF index, so the package measures something without pulling in a retriever.

Deliberately plain. The metric is a property of where the authorization filter
sits, and a stronger retriever moves every column together -- so the retriever
here only has to be reproducible, which an embedding model would not be.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Mapping

__all__ = ["TfIdfIndex"]

_TOKEN = re.compile(r"[a-z0-9]+")


class TfIdfIndex:
    def __init__(self, documents: Mapping[str, str]) -> None:
        self._docs = {k: Counter(_TOKEN.findall(v.lower())) for k, v in documents.items()}
        n = len(self._docs) or 1
        df: Counter = Counter()
        for counts in self._docs.values():
            df.update(counts.keys())
        self._idf = {t: math.log((n + 1) / (c + 1)) + 1.0 for t, c in df.items()}

    def _vector(self, counts: Mapping[str, int]) -> dict[str, float]:
        vec = {t: (1 + math.log(c)) * self._idf.get(t, 1.0) for t, c in counts.items()}
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        return {t: v / norm for t, v in vec.items()}

    def rank(self, query: str, k: int) -> list[str]:
        q = self._vector(Counter(_TOKEN.findall(query.lower())))
        scored = []
        for doc_id, counts in self._docs.items():
            d = self._vector(counts)
            score = sum(w * d.get(t, 0.0) for t, w in q.items())
            if score > 0:
                scored.append((doc_id, score))
        scored.sort(key=lambda pair: (-pair[1], pair[0]))
        return [doc_id for doc_id, _ in scored[:k]]
