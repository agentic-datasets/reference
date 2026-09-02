"""The portable conformance harness.

Imports nothing from the reference implementation. Everything it needs -- the
world, the vectors, the expectations -- arrives as JSON from `conformance/` at
the repository root.

    from agentic_dataset.conformance import load_suite, run
    report = run(my_subject)

`interface.py` says what a subject must expose; `verbs.md` and
`docs/PORTABILITY.md` say what the contract can and cannot reach.
"""

from .interface import ConformanceSubject, Observation, Scope
from .runner import (
    INVARIANTS,
    AssertionResult,
    SubjectReport,
    Vector,
    VectorSuite,
    load_suite,
    run,
)

__all__ = [
    "INVARIANTS", "AssertionResult", "ConformanceSubject", "Observation",
    "Scope", "SubjectReport", "Vector", "VectorSuite", "load_suite", "run",
]
