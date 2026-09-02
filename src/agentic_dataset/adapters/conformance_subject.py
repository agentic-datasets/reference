"""Adapt the reference implementation to the portable conformance interface.

This module lives outside `agentic_dataset.conformance` on purpose. The
harness must not know what a `ControlPlane` is; the mapping from one to the
other is the implementation's problem, and every implementation writes its own.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Callable, Sequence

from ..admission import Evaluator
from ..cache import SemanticCache
from ..conformance.interface import Observation
from ..delegation import DelegatedExecutor
from ..descriptor import DatasetDescriptor, DescriptorRegistry
from ..grant import UnauthorizedExecution
from ..ledger import EvidenceLedger
from ..principal import AuthorizationScope, Principal
from ..runtime import ControlPlane, Request, RunResult

__all__ = ["ReferenceSubject"]


class ReferenceSubject:
    """A `ConformanceSubject` backed by any of the four runtimes."""

    def __init__(
        self,
        runtime_factory: Callable[[ControlPlane], Any],
        plane_factory: Callable[..., ControlPlane],
        name: str,
    ) -> None:
        self.name = name
        self._runtime_factory = runtime_factory
        self._plane_factory = plane_factory
        self._world: dict = {}
        self._plane: ControlPlane | None = None
        self._runtime: Any = None
        self._principals: dict[str, Principal] = {}
        self._last: RunResult | None = None

    # -- interface --------------------------------------------------------
    def load_world(self, world: dict) -> None:
        self._world = world
        self._build()

    def capabilities(self) -> Sequence[dict]:
        assert self._plane is not None
        return [
            {"dataset": b.dataset, "name": b.operation, "effect": b.effect,
             "sensitivity": b.sensitivity, "policy": b.policy}
            for b in self._plane.capabilities.all()
        ]

    def reset(self) -> None:
        self._build()

    def step(self, step: dict) -> Observation | None:
        return getattr(self, f"_op_{step['op']}")(step)

    # -- construction -----------------------------------------------------
    def _build(self) -> None:
        plane = self._plane_factory()
        plane.descriptors = DescriptorRegistry(
            [DatasetDescriptor.from_dict(d) for d in self._world.get("datasets", ())]
        )
        plane.index.registry = plane.descriptors
        plane.index.reindex()
        plane.policy.policy_version = self._world.get("policy_version", "0")
        plane.policy.budget_s = self._world.get("policy_budget_s", 0.25)
        plane.ledger = EvidenceLedger()
        plane.cache = SemanticCache(plane.authority)
        self._plane = plane
        self._runtime = self._runtime_factory(plane)
        self._principals = {
            name: Principal(
                principal_id=spec["principal_id"],
                principal_class=spec["principal_class"],
                grants={k: frozenset(v) for k, v in spec["grants"].items()},
                clearance=spec["clearance"],
            )
            for name, spec in self._world.get("principals", {}).items()
        }
        self._last = None

    # -- verbs ------------------------------------------------------------
    def _op_request(self, step: dict) -> Observation:
        assert self._plane is not None
        evaluator = step.get("evaluator") or {}
        before = len(self._plane.ledger)
        result = self._runtime.run(
            Request(
                text=step["text"],
                principal=self._principals[step["principal"]],
                dataset=step.get("dataset"),
                capability=step.get("capability"),
                freshness=step.get("freshness"),
                expected_schema_version=step.get("expected_schema_version"),
                evaluator=Evaluator(
                    reachable=evaluator.get("reachable", True),
                    latency_s=evaluator.get("latency_s", 0.0),
                ),
                grant_ttl_s=step.get("grant_ttl_s"),
            )
        )
        self._last = result
        return self._observe(result, self._plane.ledger, before)

    def _op_delegate(self, step: dict) -> Observation:
        assert self._plane is not None and self._last is not None
        parent = self._last
        requested = AuthorizationScope(
            principal_class=step["scope"]["principal_class"],
            dataset_id=step["scope"]["dataset"],
            capabilities=frozenset(step["scope"]["capabilities"]),
            max_sensitivity=step["scope"]["max_sensitivity"],
        )
        descriptor = self._plane.descriptors.get(step["dataset"])
        executor = DelegatedExecutor(
            step["channel"], self._plane.capabilities, self._plane.authority
        )
        from ..capabilities import ExecutionLog

        log = ExecutionLog()
        errors: list[str] = []
        try:
            executor.invoke(
                target=f"{step['channel']}-target",
                dataset=step["dataset"],
                operation=step["capability"],
                grant=parent.grant,
                parent_scope=parent.scope,
                requested_scope=requested,
                dataset_revision=descriptor.revision if descriptor else "",
                arguments={"batch_ids": ["B001", "B002"]},
                log=log,
            )
        except UnauthorizedExecution as exc:
            errors.append(str(exc))
        return Observation(
            decision=parent.decision,
            reason=parent.reason,
            policy_id=parent.policy_id,
            granted=parent.grant is not None,
            grant_scope=parent.grant.scope.to_dict() if parent.grant else None,
            executed_scope=requested.to_dict() if not errors else None,
            dataset=step["dataset"],
            capability=step["capability"],
            tool_calls=list(log.tool_calls),
            mcp_calls=list(log.mcp_calls),
            a2a_calls=list(log.a2a_calls),
            errors=errors,
        )

    def _op_grant(self, step: dict) -> None:
        who = self._principals[step["principal"]]
        grants = {k: set(v) for k, v in who.grants.items()}
        grants.setdefault(step["dataset"], set()).add(step["capability"])
        self._principals[step["principal"]] = Principal(
            principal_id=who.principal_id,
            principal_class=who.principal_class,
            grants={k: frozenset(v) for k, v in grants.items()},
            clearance=who.clearance,
        )
        return None

    def _op_revoke(self, step: dict) -> None:
        self._principals[step["principal"]] = self._principals[step["principal"]].revoke(
            step["dataset"]
        )
        return None

    def _op_set_revision(self, step: dict) -> None:
        """The dataset's data changed. In the MCP configuration that means it
        changed on the far side too -- a verb that only updated the caller's
        copy of the metadata would be modelling a different event."""
        assert self._plane is not None
        descriptor = self._plane.descriptors.get(step["dataset"])
        if descriptor is not None:
            self._plane.register_dataset(replace(descriptor, revision=step["revision"]))
        remote = getattr(self._plane, "remote_descriptors", None)
        if remote is not None:
            far = remote.get(step["dataset"])
            if far is not None:
                remote.register(replace(far, revision=step["revision"]))
        return None

    def _op_set_policy_version(self, step: dict) -> None:
        assert self._plane is not None
        self._plane.policy.policy_version = step["version"]
        return None

    def _op_register_descriptor(self, step: dict) -> None:
        assert self._plane is not None
        self._plane.register_dataset(DatasetDescriptor.from_dict(step["descriptor"]))
        return None

    def _op_reset(self, step: dict) -> None:
        self.reset()
        return None

    # -- mapping ----------------------------------------------------------
    @staticmethod
    def _observe(result: RunResult, ledger: EvidenceLedger, before: int) -> Observation:
        rows = [r.to_dict() for r in ledger.records()[before:]]
        return Observation(
            decision=result.decision,
            reason=result.reason,
            policy_id=result.policy_id,
            rationale=result.rationale,
            granted=result.grant is not None,
            grant_scope=result.grant.scope.to_dict() if result.grant else None,
            executed_scope=result.scope.to_dict() if result.scope and result.executed else None,
            dataset=result.dataset,
            capability=result.capability,
            tool_calls=list(result.execution.tool_calls),
            mcp_calls=list(result.execution.mcp_calls),
            a2a_calls=list(result.execution.a2a_calls),
            cache_hit=result.cache_used,
            result_present=result.result is not None,
            evidence=rows,
            errors=list(result.errors),
        )
