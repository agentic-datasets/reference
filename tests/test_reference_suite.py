"""The white-box suite: AD-001..AD-015 with implementation access.

Parametrised down to one test per assertion per configuration, so a failure
names the assertion and the runtime rather than reporting that "the suite
failed".

These checks reach into `plane.ledger`, `plane.capabilities`, `plane._cache_key`
and `DelegatedExecutor`. That privilege is why they found six defects in this
codebase and why they cannot be pointed at anybody else's. The portable
equivalents are in `tests/test_conformance_vectors.py`; both run, and
`docs/PORTABILITY.md` explains where the two differ.
"""

from __future__ import annotations

import pytest

from agentic_dataset.reference_suite import CHECKS, run_suite

CHECK_IDS = [check.id for check, _ in CHECKS]


@pytest.fixture(scope="module")
def _reports():
    return {}


def _report(reports, runtime_cls, plane_factory):
    key = (runtime_cls.name, plane_factory.__name__)
    if key not in reports:
        reports[key] = run_suite(
            runtime_cls.name, runtime_cls, plane_factory=plane_factory
        )
    return reports[key]


@pytest.mark.parametrize("check_id", CHECK_IDS)
def test_assertion(check_id, runtime_cls, plane_factory, _reports):
    report = _report(_reports, runtime_cls, plane_factory)
    result = report.by_id(check_id)
    assert result.passed, f"{check_id} {result.check.name}: {result.detail} {result.error or ''}"


def test_prohibited_execution_rate_is_exactly_zero(runtime_cls, plane_factory, _reports):
    """AD-015 is the only assertion with a rate, and it is not a threshold."""
    report = _report(_reports, runtime_cls, plane_factory)
    assert report.by_id("AD-015").value == 0.0
