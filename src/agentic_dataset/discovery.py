"""Semantic discovery, and the filter that comes after it.

Two stages, in this order and never the other:

    200 registered datasets -> semantic retrieval -> 10 relevant
        -> authorization filtering -> 3 accessible
        -> capability matching -> the planner

Retrieval is TF-IDF cosine over descriptor text rather than an embedding
model. That is a deliberate limitation: it keeps the core dependency-free and
the ranking reproducible, and the metric this module exists to measure --
`authorized_recall_at_k` -- is a property of the *filter*, not of the retriever.
A better retriever moves both numbers and leaves the gap between them, which is
the quantity of interest. `evals/authorized_recall.py` reports both.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Iterable, Mapping, Optional, Sequence

from .authorized_recall.metric import authorized_recall_at_k as _authorized_recall_at_k
from .authorized_recall.metric import (
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
    unusable_fraction_at_k,
)
from .descriptor import DatasetDescriptor, DescriptorRegistry
from .principal import Principal

__all__ = [
    "SemanticIndex",
    "DiscoveryResult",
    "recall_at_k",
    "precision_at_k",
    "reciprocal_rank",
    "ndcg_at_k",
    "unusable_fraction_at_k",
    "authorized_recall_at_k",
]

_TOKEN = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


@dataclass(frozen=True)
class DiscoveryResult:
    ranked: tuple[tuple[str, float], ...]
    authorized: tuple[tuple[str, float], ...]

    @property
    def ranked_ids(self) -> tuple[str, ...]:
        return tuple(d for d, _ in self.ranked)

    @property
    def authorized_ids(self) -> tuple[str, ...]:
        return tuple(d for d, _ in self.authorized)

    @property
    def withheld(self) -> tuple[str, ...]:
        """Semantically relevant, and not this principal's to see.

        Recorded rather than silently dropped: "the answer omits a dataset you
        are not cleared for" and "no such dataset exists" are different
        statements, and only one of them is true.
        """
        allowed = set(self.authorized_ids)
        return tuple(d for d in self.ranked_ids if d not in allowed)


class SemanticIndex:
    def __init__(self, registry: DescriptorRegistry) -> None:
        self.registry = registry
        self._docs: dict[str, Counter] = {}
        self._idf: dict[str, float] = {}
        self.reindex()

    def reindex(self) -> None:
        self._docs = {
            d.dataset_id: Counter(_tokens(d.text)) for d in self.registry.all()
        }
        n = len(self._docs) or 1
        df: Counter = Counter()
        for counts in self._docs.values():
            df.update(counts.keys())
        self._idf = {t: math.log((n + 1) / (c + 1)) + 1.0 for t, c in df.items()}

    def _vector(self, counts: Mapping[str, int]) -> dict[str, float]:
        vec = {t: (1 + math.log(c)) * self._idf.get(t, 1.0) for t, c in counts.items()}
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        return {t: v / norm for t, v in vec.items()}

    def search(self, query: str, k: int = 10) -> tuple[tuple[str, float], ...]:
        q = self._vector(Counter(_tokens(query)))
        scored = []
        for dataset_id, counts in self._docs.items():
            d = self._vector(counts)
            score = sum(w * d.get(t, 0.0) for t, w in q.items())
            if score > 0:
                scored.append((dataset_id, score))
        scored.sort(key=lambda pair: (-pair[1], pair[0]))
        return tuple(scored[:k])

    def discover(
        self,
        query: str,
        principal: Principal,
        k: int = 10,
        required_capability: Optional[str] = None,
        pool: Optional[int] = None,
    ) -> DiscoveryResult:
        """Rank by meaning, then remove what the principal may not use.

        Filtering after ranking rather than before is what makes `withheld`
        meaningful and what makes `authorized_recall_at_k` measurable: you
        cannot report the gap between what was relevant and what was usable if
        the unusable half was never scored.

        `pool` decides *where* the truncation happens. With `pool=None` the
        index retrieves k and filters what is left, so an unusable dataset
        occupies one of the k slots. With `pool > k` it retrieves a wider
        candidate set, filters, and then truncates, so the k slots are k
        usable answers. The two differ by a measurable amount --
        `evals/authorized_recall.py` reports it -- and the difference is the
        argument for making discovery policy-aware rather than bolting a
        filter onto the end.
        """
        ranked = self.search(query, k=pool or k)
        authorized = []
        for dataset_id, score in ranked:
            descriptor = self.registry.get(dataset_id)
            if descriptor is None:
                continue
            held = principal.granted_capabilities(dataset_id)
            if not held:
                continue
            if required_capability is not None and required_capability not in held:
                continue
            if required_capability is not None:
                cap = descriptor.capability(required_capability)
                if cap is None or not principal.clears(cap.sensitivity):
                    continue
            authorized.append((dataset_id, score))
        return DiscoveryResult(ranked=ranked[:k], authorized=tuple(authorized[:k]))


# -- retrieval metrics ----------------------------------------------------
#
# Defined in `agentic_dataset.authorized_recall`, not here. That package has no
# dependency on the control plane, so the metric can be used by systems that
# never adopt any of this; re-exporting rather than re-implementing is what
# stops the two definitions drifting into two different numbers.
#
# The signatures below take a `Principal` and adapt it to the predicate the
# metric is actually defined over.

def _predicate(principal: Principal, required_capability: Optional[str] = None):
    def authorized(dataset_id: str) -> bool:
        held = principal.granted_capabilities(dataset_id)
        if not held:
            return False
        return required_capability is None or required_capability in held

    return authorized


def authorized_recall_at_k(
    retrieved: Sequence[str],
    relevant: Iterable[str],
    principal: Principal,
    k: int,
    required_capability: Optional[str] = None,
) -> float:
    """Recall over the subset the principal may actually use.

    Thin adapter over `authorized_recall.metric.authorized_recall_at_k`, which
    carries the definition, the two conventions and the proof that the
    pre/post-filter gap is non-negative.
    """
    return _authorized_recall_at_k(
        retrieved, relevant, _predicate(principal, required_capability), k
    )
