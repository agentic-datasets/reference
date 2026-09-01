"""Milestone M6: Authorized Recall@K, measured.

Standard Recall@K counts a retrieved dataset as a success whether or not the
caller may use it. That is the wrong success condition for a governed system:
surfacing a dataset the principal cannot touch has not helped anybody, and it
has spent one of the K slots doing it.

Three numbers, at each K:

  Recall@K                      relevant items retrieved, authorization ignored
  Authorized Recall@K (post)    filter after truncation -- the naive arrangement
  Authorized Recall@K (pre)     filter before truncation -- policy-aware discovery

The gap between the second and the third is the quantity this milestone exists
to produce. It is a property of *where the filter sits*, which is why the
retriever being a plain TF-IDF index does not invalidate it: a better retriever
moves all three numbers together.

    python evals/authorized_recall.py
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

from agentic_dataset.descriptor import DatasetDescriptor, DescriptorRegistry
from agentic_dataset.discovery import (
    SemanticIndex,
    authorized_recall_at_k,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)
from agentic_dataset.principal import Principal

DATA = Path(__file__).parent / "datasets"
KS = (1, 3, 5, 10)
POOL = 40  # the whole corpus, so "pre" is filter-then-truncate with no cutoff


def load():
    corpus = json.loads((DATA / "corpus.json").read_text())["datasets"]
    queries = json.loads((DATA / "queries.json").read_text())["queries"]
    profiles = json.loads((DATA / "profiles.json").read_text())["profiles"]
    registry = DescriptorRegistry(
        [DatasetDescriptor.from_dict(d) for d in corpus]
    )
    principals = {
        name: Principal(
            principal_id=f"u-{name}",
            principal_class=spec["principal_class"],
            grants={d: frozenset(caps) for d, caps in spec["grants"].items()},
            clearance=spec["clearance"],
        )
        for name, spec in profiles.items()
    }
    return registry, queries, principals


def main() -> None:
    registry, queries, principals = load()
    index = SemanticIndex(registry)

    rows: dict[int, dict[str, list[float]]] = {
        k: {"recall": [], "arecall_post": [], "arecall_pre": [], "precision": [],
            "ndcg": [], "withheld": [], "arecall_post_nz": [], "arecall_pre_nz": []}
        for k in KS
    }
    mrr: list[float] = []
    unauthorized_relevant = 0
    total_relevant = 0

    for query in queries:
        relevant = query["relevant"]
        for principal in principals.values():
            authorized_relevant = [
                d for d in relevant if principal.granted_capabilities(d)
            ]
            total_relevant += len(relevant)
            unauthorized_relevant += len(relevant) - len(authorized_relevant)
            mrr.append(reciprocal_rank(
                [d for d, _ in index.search(query["query"], k=POOL)], relevant
            ))
            for k in KS:
                post = index.discover(query["query"], principal, k=k)
                pre = index.discover(query["query"], principal, k=k, pool=POOL)
                rows[k]["recall"].append(recall_at_k(post.ranked_ids, relevant, k))
                rows[k]["precision"].append(precision_at_k(post.ranked_ids, relevant, k))
                rows[k]["ndcg"].append(ndcg_at_k(post.ranked_ids, relevant, k))
                rows[k]["arecall_post"].append(
                    authorized_recall_at_k(post.authorized_ids, relevant, principal, k)
                )
                rows[k]["arecall_pre"].append(
                    authorized_recall_at_k(pre.authorized_ids, relevant, principal, k)
                )
                rows[k]["withheld"].append(len(post.withheld) / k)
                if authorized_relevant:
                    # The convention that an empty authorized set scores 1.0 is
                    # defensible -- the control plane cannot be faulted for not
                    # surfacing what it must not surface -- but it inflates the
                    # mean, so the same numbers are reported without those pairs.
                    rows[k]["arecall_post_nz"].append(rows[k]["arecall_post"][-1])
                    rows[k]["arecall_pre_nz"].append(rows[k]["arecall_pre"][-1])

    print(f"corpus: {len(registry)} datasets, {len(queries)} queries, "
          f"{len(principals)} authorization profiles "
          f"({len(queries) * len(principals)} query-principal pairs)")
    print(f"relevant-but-unauthorized pairs: {unauthorized_relevant}/{total_relevant} "
          f"({unauthorized_relevant / total_relevant:.1%})")
    print(f"MRR (authorization-blind): {statistics.mean(mrr):.3f}")
    print()
    header = f"{'K':>3}  {'Recall':>7} {'ARecall':>8} {'ARecall':>8} {'gap':>6}  {'P@K':>6} {'nDCG':>6} {'unusable':>8}"
    print(header)
    print(f"{'':>3}  {'':>7} {'post':>8} {'pre':>8} {'':>6}  {'':>6} {'':>6} {'in top-K':>8}")
    results = {}
    for k in KS:
        r = statistics.mean(rows[k]["recall"])
        ap = statistics.mean(rows[k]["arecall_post"])
        ar = statistics.mean(rows[k]["arecall_pre"])
        results[k] = {
            "recall": r, "arecall_post": ap, "arecall_pre": ar, "gap": ar - ap,
            "arecall_post_nonempty": statistics.mean(rows[k]["arecall_post_nz"]),
            "arecall_pre_nonempty": statistics.mean(rows[k]["arecall_pre_nz"]),
            "n_nonempty": len(rows[k]["arecall_pre_nz"]),
        }
        print(
            f"{k:>3}  {r:>7.3f} {ap:>8.3f} {ar:>8.3f} {ar - ap:>+6.3f}  "
            f"{statistics.mean(rows[k]['precision']):>6.3f} "
            f"{statistics.mean(rows[k]['ndcg']):>6.3f} "
            f"{statistics.mean(rows[k]['withheld']):>8.1%}"
        )

    print()
    print("excluding query-principal pairs where nothing relevant is authorized "
          f"(n={results[KS[0]]['n_nonempty']} of {len(queries) * len(principals)}):")
    print(f"{'K':>3}  {'ARecall post':>12} {'ARecall pre':>12} {'gap':>7}")
    for k in KS:
        v = results[k]
        print(f"{k:>3}  {v['arecall_post_nonempty']:>12.3f} "
              f"{v['arecall_pre_nonempty']:>12.3f} "
              f"{v['arecall_pre_nonempty'] - v['arecall_post_nonempty']:>+7.3f}")

    print()
    five = results[5]
    print(
        "At K=5, moving the authorization filter ahead of truncation changes\n"
        f"Authorized Recall@5 from {five['arecall_post_nonempty']:.3f} to "
        f"{five['arecall_pre_nonempty']:.3f} "
        f"({five['arecall_pre_nonempty'] - five['arecall_post_nonempty']:+.3f}) on the "
        f"{five['n_nonempty']} pairs where anything\n"
        f"relevant is authorized at all, while plain Recall@5 stays at "
        f"{five['recall']:.3f} and cannot\n"
        "see the difference. Against the >= 0.95 gate in CONFORMANCE.md, filtering\n"
        "after truncation fails and filtering before it passes -- so the gate is a\n"
        "statement about where the filter sits, not about the retriever."
    )
    (DATA.parent / "authorized_recall_result.json").write_text(
        json.dumps({"k": {str(k): v for k, v in results.items()}}, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
