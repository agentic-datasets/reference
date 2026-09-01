"""Who is asking, and what they are allowed to have asked for.

`AuthorizationScope` is the object that must survive unchanged from admission
to execution, across an MCP boundary, and across an agent handoff. AD-007,
AD-013 and AD-014 are all the same assertion applied at three seams: a
delegation may narrow a scope and may never widen it.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Mapping, Optional

from .descriptor import SENSITIVITY_ORDER

__all__ = ["Principal", "AuthorizationScope"]


@dataclass(frozen=True)
class Principal:
    principal_id: str
    principal_class: str
    grants: Mapping[str, frozenset[str]] = field(default_factory=dict)
    clearance: str = "internal"
    revoked: frozenset[str] = frozenset()

    def granted_capabilities(self, dataset_id: str) -> frozenset[str]:
        if dataset_id in self.revoked:
            return frozenset()
        return frozenset(self.grants.get(dataset_id, frozenset()))

    def may_reach(self, dataset_id: str) -> bool:
        return bool(self.granted_capabilities(dataset_id))

    def clears(self, sensitivity: str) -> bool:
        try:
            return SENSITIVITY_ORDER.index(self.clearance) >= SENSITIVITY_ORDER.index(
                sensitivity
            )
        except ValueError:
            return False

    def revoke(self, dataset_id: str) -> "Principal":
        return Principal(
            principal_id=self.principal_id,
            principal_class=self.principal_class,
            grants=self.grants,
            clearance=self.clearance,
            revoked=self.revoked | {dataset_id},
        )


@dataclass(frozen=True)
class AuthorizationScope:
    """What this request was admitted for. Narrower than the principal's rights.

    A principal may hold `search`, `compare_batches` and `calculate_yield` on a
    dataset; the scope minted for one request names only the capability that
    request was admitted for. Handing the whole standing entitlement to the
    execution layer would make every approved request a general-purpose key.
    """

    principal_class: str
    dataset_id: str
    capabilities: frozenset[str]
    max_sensitivity: str

    def covers(self, other: "AuthorizationScope") -> bool:
        """True when `other` is this scope or a narrowing of it.

        The direction matters. Delegation passes `other` down; if `covers` is
        false the delegate is asking for authority the caller did not have.
        """
        if self.principal_class != other.principal_class:
            return False
        if self.dataset_id != other.dataset_id:
            return False
        if not other.capabilities <= self.capabilities:
            return False
        try:
            return SENSITIVITY_ORDER.index(self.max_sensitivity) >= SENSITIVITY_ORDER.index(
                other.max_sensitivity
            )
        except ValueError:
            return False

    def narrow(
        self,
        capabilities: Optional[frozenset[str]] = None,
        max_sensitivity: Optional[str] = None,
    ) -> "AuthorizationScope":
        caps = self.capabilities if capabilities is None else (capabilities & self.capabilities)
        sens = self.max_sensitivity
        if max_sensitivity is not None and SENSITIVITY_ORDER.index(
            max_sensitivity
        ) < SENSITIVITY_ORDER.index(sens):
            sens = max_sensitivity
        return AuthorizationScope(
            principal_class=self.principal_class,
            dataset_id=self.dataset_id,
            capabilities=caps,
            max_sensitivity=sens,
        )

    def to_dict(self) -> dict:
        return {
            "principal_class": self.principal_class,
            "dataset": self.dataset_id,
            "capabilities": sorted(self.capabilities),
            "max_sensitivity": self.max_sensitivity,
        }

    def digest(self) -> str:
        return hashlib.sha256(
            json.dumps(self.to_dict(), sort_keys=True).encode()
        ).hexdigest()[:16]
