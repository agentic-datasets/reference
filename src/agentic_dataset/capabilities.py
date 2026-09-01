"""Bounded capabilities, and the wrapper nothing gets past.

The model sees `compare_batches(batch_a, batch_b)`. The control plane knows the
dataset, the effect, the classification and the policy. There is no
`query_database(sql)` for a confused or adversarial model to reach for, because
the registry never exposes the raw function -- only a `BoundCapability` whose
`__call__` demands a grant.

AD-002 (registered), AD-003 (grant required), AD-006 (default-deny on unknown)
and AD-007 (scope not widened) are all enforced here, at one seam, rather than
distributed across the runtimes. That is why four adapters can share it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Optional

from .grant import Grant, GrantAuthority, UnauthorizedExecution
from .principal import AuthorizationScope

__all__ = [
    "ExecutionLog",
    "BoundCapability",
    "CapabilityRegistry",
    "REGISTRY",
    "dataset_capability",
]


@dataclass
class ExecutionLog:
    """What actually ran. The conformance suite asserts on this, not on prose.

    Three lists rather than one, because a refusal that leaks through a
    delegation boundary shows up as an MCP or A2A call while `tool_calls` stays
    empty, and a suite that only watched `tool_calls` would call that a pass.
    """

    tool_calls: list[str] = field(default_factory=list)
    mcp_calls: list[str] = field(default_factory=list)
    a2a_calls: list[str] = field(default_factory=list)
    denied: list[str] = field(default_factory=list)

    @property
    def executed_anything(self) -> bool:
        return bool(self.tool_calls or self.mcp_calls or self.a2a_calls)

    def to_dict(self) -> dict:
        return {
            "tool_calls": list(self.tool_calls),
            "mcp_calls": list(self.mcp_calls),
            "a2a_calls": list(self.a2a_calls),
            "denied": list(self.denied),
        }


class BoundCapability:
    """One operation, with its metadata, callable only with a valid grant."""

    def __init__(
        self,
        fn: Callable[..., Any],
        *,
        dataset: str,
        operation: str,
        effect: str = "read",
        sensitivity: str = "internal",
        policy: Optional[str] = None,
        forward_authorization: bool = False,
    ) -> None:
        # Private, mangled, and never returned by any accessor on this class.
        # Python cannot make it unreachable the way Rust's privacy can; it can
        # make reaching it an act rather than an accident.
        self.__fn = fn
        self.dataset = dataset
        self.operation = operation
        self.effect = effect
        self.sensitivity = sensitivity
        self.policy = policy
        # Set only for capabilities that execute across a boundary, where the
        # far side must be able to verify the grant for itself. A local
        # capability never sees the token: it has already been checked, and
        # handing it on would create a second copy to leak.
        self.forward_authorization = forward_authorization
        self.__doc__ = fn.__doc__
        self.__name__ = operation

    @property
    def signature(self) -> dict:
        return {
            "name": self.operation,
            "dataset": self.dataset,
            "effect": self.effect,
            "sensitivity": self.sensitivity,
            "policy": self.policy,
        }

    def __call__(
        self,
        *args: Any,
        authorization: Optional[Grant] = None,
        authority: Optional[GrantAuthority] = None,
        dataset_revision: str = "",
        requested_scope: Optional[AuthorizationScope] = None,
        log: Optional[ExecutionLog] = None,
        **kwargs: Any,
    ) -> Any:
        if authority is None:
            raise UnauthorizedExecution(
                "no grant authority: a capability cannot verify its own authorization"
            )
        try:
            authority.verify(
                authorization,
                dataset_id=self.dataset,
                dataset_revision=dataset_revision,
                capability=self.operation,
                requested_scope=requested_scope,
            )
        except UnauthorizedExecution:
            if log is not None:
                log.denied.append(f"{self.dataset}.{self.operation}")
            raise
        if log is not None:
            log.tool_calls.append(f"{self.dataset}.{self.operation}")
        if self.forward_authorization:
            kwargs["_authorization"] = authorization
        return self.__fn(*args, **kwargs)


class CapabilityRegistry:
    """The set of operations that exist. Anything not in it does not run."""

    def __init__(self) -> None:
        self._by_key: dict[tuple[str, str], BoundCapability] = {}

    def register(self, capability: BoundCapability) -> BoundCapability:
        self._by_key[(capability.dataset, capability.operation)] = capability
        return capability

    def capability(
        self,
        *,
        dataset: str,
        operation: str,
        effect: str = "read",
        sensitivity: str = "internal",
        policy: Optional[str] = None,
        forward_authorization: bool = False,
    ) -> Callable[[Callable[..., Any]], BoundCapability]:
        def wrap(fn: Callable[..., Any]) -> BoundCapability:
            return self.register(
                BoundCapability(
                    fn,
                    dataset=dataset,
                    operation=operation,
                    effect=effect,
                    sensitivity=sensitivity,
                    policy=policy,
                    forward_authorization=forward_authorization,
                )
            )

        return wrap

    def get(self, dataset: str, operation: str) -> Optional[BoundCapability]:
        return self._by_key.get((dataset, operation))

    def names(self, dataset: str) -> frozenset[str]:
        return frozenset(op for (ds, op) in self._by_key if ds == dataset)

    def all(self) -> Iterable[BoundCapability]:
        return tuple(self._by_key.values())

    def invoke(
        self,
        *,
        dataset: str,
        operation: str,
        grant: Optional[Grant],
        authority: GrantAuthority,
        dataset_revision: str,
        requested_scope: Optional[AuthorizationScope],
        arguments: Optional[dict] = None,
        log: Optional[ExecutionLog] = None,
    ) -> Any:
        bound = self.get(dataset, operation)
        if bound is None:
            # AD-006 at the execution seam as well as the admission seam. An
            # admitted name with no implementation behind it must not become a
            # silent success.
            if log is not None:
                log.denied.append(f"{dataset}.{operation}")
            raise UnauthorizedExecution(
                f"{dataset}.{operation} is not a registered capability"
            )
        return bound(
            authorization=grant,
            authority=authority,
            dataset_revision=dataset_revision,
            requested_scope=requested_scope,
            log=log,
            **(arguments or {}),
        )


REGISTRY = CapabilityRegistry()


def dataset_capability(
    *,
    dataset: str,
    operation: str,
    effect: str = "read",
    sensitivity: str = "internal",
    policy: Optional[str] = None,
) -> Callable[[Callable[..., Any]], BoundCapability]:
    """The decorator from `docs/ARCHITECTURE.md` section 12, on the default registry."""
    return REGISTRY.capability(
        dataset=dataset,
        operation=operation,
        effect=effect,
        sensitivity=sensitivity,
        policy=policy,
    )
