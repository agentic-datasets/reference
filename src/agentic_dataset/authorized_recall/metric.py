"""Authorized Recall@K, defined over a predicate rather than over a control plane.

The metric takes `authorized: Callable[[str], bool]`, not a `Principal`, and
nothing else in this package imports the reference implementation. That is
deliberate: the quantity is a property of policy-conditioned retrieval, not of
this architecture, and a system with RBAC, ABAC, row-level security or a
multi-tenant vector store can use it without adopting anything here.

See README.md in this directory for the mathematical definition and for the
proof that the pre/post-filter gap is non-negative.
"""

from __future__ import annotations

import math
from typing import Callable, Iterable, Sequence

__all__ = [
    "Authorized",
    "recall_at_k",
    "authorized_recall_at_k",
    "precision_at_k",
    "reciprocal_rank",
    "ndcg_at_k",
    "unusable_fraction_at_k",
    "post_filter",
    "pre_filter",
]

Authorized = Callable[[str], bool]


def recall_at_k(retrieved: Sequence[str], relevant: Iterable[str], k: int) -> float:
    """|R ∩ L_K| / |R|. Authorization-blind, and 1.0 on an empty relevant set."""
    rel = set(relevant)
    if not rel:
        return 1.0
    return len(rel & set(retrieved[:k])) / len(rel)


def authorized_recall_at_k(
    retrieved: Sequence[str],
    relevant: Iterable[str],
    authorized: Authorized,
    k: int,
) -> float:
    """|R_A ∩ L_K| / |R_A|, where R_A = { d ∈ R : authorized(d) }.

    Recall over the subset the caller may actually use. Plain Recall@K counts a
    retrieved item the caller cannot touch as a success; it is not one, and it
    has spent one of the K slots.

    Two conventions, decided rather than left to fall out of the arithmetic:

    * **R_A empty → 1.0.** The system cannot be faulted for failing to surface
      what it must not surface. This inflates the mean over a population
      containing such pairs, so report the restricted mean alongside it.
    * **Retrieved-but-unauthorized items are neither credited nor penalised
      here.** They are a separate quantity, `unusable_fraction_at_k`.

    When `authorized` is identically true this equals `recall_at_k`.
    """
    rel = set(relevant)
    authorized_relevant = {d for d in rel if authorized(d)}
    if not authorized_relevant:
        return 1.0
    return len(authorized_relevant & set(retrieved[:k])) / len(authorized_relevant)


def unusable_fraction_at_k(
    retrieved: Sequence[str], authorized: Authorized, k: int
) -> float:
    """Fraction of the K returned slots the caller cannot act on.

    Reported separately from ARecall because it answers a different question:
    not "did we find what they can use" but "how much of the answer was noise
    to them".
    """
    if k == 0:
        return 0.0
    window = retrieved[:k]
    return sum(1 for d in window if not authorized(d)) / k


def precision_at_k(retrieved: Sequence[str], relevant: Iterable[str], k: int) -> float:
    rel = set(relevant)
    return len(rel & set(retrieved[:k])) / k if k else 0.0


def reciprocal_rank(retrieved: Sequence[str], relevant: Iterable[str]) -> float:
    rel = set(relevant)
    for i, item in enumerate(retrieved, start=1):
        if item in rel:
            return 1.0 / i
    return 0.0


def ndcg_at_k(retrieved: Sequence[str], relevant: Iterable[str], k: int) -> float:
    rel = set(relevant)
    dcg = sum(
        1.0 / math.log2(i + 1)
        for i, item in enumerate(retrieved[:k], start=1)
        if item in rel
    )
    ideal = sum(1.0 / math.log2(i + 1) for i in range(1, min(len(rel), k) + 1))
    return dcg / ideal if ideal else 0.0


# -- where the filter sits ------------------------------------------------
#
# The two arrangements the experiment compares. They differ only in whether
# truncation happens before or after the authorization filter, and that
# difference is the whole finding.

def post_filter(ranking: Sequence[str], authorized: Authorized, k: int) -> list[str]:
    """Truncate, then filter. The naive arrangement: unusable items occupy slots."""
    return [d for d in ranking[:k] if authorized(d)]


def pre_filter(ranking: Sequence[str], authorized: Authorized, k: int) -> list[str]:
    """Filter, then truncate. K slots of usable answers.

    `pre_filter` returns a superset of `post_filter` for every ranking, k and
    predicate, because filtering preserves relative order: the authorized items
    within the first K of the ranking are among the first K authorized items of
    the ranking. That is why the measured gap is non-negative by construction
    and not an artefact of the corpus.
    """
    return [d for d in ranking if authorized(d)][:k]
