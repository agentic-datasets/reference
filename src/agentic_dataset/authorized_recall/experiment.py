"""The Authorized Recall@K measurement.

    python -m agentic_dataset.authorized_recall

Runs on the in-memory corpus by default, so it needs no data files. `--json`
reads the committed `evals/datasets/*.json` instead; both produce the same
numbers, because they come from the same generator.
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Callable

from .corpus import CAPABILITIES, build
from .metric import (
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

KS = (1, 3, 5, 10)
DATA = Path(__file__).resolve().parents[3] / "evals" / "datasets"


def _load_from_json() -> tuple[list[dict], list[dict], dict]:
    corpus = json.loads((DATA / "corpus.json").read_text())["datasets"]
    queries = json.loads((DATA / "queries.json").read_text())["queries"]
    profiles = json.loads((DATA / "profiles.json").read_text())["profiles"]
    return corpus, queries, profiles


def _document(dataset: dict) -> str:
    """The text a dataset is indexed under.

    Identical to `descriptor.DatasetDescriptor.text` in the reference
    implementation. It has to be: this experiment and the one reachable through
    the control plane are the same experiment, and two document constructions
    would give two nDCG columns both claiming to be it.
    """
    parts = [dataset["dataset"].replace("-", " "), dataset.get("description", "")]
    parts += [c["name"].replace("_", " ") for c in dataset.get("capabilities", ())]
    parts += [c.get("description", "") for c in dataset.get("capabilities", ())]
    parts += [s.replace("_", " ") for s in dataset.get("schemas", ())]
    return " ".join(p for p in parts if p)


def _predicate(profile: dict) -> Callable[[str], bool]:
    """A profile becomes a predicate. Nothing downstream knows what a principal is."""
    granted = set(profile["grants"])
    return lambda dataset_id: dataset_id in granted


def run(from_json: bool = False) -> dict:
    datasets, queries, profiles = _load_from_json() if from_json else build()
    index = TfIdfIndex({d["dataset"]: _document(d) for d in datasets})
    pool = len(datasets)

    rows: dict[int, dict[str, list[float]]] = {
        k: {key: [] for key in
            ("recall", "arecall_post", "arecall_pre", "precision", "ndcg",
             "unusable", "arecall_post_nz", "arecall_pre_nz")}
        for k in KS
    }
    mrr: list[float] = []
    unauthorized_relevant = total_relevant = 0

    for query in queries:
        relevant = query["relevant"]
        ranking = index.rank(query["query"], k=pool)
        mrr.append(reciprocal_rank(ranking, relevant))
        for profile in profiles.values():
            authorized = _predicate(profile)
            authorized_relevant = [d for d in relevant if authorized(d)]
            total_relevant += len(relevant)
            unauthorized_relevant += len(relevant) - len(authorized_relevant)
            for k in KS:
                post = post_filter(ranking, authorized, k)
                pre = pre_filter(ranking, authorized, k)
                r = rows[k]
                r["recall"].append(recall_at_k(ranking, relevant, k))
                r["precision"].append(precision_at_k(ranking, relevant, k))
                r["ndcg"].append(ndcg_at_k(ranking, relevant, k))
                r["unusable"].append(unusable_fraction_at_k(ranking, authorized, k))
                r["arecall_post"].append(
                    authorized_recall_at_k(post, relevant, authorized, k)
                )
                r["arecall_pre"].append(
                    authorized_recall_at_k(pre, relevant, authorized, k)
                )
                if authorized_relevant:
                    r["arecall_post_nz"].append(r["arecall_post"][-1])
                    r["arecall_pre_nz"].append(r["arecall_pre"][-1])

    results = {}
    for k in KS:
        r = rows[k]
        results[k] = {
            "recall": statistics.mean(r["recall"]),
            "arecall_post": statistics.mean(r["arecall_post"]),
            "arecall_pre": statistics.mean(r["arecall_pre"]),
            "precision": statistics.mean(r["precision"]),
            "ndcg": statistics.mean(r["ndcg"]),
            "unusable": statistics.mean(r["unusable"]),
            "arecall_post_nonempty": statistics.mean(r["arecall_post_nz"]),
            "arecall_pre_nonempty": statistics.mean(r["arecall_pre_nz"]),
            "n_nonempty": len(r["arecall_pre_nz"]),
        }
        results[k]["gap"] = results[k]["arecall_pre"] - results[k]["arecall_post"]
        results[k]["gap_nonempty"] = (
            results[k]["arecall_pre_nonempty"] - results[k]["arecall_post_nonempty"]
        )
    return {
        "datasets": len(datasets),
        "queries": len(queries),
        "profiles": len(profiles),
        "pairs": len(queries) * len(profiles),
        "unauthorized_relevant": unauthorized_relevant,
        "total_relevant": total_relevant,
        "mrr": statistics.mean(mrr),
        "k": results,
    }


def report(out: dict) -> str:
    lines = [
        f"corpus: {out['datasets']} datasets, {out['queries']} queries, "
        f"{out['profiles']} authorization profiles ({out['pairs']} query-principal pairs)",
        f"relevant-but-unauthorized pairs: {out['unauthorized_relevant']}/"
        f"{out['total_relevant']} "
        f"({out['unauthorized_relevant'] / out['total_relevant']:.1%})",
        f"MRR (authorization-blind): {out['mrr']:.3f}",
        "",
        f"{'K':>3}  {'Recall':>7} {'ARecall':>8} {'ARecall':>8} {'gap':>6}  "
        f"{'P@K':>6} {'nDCG':>6} {'unusable':>8}",
        f"{'':>3}  {'':>7} {'post':>8} {'pre':>8} {'':>6}  {'':>6} {'':>6} {'in top-K':>8}",
    ]
    for k in KS:
        v = out["k"][k]
        lines.append(
            f"{k:>3}  {v['recall']:>7.3f} {v['arecall_post']:>8.3f} "
            f"{v['arecall_pre']:>8.3f} {v['gap']:>+6.3f}  "
            f"{v['precision']:>6.3f} {v['ndcg']:>6.3f} {v['unusable']:>8.1%}"
        )
    n = out["k"][KS[0]]["n_nonempty"]
    lines += [
        "",
        f"excluding query-principal pairs where nothing relevant is authorized "
        f"(n={n} of {out['pairs']}):",
        f"{'K':>3}  {'ARecall post':>12} {'ARecall pre':>12} {'gap':>7}",
    ]
    for k in KS:
        v = out["k"][k]
        lines.append(
            f"{k:>3}  {v['arecall_post_nonempty']:>12.3f} "
            f"{v['arecall_pre_nonempty']:>12.3f} {v['gap_nonempty']:>+7.3f}"
        )
    five = out["k"][5]
    lines += [
        "",
        "At K=5, moving the authorization filter ahead of truncation changes",
        f"Authorized Recall@5 from {five['arecall_post_nonempty']:.3f} to "
        f"{five['arecall_pre_nonempty']:.3f} ({five['gap_nonempty']:+.3f}) on the "
        f"{five['n_nonempty']} pairs where anything",
        f"relevant is authorized at all, while plain Recall@5 stays at "
        f"{five['recall']:.3f} and cannot",
        "see the difference. The gap's sign is guaranteed by the ordering argument in",
        "this package's README; its size is what the corpus determines.",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(prog="agentic_dataset.authorized_recall")
    parser.add_argument("--json", action="store_true",
                        help="read the committed evals/datasets/*.json instead of "
                             "building the corpus in memory")
    parser.add_argument("--emit", metavar="PATH",
                        help="write the result dictionary as JSON")
    args = parser.parse_args()
    out = run(from_json=args.json)
    print(report(out))
    if args.emit:
        Path(args.emit).write_text(
            json.dumps({"k": {str(k): v for k, v in out["k"].items()},
                        **{x: out[x] for x in
                           ("datasets", "queries", "profiles", "pairs", "mrr")}},
                       indent=2) + "\n"
        )
