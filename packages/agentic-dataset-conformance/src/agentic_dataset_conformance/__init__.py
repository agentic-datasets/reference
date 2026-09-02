"""The portable conformance suite for the agentic-dataset contract.

Fifteen normative assertions, AD-001 .. AD-015, as language-neutral executable
vectors plus a runner that evaluates them against any implementation through a
four-method interface. It imports no implementation, including the reference
one, and the vectors travel with it.

    from agentic_dataset_conformance import load_suite, run
    report = run(my_subject)
    print(report.passed, [f.assertion for f in report.failures])

The vectors and worlds are the normative artifact and are dedicated to the
public domain under CC0-1.0; the software around them is Apache-2.0. Copy the
vectors into a Rust, Go or TypeScript project and write your own runner --
that is what they are for, and `export_vectors()` exists to make it one call.

See `verbs.md` beside this module for the control-verb vocabulary a subject
must understand, and `interface.py` for what it must expose.
"""

from __future__ import annotations

import shutil
from importlib import resources
from pathlib import Path

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
from .toy import ToyImplementation

__version__ = "0.1.0"

#: The fifteen assertion identifiers, in order.
ASSERTIONS = tuple(f"AD-{i:03d}" for i in range(1, 16))

__all__ = [
    "ASSERTIONS", "AssertionResult", "ConformanceSubject", "INVARIANTS",
    "Observation", "Scope", "SubjectReport", "ToyImplementation", "Vector",
    "VectorSuite", "__version__", "export_vectors", "load_suite", "run",
    "vectors_path",
]


def vectors_path():
    """The packaged normative data as a traversable resource."""
    return resources.files(__package__) / "data"


def export_vectors(destination: str | Path) -> Path:
    """Copy the normative worlds and vectors out, for use anywhere.

    They are CC0-1.0: no attribution required, no conditions. Vendor them into
    another language's repository and write a runner there.
    """
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    with resources.as_file(vectors_path()) as data:
        for sub in ("worlds", "vectors"):
            shutil.copytree(data / sub, destination / sub, dirs_exist_ok=True)
    return destination
