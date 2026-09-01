"""Deterministic admission. The only door to `Approved`.

`adjudicate` is `evaluate` wrapped with the one thing a pure function cannot
express -- that the authority may not be there. When it is not, the result is
INDETERMINATE and no approval is minted, so execution stays unreachable by
construction rather than by convention.

    if not evaluator.reachable:  -> INDETERMINATE(EVALUATOR_UNAVAILABLE)
    if latency > budget:         -> INDETERMINATE(EVALUATOR_TIMEOUT)
    else:                        -> evaluate() -> GRANTED | REFUSED

No model is consulted anywhere in this module, and none can be: `evaluate` is a
pure function of principal, intent, descriptor, capability and environment.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .descriptor import DatasetCapability, DatasetDescriptor
from .intent import DatasetIntent
from .principal import AuthorizationScope, Principal
from .verdict import (
    Approved,
    Indeterminate,
    IndeterminateReason,
    Refusal,
    RefusalReason,
    Verdict,
    mint_approval,
)

__all__ = ["Environment", "Evaluator", "PolicyEngine", "scope_for"]


@dataclass(frozen=True)
class Environment:
    """Facts about the world at decision time, separate from the descriptor."""

    expected_schema_version: Optional[str] = None
    observation_count: int = 0
    trace_id: str = ""


@dataclass(frozen=True)
class Evaluator:
    """Whether the policy authority can answer, and how long it takes.

    Separate from the facts on purpose. The descriptor describes the dataset;
    this describes the governor. A system that cannot distinguish "the
    principal is not cleared" from "I could not find out whether the principal
    is cleared" is the failure this type exists to prevent.
    """

    reachable: bool = True
    latency_s: float = 0.0


class PolicyEngine:
    """A small internal evaluator.

    PLAN.md open question 2 asks whether policy should be Cedar, OPA/Rego or
    something internal, and answers that the architecture must not depend on
    the answer. It does not: everything outside this class sees a `Verdict`.
    Replacing the body of `evaluate` with a Rego call changes no other module
    and no conformance assertion.
    """

    def __init__(self, policy_version: str = "2026.09.01", budget_s: float = 0.25) -> None:
        self.policy_version = policy_version
        self.budget_s = budget_s

    # -- adjudication -----------------------------------------------------
    def adjudicate(
        self,
        *,
        principal: Principal,
        intent: DatasetIntent,
        descriptor: Optional[DatasetDescriptor],
        capability_name: Optional[str],
        environment: Environment = Environment(),
        evaluator: Evaluator = Evaluator(),
        budget_s: Optional[float] = None,
    ) -> Verdict:
        budget = self.budget_s if budget_s is None else budget_s
        if not evaluator.reachable:
            return Verdict.indeterminate_(
                Indeterminate(IndeterminateReason.EVALUATOR_UNAVAILABLE)
            )
        if evaluator.latency_s > budget:
            return Verdict.indeterminate_(
                Indeterminate(IndeterminateReason.EVALUATOR_TIMEOUT)
            )

        refusal = self.evaluate(
            principal=principal,
            intent=intent,
            descriptor=descriptor,
            capability_name=capability_name,
            environment=environment,
        )
        if refusal is not None:
            return Verdict.refused(refusal)

        assert descriptor is not None and capability_name is not None
        capability = descriptor.capability(capability_name)
        assert capability is not None
        return Verdict.granted(
            mint_approval(
                request_id=intent.request_id,
                dataset_id=descriptor.dataset_id,
                capability=capability_name,
                policy_id=capability.required_policy,
                policy_version=self.policy_version,
                trace=environment.trace_id or intent.request_id,
            )
        )

    # -- the rules --------------------------------------------------------
    def evaluate(
        self,
        *,
        principal: Principal,
        intent: DatasetIntent,
        descriptor: Optional[DatasetDescriptor],
        capability_name: Optional[str],
        environment: Environment = Environment(),
    ) -> Optional[Refusal]:
        """Return the refusal that applies, or `None` when nothing refuses.

        Order is deliberate. A prohibited operation is refused as prohibited
        rather than as unregistered, because "the dataset forbids this" and
        "the dataset has never heard of this" are different findings for
        whoever reads the ledger.
        """
        if descriptor is None:
            return Refusal(RefusalReason.MISSING_DESCRIPTOR, "no descriptor for this dataset")
        problems = descriptor.errors()
        if problems:
            return Refusal(RefusalReason.DESCRIPTOR_INVALID, "; ".join(problems))

        if capability_name is None:
            return Refusal(
                RefusalReason.UNREGISTERED_CAPABILITY,
                "the request resolved to no capability",
            )
        if descriptor.is_prohibited(capability_name):
            return Refusal(
                RefusalReason.PROHIBITED_OPERATION,
                f"{capability_name} is prohibited by {descriptor.dataset_id}",
            )
        capability = descriptor.capability(capability_name)
        if capability is None:
            # AD-006. Default-deny on anything the descriptor does not
            # advertise -- an unlisted name is not an implicitly allowed one.
            return Refusal(
                RefusalReason.UNREGISTERED_CAPABILITY,
                f"{capability_name} is not advertised by {descriptor.dataset_id}",
            )

        if (
            environment.expected_schema_version is not None
            and environment.expected_schema_version != descriptor.schema_version
        ):
            return Refusal(
                RefusalReason.SCHEMA_VERSION_MISMATCH,
                f"caller expects schema {environment.expected_schema_version}, "
                f"dataset is at {descriptor.schema_version}",
            )

        held = principal.granted_capabilities(descriptor.dataset_id)
        if capability_name not in held:
            return Refusal(
                RefusalReason.INSUFFICIENT_PRIVILEGE,
                f"{principal.principal_class} does not hold "
                f"{capability_name} on {descriptor.dataset_id}",
            )
        if not principal.clears(capability.sensitivity):
            return Refusal(
                RefusalReason.CLASSIFICATION_EXCEEDS_CLEARANCE,
                f"{capability_name} is {capability.sensitivity}, "
                f"{principal.principal_class} is cleared to {principal.clearance}",
            )
        if capability.effect == "write" and "write" not in held:
            return Refusal(
                RefusalReason.EFFECT_NOT_PERMITTED,
                f"{capability_name} has effect write and no write grant is held",
            )

        if intent.freshness_requirement is not None and descriptor.age_s > intent.freshness_requirement:
            return Refusal(
                RefusalReason.FRESHNESS_UNSATISFIABLE,
                f"data is {descriptor.age_s}s old, request requires "
                f"{intent.freshness_requirement}s",
            )
        limit = descriptor.retention_contract.get("observations")
        if limit is not None and environment.observation_count > int(limit):
            return Refusal(
                RefusalReason.RETENTION_EXCEEDED,
                f"{environment.observation_count} observations exceeds the "
                f"retention contract of {limit}",
            )
        return None


def scope_for(
    principal: Principal, descriptor: DatasetDescriptor, capability: DatasetCapability
) -> AuthorizationScope:
    """The scope one approval carries: this capability, on this dataset, at
    the lower of the capability's sensitivity and the principal's clearance.

    Not the principal's standing entitlement. Handing that to the execution
    layer would make every approved request a general-purpose key.
    """
    from .descriptor import SENSITIVITY_ORDER

    ceiling = min(
        capability.sensitivity,
        principal.clearance,
        key=SENSITIVITY_ORDER.index,
    )
    return AuthorizationScope(
        principal_class=principal.principal_class,
        dataset_id=descriptor.dataset_id,
        capabilities=frozenset({capability.name}),
        max_sensitivity=ceiling,
    )
