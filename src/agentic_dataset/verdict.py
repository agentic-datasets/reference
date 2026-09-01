"""The three-valued verdict, ported from `ok-governed-motion`.

The Rust original adjudicates robot motion; this adjudicates dataset
operations. The domain differs, the shape does not, and that is the point:
`crates/gov/src/policy.rs` defines `Verdict::{Approved, Refused, Indeterminate}`
and mints `Approved` from nowhere but `evaluate`.

Two things are copied verbatim rather than re-derived, because a fourth
implementation in a fourth domain that quietly renames them is not a port:

* the serialised indeterminate reasons ``EVALUATOR_UNAVAILABLE`` and
  ``EVALUATOR_TIMEOUT``;
* their rationales.

`tests/test_verdict_parity.py` asserts both against the Rust source.

One thing is weaker here than in Rust. `Approved` in `policy.rs` carries a
private `Seal` field, so the struct is literally unnameable outside its module
and "the driver ran on a refused intent" describes a program that does not
compile. Python has no such guarantee. The nearest equivalent -- a module
private sentinel that `Approved.__init__` requires -- makes forging an approval
deliberate rather than accidental, and it is deliberate that this is written
down rather than papered over.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

__all__ = [
    "IndeterminateReason",
    "RefusalReason",
    "Approved",
    "Refusal",
    "Indeterminate",
    "Verdict",
    "mint_approval",
]


class IndeterminateReason(Enum):
    """Why the authority could not answer.

    Deliberately not a policy id. No policy refused this operation; the thing
    that could have refused it did not answer, and collapsing the two would put
    a rule's name on an outcome no rule produced.

    These two members are the whole enum, on purpose. `docs/ARCHITECTURE.md`
    section 2.3 also lists an incomplete descriptor as a cause of
    INDETERMINATE; this implementation does not, and `docs/FINDINGS.md` F-001
    records the disagreement rather than resolving it silently.
    """

    EVALUATOR_UNAVAILABLE = "EVALUATOR_UNAVAILABLE"
    EVALUATOR_TIMEOUT = "EVALUATOR_TIMEOUT"

    @property
    def rationale(self) -> str:
        return _RATIONALES[self]


_RATIONALES = {
    IndeterminateReason.EVALUATOR_UNAVAILABLE: (
        "the policy authority could not be reached"
    ),
    IndeterminateReason.EVALUATOR_TIMEOUT: (
        "the policy authority did not answer within the budget"
    ),
}


class RefusalReason(Enum):
    """Why a rule said no.

    Every member names a rule that exists and can be pointed at. There is no
    ``UNKNOWN`` member: a refusal nobody can attribute is the failure mode
    `IndeterminateReason` exists to prevent.
    """

    MISSING_DESCRIPTOR = "MISSING_DESCRIPTOR"
    UNREGISTERED_CAPABILITY = "UNREGISTERED_CAPABILITY"
    PROHIBITED_OPERATION = "PROHIBITED_OPERATION"
    INSUFFICIENT_PRIVILEGE = "INSUFFICIENT_PRIVILEGE"
    CLASSIFICATION_EXCEEDS_CLEARANCE = "CLASSIFICATION_EXCEEDS_CLEARANCE"
    SCHEMA_VERSION_MISMATCH = "SCHEMA_VERSION_MISMATCH"
    FRESHNESS_UNSATISFIABLE = "FRESHNESS_UNSATISFIABLE"
    RETENTION_EXCEEDED = "RETENTION_EXCEEDED"
    EFFECT_NOT_PERMITTED = "EFFECT_NOT_PERMITTED"
    DESCRIPTOR_INVALID = "DESCRIPTOR_INVALID"

    @property
    def policy_id(self) -> str:
        return _POLICY_IDS[self]


_POLICY_IDS = {
    RefusalReason.MISSING_DESCRIPTOR: "AD-POL-001",
    RefusalReason.DESCRIPTOR_INVALID: "AD-POL-002",
    RefusalReason.UNREGISTERED_CAPABILITY: "AD-POL-003",
    RefusalReason.PROHIBITED_OPERATION: "AD-POL-004",
    RefusalReason.INSUFFICIENT_PRIVILEGE: "AD-POL-005",
    RefusalReason.CLASSIFICATION_EXCEEDS_CLEARANCE: "AD-POL-006",
    RefusalReason.SCHEMA_VERSION_MISMATCH: "AD-POL-007",
    RefusalReason.FRESHNESS_UNSATISFIABLE: "AD-POL-008",
    RefusalReason.RETENTION_EXCEEDED: "AD-POL-009",
    RefusalReason.EFFECT_NOT_PERMITTED: "AD-POL-010",
}

# The Python stand-in for the Rust `Seal`. Nothing outside this module holds a
# reference to it, so `Approved(...)` raises unless it came through
# `mint_approval`, which `admission.adjudicate` is the only caller of.
_SEAL = object()


@dataclass(frozen=True)
class Approved:
    """Proof that a policy authority approved a specific operation.

    Execution takes one of these, and nothing else starts execution.
    """

    request_id: str
    dataset_id: str
    capability: str
    policy_id: Optional[str]
    policy_version: str
    trace: str
    reason: str = "PRINCIPAL_AUTHORIZED"
    _seal: Any = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._seal is not _SEAL:
            raise RuntimeError(
                "Approved may only be minted by the admission module. "
                "An approval constructed anywhere else is authority nobody granted."
            )


def mint_approval(
    *,
    request_id: str,
    dataset_id: str,
    capability: str,
    policy_id: Optional[str],
    policy_version: str,
    trace: str,
) -> Approved:
    """The only door to `Approved`. `admission.adjudicate` is its only caller."""
    return Approved(
        request_id=request_id,
        dataset_id=dataset_id,
        capability=capability,
        policy_id=policy_id,
        policy_version=policy_version,
        trace=trace,
        _seal=_SEAL,
    )


@dataclass(frozen=True)
class Refusal:
    reason: RefusalReason
    detail: str = ""

    @property
    def policy_id(self) -> str:
        return self.reason.policy_id


@dataclass(frozen=True)
class Indeterminate:
    """An outcome that is neither permission nor refusal.

    It exists so that "nobody decided" is a row rather than a hole. A fail-open
    and an approval leave the same trace three months later if the only
    evidence of non-evaluation is the absence of evidence.
    """

    reason: IndeterminateReason

    @property
    def rationale(self) -> str:
        return self.reason.rationale


@dataclass(frozen=True)
class Verdict:
    """The three things adjudication can conclude.

    `INDETERMINATE` is terminal in exactly the way `REFUSED` is: no plan, no
    execution, no approval token. What separates them is the record, and an
    auditor reading it needs to tell "a rule said no" from "no rule answered".
    """

    kind: str  # GRANTED | REFUSED | INDETERMINATE
    approval: Optional[Approved] = None
    refusal: Optional[Refusal] = None
    indeterminate: Optional[Indeterminate] = None

    GRANTED = "GRANTED"
    REFUSED = "REFUSED"
    INDETERMINATE = "INDETERMINATE"

    @classmethod
    def granted(cls, approval: Approved) -> "Verdict":
        return cls(kind=cls.GRANTED, approval=approval)

    @classmethod
    def refused(cls, refusal: Refusal) -> "Verdict":
        return cls(kind=cls.REFUSED, refusal=refusal)

    @classmethod
    def indeterminate_(cls, indeterminate: Indeterminate) -> "Verdict":
        return cls(kind=cls.INDETERMINATE, indeterminate=indeterminate)

    def approved(self) -> Optional[Approved]:
        """Only an approval yields the token that starts execution.

        Both other arms return ``None``, which is the whole point:
        indeterminacy is not a weaker approval.
        """
        return self.approval if self.kind == self.GRANTED else None

    @property
    def reason(self) -> str:
        if self.kind == self.GRANTED:
            assert self.approval is not None
            return self.approval.reason
        if self.kind == self.REFUSED:
            assert self.refusal is not None
            return self.refusal.reason.value
        assert self.indeterminate is not None
        return self.indeterminate.reason.value

    @property
    def policy_id(self) -> Optional[str]:
        """`None` on INDETERMINATE, and that is not an omission.

        No policy produced the outcome, so naming one would attribute a
        decision to a rule that never ran.
        """
        if self.kind == self.GRANTED:
            assert self.approval is not None
            return self.approval.policy_id
        if self.kind == self.REFUSED:
            assert self.refusal is not None
            return self.refusal.policy_id
        return None

    def to_dict(self) -> dict:
        out: dict = {"verdict": self.kind, "reason": self.reason,
                     "policy_id": self.policy_id}
        if self.kind == self.INDETERMINATE:
            assert self.indeterminate is not None
            out["rationale"] = self.indeterminate.rationale
        if self.kind == self.REFUSED and self.refusal is not None and self.refusal.detail:
            out["detail"] = self.refusal.detail
        return out
