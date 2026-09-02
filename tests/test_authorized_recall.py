"""The metric's stated properties, and the cross-check between its two callers.

The definition, the two conventions and the non-negativity proof live in
`packages/authorized-recall/README.md`. These are the assertions
that keep the code matching what that document claims.
"""

from __future__ import annotations

import pytest

from authorized_recall import (
    authorized_recall_at_k,
    post_filter,
    pre_filter,
    recall_at_k,
    unusable_fraction_at_k,
)
from authorized_recall.corpus import build
from authorized_recall.experiment import run
from agentic_dataset.datasets import descriptor_registry, principals
from agentic_dataset.discovery import SemanticIndex
from agentic_dataset.discovery import authorized_recall_at_k as via_principal

EVERYTHING = lambda _d: True          # noqa: E731
NOTHING = lambda _d: False            # noqa: E731


def test_it_reduces_to_recall_when_everything_is_authorized():
    """ARecall is a strict generalisation of Recall, not a different measurement."""
    retrieved, relevant = ["a", "b", "c"], ["a", "c", "d"]
    for k in (1, 2, 3, 4):
        assert authorized_recall_at_k(retrieved, relevant, EVERYTHING, k) == recall_at_k(
            retrieved, relevant, k
        )


def test_an_empty_authorized_relevant_set_scores_one():
    """A convention, not arithmetic: the system cannot be faulted for not
    surfacing what it must not surface."""
    assert authorized_recall_at_k(["a"], ["b"], NOTHING, 1) == 1.0


def test_plain_recall_credits_an_unusable_result():
    """The reason the metric exists, as a two-line example."""
    retrieved = relevant = ["restricted", "usable"]
    authorized = lambda d: d == "usable"  # noqa: E731
    assert recall_at_k(retrieved[:1], relevant, 1) == 0.5
    assert authorized_recall_at_k(retrieved[:1], relevant, authorized, 1) == 0.0


def test_unusable_fraction_is_reported_separately():
    authorized = lambda d: d == "usable"  # noqa: E731
    assert unusable_fraction_at_k(["restricted", "usable"], authorized, 2) == 0.5


@pytest.mark.parametrize("k", [1, 2, 3, 5, 10])
def test_pre_filter_contains_post_filter_over_the_whole_corpus(k):
    """The ordering argument, checked rather than only argued.

    If this ever fails, the non-negativity proof in the package README is
    wrong and every reported gap is suspect.
    """
    datasets, queries, profiles = build()
    from authorized_recall.experiment import _document, _predicate
    from authorized_recall import TfIdfIndex

    index = TfIdfIndex({d["dataset"]: _document(d) for d in datasets})
    for query in queries:
        ranking = index.rank(query["query"], k=len(datasets))
        for profile in profiles.values():
            authorized = _predicate(profile)
            assert set(post_filter(ranking, authorized, k)) <= set(
                pre_filter(ranking, authorized, k)
            )


def test_the_measured_gap_is_never_negative():
    out = run()
    for k, row in out["k"].items():
        assert row["gap"] >= 0, k
        assert row["gap_nonempty"] >= 0, k


def test_the_headline_number_is_what_the_documents_say():
    """0.853 -> 0.960 at K=5. Quoted in README.md, RESULTS.md and the package
    README; if the corpus or the retriever changes, all four move together or
    this fails."""
    five = run()["k"][5]
    assert round(five["arecall_post_nonempty"], 3) == 0.853
    assert round(five["arecall_pre_nonempty"], 3) == 0.960
    assert round(five["gap_nonempty"], 3) == 0.107
    assert round(five["recall"], 3) == 0.867


def test_the_committed_corpus_matches_the_generator():
    """`evals/datasets/*.json` is the record of what was measured. It has to be
    the same corpus the in-memory build produces, or the record is of something
    else.

    The path is passed in: the `authorized-recall` package ships no data and
    does not know where a repository put any.
    """
    from pathlib import Path

    data = Path(__file__).resolve().parents[1] / "evals" / "datasets"
    assert run(from_json=data)["k"][5] == run()["k"][5]


def test_the_control_plane_path_reproduces_the_standalone_metric():
    """Two callers, one definition.

    `discovery.authorized_recall_at_k` adapts a `Principal` to the predicate
    the metric is defined over. This asserts the adaptation is faithful on the
    reference dataset family.
    """
    index = SemanticIndex(descriptor_registry())
    who = principals()["analyst"]
    query = "compare recovery across purification batches"
    ranked = [d for d, _ in index.search(query, k=10)]
    relevant = ["purification-batches", "clinical-private"]

    authorized = lambda d: bool(who.granted_capabilities(d))  # noqa: E731
    assert via_principal(ranked, relevant, who, 5) == authorized_recall_at_k(
        ranked, relevant, authorized, 5
    )
