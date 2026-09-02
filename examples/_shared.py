"""The three requests every example runs."""

from __future__ import annotations

from agentic_dataset.admission import Evaluator
from agentic_dataset.datasets import principals
from agentic_dataset.runtime import Request

QUESTION = "Compare the recovery of batches B001 and B002"


def transcripts() -> dict[str, Request]:
    who = principals()["process_engineer"]
    return {
        "granted": Request(text=QUESTION, principal=who),
        "refused": Request(
            text="Delete the source records for batch B001", principal=who,
            dataset="purification-batches", capability="delete_source",
        ),
        "indeterminate": Request(
            text=QUESTION, principal=who, evaluator=Evaluator(reachable=False)
        ),
    }


def show(runtime) -> None:
    print(f"--- {runtime.name} " + "-" * (56 - len(runtime.name)))
    for label, request in transcripts().items():
        r = runtime.run(request)
        print(
            f"{label:<14} {r.decision:<14} {r.reason:<24} "
            f"grant={'yes' if r.grant else 'no ':<3} "
            f"executed={'yes' if r.executed else 'no'}"
        )
    print()
