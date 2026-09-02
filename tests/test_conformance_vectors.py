"""The portable suite: the harness, the subjects, the mutants, and the purity
constraint that makes the whole thing mean anything."""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

import pytest

from agentic_dataset.conformance import load_suite, run
from agentic_dataset.conformance.runner import DEFAULT_ROOT

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "conformance"))

from mutations import TARGETS  # noqa: E402
from subjects import subjects  # noqa: E402

SUITE = load_suite()
SUBJECTS = subjects()
ASSERTION_IDS = [f"AD-{i:03d}" for i in range(1, 16)]


def _ids(items):
    return [getattr(s, "name", str(s)) for s in items]


@pytest.fixture(scope="module")
def reports():
    return {s.name: run(s, SUITE) for s in SUBJECTS}


def test_the_suite_covers_all_fifteen_assertions():
    assert list(SUITE.assertions) == ASSERTION_IDS


def test_the_harness_imports_no_implementation():
    """The constraint the portability claim rests on.

    If this fails, the conformance package has grown a dependency on something
    it is supposed to be able to test from outside, and the suite has quietly
    become a test of this codebase again.
    """
    offenders = []
    for path in sorted((REPO / "src/agentic_dataset/conformance").glob("*.py")):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.ImportFrom):
                module = ("." * node.level) + (node.module or "")
            elif isinstance(node, ast.Import):
                module = ",".join(a.name for a in node.names)
            else:
                continue
            if module.startswith("agentic_dataset"):
                offenders.append(f"{path.name}: {module}")
            if module.startswith(".") and module.lstrip(".").split(".")[0] not in (
                "interface", "runner", ""
            ):
                offenders.append(f"{path.name}: {module}")
    assert not offenders, offenders


@pytest.mark.parametrize("subject", SUBJECTS, ids=_ids(SUBJECTS))
@pytest.mark.parametrize("assertion", ASSERTION_IDS)
def test_subject_satisfies_assertion(subject, assertion, reports):
    result = reports[subject.name].by_id(assertion)
    assert result.passed, f"{subject.name} {assertion}: {result.detail}"


def test_an_independent_implementation_passes():
    """Criterion 3 and 4 of M7: the contract is implementable without the
    reference implementation, and the implementation that does so passes."""
    from toy_implementation import ToyImplementation

    report = run(ToyImplementation(), SUITE)
    assert report.passed
    assert report.observations > 50


def test_the_toy_shares_nothing_but_the_interface():
    source = (REPO / "conformance/toy_implementation.py").read_text()
    imported = {
        (node.module or "")
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom)
    }
    from_impl = {m for m in imported if m.startswith("agentic_dataset")}
    assert from_impl == {"agentic_dataset.conformance.interface"}, from_impl


@pytest.mark.parametrize(
    "mutant,target", list(TARGETS.items()), ids=[c.name for c in TARGETS]
)
def test_a_broken_implementation_is_caught_by_the_right_assertion(mutant, target):
    """Criterion 5: the suite is neither vacuous nor merely checking that
    execution succeeded."""
    report = run(mutant(), SUITE)
    caught = [f.assertion for f in report.failures]
    assert target in caught, f"{mutant.name} was not caught by {target}; caught by {caught}"


def test_prohibited_execution_rate_is_zero_for_every_subject(reports):
    for name, report in reports.items():
        result = report.by_id("AD-015")
        assert result.numerator == 0, f"{name}: {result.detail}"
        assert result.denominator > 0


def test_the_committed_vectors_match_the_generator():
    """The JSON is normative; the generator is convenience. They must agree."""
    sys.path.insert(0, str(REPO / "conformance"))
    import generate

    produced = generate.vectors()
    for name, vector in produced.items():
        on_disk = json.loads((DEFAULT_ROOT / "vectors" / f"{name}.json").read_text())
        vector.setdefault("world", "reference")
        assert on_disk == json.loads(json.dumps(vector)), name
    assert json.loads((DEFAULT_ROOT / "worlds" / "reference.json").read_text()) == json.loads(
        json.dumps(generate.world())
    )
