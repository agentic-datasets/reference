"""Policy-aware discovery and the metric that scores it."""

from __future__ import annotations

from agentic_dataset.datasets import descriptor_registry, principals
from agentic_dataset.discovery import (
    SemanticIndex,
    authorized_recall_at_k,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)
from agentic_dataset.principal import Principal


def _index() -> SemanticIndex:
    return SemanticIndex(descriptor_registry())


def test_discovery_surfaces_by_meaning_not_by_name():
    ranked = _index().search("why did recovery drop after polishing", k=3)
    assert "purification-batches" in [d for d, _ in ranked]


def test_authorization_filtering_removes_what_the_caller_cannot_use():
    result = _index().discover(
        "recovery endpoints for subjects", principals()["process_engineer"], k=5
    )
    assert "clinical-private" not in result.authorized_ids


def test_what_is_withheld_is_recorded_not_silently_dropped():
    """"You are not cleared for this" and "no such dataset" are different
    statements, and only one of them is true."""
    result = _index().discover(
        "clinical subject observations", principals()["external_auditor"], k=5
    )
    assert "clinical-private" in result.ranked_ids
    assert "clinical-private" not in result.authorized_ids
    assert "clinical-private" in result.withheld


def test_filtering_before_truncation_returns_more_usable_answers():
    index = _index()
    who = principals()["external_auditor"]
    post = index.discover("recovery of clinical subjects", who, k=1)
    pre = index.discover("recovery of clinical subjects", who, k=1, pool=10)
    assert len(pre.authorized_ids) >= len(post.authorized_ids)


def test_plain_recall_counts_an_unusable_dataset_as_a_success():
    """The reason Authorized Recall@K exists."""
    retrieved = ["clinical-private", "purification-batches"]
    relevant = ["clinical-private", "purification-batches"]
    who = principals()["process_engineer"]
    assert recall_at_k(retrieved, relevant, 1) == 0.5
    assert authorized_recall_at_k(retrieved[:1], relevant, who, 1) == 0.0
    assert authorized_recall_at_k(retrieved, relevant, who, 2) == 1.0


def test_authorized_recall_is_one_when_nothing_relevant_is_authorized():
    """The control plane cannot be faulted for not surfacing what it must not
    surface. Stated as a convention because it changes the mean."""
    nobody = Principal(principal_id="u", principal_class="none", grants={})
    assert authorized_recall_at_k(["a"], ["clinical-private"], nobody, 1) == 1.0


def test_authorized_recall_equals_recall_when_everything_is_authorized():
    who = Principal(
        principal_id="u", principal_class="all",
        grants={"a": frozenset({"search"}), "b": frozenset({"search"})},
    )
    assert authorized_recall_at_k(["a"], ["a", "b"], who, 1) == recall_at_k(["a"], ["a", "b"], 1)


def test_the_other_metrics_behave():
    assert precision_at_k(["a", "b"], ["a"], 2) == 0.5
    assert reciprocal_rank(["x", "a"], ["a"]) == 0.5
    assert reciprocal_rank(["x"], ["a"]) == 0.0
    assert ndcg_at_k(["a"], ["a"], 1) == 1.0
    assert ndcg_at_k(["x", "a"], ["a"], 2) < 1.0
