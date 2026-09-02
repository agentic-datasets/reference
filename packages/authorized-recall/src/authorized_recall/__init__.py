"""Authorized Recall@K — retrieval quality over the subset a principal may use.

Self-contained: nothing in this package imports the rest of the repository, so
the metric can be adopted without adopting the control plane. See README.md
here for the definition and the non-negativity proof for the pre/post-filter
gap.
"""

from .metric import (
    Authorized,
    authorized_recall_at_k,
    ndcg_at_k,
    post_filter,
    pre_filter,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
    unusable_fraction_at_k,
)
from .retrieval import TfIdfIndex

__version__ = "0.1.0"

__all__ = [
    "Authorized", "TfIdfIndex", "__version__", "authorized_recall_at_k", "ndcg_at_k",
    "post_filter", "pre_filter", "precision_at_k", "recall_at_k",
    "reciprocal_rank", "unusable_fraction_at_k",
]
