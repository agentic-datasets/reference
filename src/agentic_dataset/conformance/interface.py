"""The conformance interface. Nothing in this package imports the reference
implementation, and this module imports nothing at all beyond the standard
library.

An implementation is conformance-testable when it can do four things:

    load a world        descriptors, principals, a policy version
    report capabilities what it will actually execute, with metadata
    run a step          one control verb, returning an Observation
    reset               forget cache and evidence between vectors

`Observation` is the whole observable surface. If a property cannot be
established from an `Observation`, a world and a sequence of steps, it is not
part of the portable contract -- see `docs/PORTABILITY.md` for the three
sub-properties that turned out to fall outside it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, Sequence, runtime_checkable

__all__ = ["Observation", "Scope", "ConformanceSubject", "DECISIONS"]

DECISIONS = ("GRANTED", "REFUSED", "INDETERMINATE")


@dataclass(frozen=True)
class Scope:
    """An authorization scope, as data. Comparison is defined here so that two
    implementations cannot disagree about what "narrower" means."""

    principal_class: str
    dataset: str
    capabilities: frozenset[str]
    max_sensitivity: str

    SENSITIVITY = ("public", "internal", "confidential", "restricted")

    @classmethod
    def from_dict(cls, raw: dict | None) -> "Scope | None":
        if raw is None:
            return None
        return cls(
            principal_class=raw["principal_class"],
            dataset=raw["dataset"],
            capabilities=frozenset(raw["capabilities"]),
            max_sensitivity=raw["max_sensitivity"],
        )

    def covers(self, other: "Scope") -> bool:
        if self.principal_class != other.principal_class or self.dataset != other.dataset:
            return False
        if not other.capabilities <= self.capabilities:
            return False
        try:
            return self.SENSITIVITY.index(self.max_sensitivity) >= self.SENSITIVITY.index(
                other.max_sensitivity
            )
        except ValueError:
            return False


@dataclass
class Observation:
    """What a subject reports after one step.

    Every field is something an auditor could see from outside. There is no
    handle to a policy object, a ledger or a capability registry, because an
    implementation in another language would not have those and the contract
    must not require them.
    """

    decision: str
    reason: str
    policy_id: str | None = None
    rationale: str | None = None
    granted: bool = False
    grant_scope: dict | None = None
    executed_scope: dict | None = None
    dataset: str | None = None
    capability: str | None = None
    tool_calls: list[str] = field(default_factory=list)
    mcp_calls: list[str] = field(default_factory=list)
    a2a_calls: list[str] = field(default_factory=list)
    cache_hit: bool = False
    result_present: bool = False
    evidence: list[dict] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def executed(self) -> bool:
        return bool(self.tool_calls or self.mcp_calls or self.a2a_calls)

    def to_dict(self) -> dict:
        return {
            "decision": self.decision, "reason": self.reason,
            "policy_id": self.policy_id, "rationale": self.rationale,
            "granted": self.granted, "grant_scope": self.grant_scope,
            "executed_scope": self.executed_scope, "dataset": self.dataset,
            "capability": self.capability, "tool_calls": list(self.tool_calls),
            "mcp_calls": list(self.mcp_calls), "a2a_calls": list(self.a2a_calls),
            "cache_hit": self.cache_hit, "result_present": self.result_present,
            "evidence": list(self.evidence), "errors": list(self.errors),
        }


@runtime_checkable
class ConformanceSubject(Protocol):
    """What an implementation must expose to be tested.

    Deliberately four methods. Every one is something a governed data service
    would already have to be able to do; none of them exists only for the test.
    """

    name: str

    def load_world(self, world: dict) -> None:
        """Adopt a set of descriptors, principals and a policy version."""

    def capabilities(self) -> Sequence[dict]:
        """Every operation this implementation will actually execute.

        Each entry: dataset, name, effect, sensitivity, policy. AD-002 compares
        this against what the world's descriptors advertise, in both
        directions.
        """

    def step(self, step: dict) -> Observation | None:
        """Run one control verb. `None` for verbs that produce no observation."""

    def reset(self) -> None:
        """Forget cache and evidence. Worlds persist until the next load."""
