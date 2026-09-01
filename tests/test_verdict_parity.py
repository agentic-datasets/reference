"""The port must not quietly diverge from the Rust original.

PLAN.md open question 1 chose reimplementation over binding, on condition that
the serialised strings are asserted to match `ok-governed-motion`. This is that
assertion. The literals below are the contract; the optional second test reads
the Rust source when it is present on the machine and checks the literals are
still what that source says.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

from agentic_dataset.verdict import (
    Approved,
    Indeterminate,
    IndeterminateReason,
    Refusal,
    RefusalReason,
    Verdict,
    mint_approval,
)

# From ok-governed-motion crates/gov/src/policy.rs, IndeterminateReason::as_str
EXPECTED_REASONS = {"EVALUATOR_UNAVAILABLE", "EVALUATOR_TIMEOUT"}
EXPECTED_RATIONALES = {
    "EVALUATOR_UNAVAILABLE": "the policy authority could not be reached",
    "EVALUATOR_TIMEOUT": "the policy authority did not answer within the budget",
}


def test_indeterminate_reasons_match_the_rust_strings():
    assert {r.value for r in IndeterminateReason} == EXPECTED_REASONS


def test_indeterminate_rationales_match_the_rust_strings():
    for reason in IndeterminateReason:
        assert reason.rationale == EXPECTED_RATIONALES[reason.value]


def test_there_are_exactly_two_indeterminate_reasons():
    """A third reason is drift, not a feature.

    `docs/ARCHITECTURE.md` section 2.3 lists an incomplete descriptor as a
    cause of INDETERMINATE. This implementation refuses that case instead --
    see docs/FINDINGS.md F-001 -- and this test is what stops the two
    documents being reconciled by quietly adding a member here.
    """
    assert len(IndeterminateReason) == 2


def test_verdict_wire_strings():
    assert Verdict.GRANTED == "GRANTED"
    assert Verdict.REFUSED == "REFUSED"
    assert Verdict.INDETERMINATE == "INDETERMINATE"


def test_only_approval_yields_a_token():
    approval = mint_approval(
        request_id="r", dataset_id="d", capability="c",
        policy_id=None, policy_version="v", trace="t",
    )
    assert Verdict.granted(approval).approved() is approval
    assert Verdict.refused(Refusal(RefusalReason.INSUFFICIENT_PRIVILEGE)).approved() is None
    assert (
        Verdict.indeterminate_(
            Indeterminate(IndeterminateReason.EVALUATOR_TIMEOUT)
        ).approved()
        is None
    )


def test_approval_cannot_be_constructed_outside_the_admission_module():
    with pytest.raises(RuntimeError):
        Approved(
            request_id="r", dataset_id="d", capability="c",
            policy_id=None, policy_version="v", trace="t",
        )


def test_indeterminate_carries_no_policy_id():
    """No rule produced the outcome, so naming one would be a false attribution."""
    verdict = Verdict.indeterminate_(
        Indeterminate(IndeterminateReason.EVALUATOR_UNAVAILABLE)
    )
    assert verdict.policy_id is None
    assert verdict.to_dict()["rationale"]


def _rust_policy_source() -> Path | None:
    override = os.environ.get("GOVERNED_MOTION_SRC")
    candidates = [Path(override)] if override else []
    here = Path(__file__).resolve()
    candidates += [
        parent / "ok-governed-motion" / "crates" / "gov" / "src" / "policy.rs"
        for parent in here.parents
    ]
    return next((c for c in candidates if c.is_file()), None)


def test_against_the_rust_source_when_it_is_present():
    """Checked out beside this repository, the literals are verified directly.

    Skipped elsewhere rather than vendored, because a copy of the Rust file in
    this repository would be one more thing that can drift.
    """
    source = _rust_policy_source()
    if source is None:
        pytest.skip("ok-governed-motion not checked out beside this repository")
    text = source.read_text()
    for reason in EXPECTED_REASONS:
        assert f'"{reason}"' in text, f"{reason} is not in {source}"
    for rationale in EXPECTED_RATIONALES.values():
        assert f'"{rationale}"' in text, f"rationale drifted: {rationale}"
