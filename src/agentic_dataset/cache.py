"""The authorization-scoped semantic cache.

Sits after admission and before execution. That position is the whole design:
a cache consulted before admission is a policy bypass with good latency, and
one keyed only on the question is a policy bypass with good latency and a
plausible explanation.

The key carries every dimension along which two identical questions may
legitimately deserve different answers:

    semantic intent + dataset + revision + capability
        + authorization scope + principal class
        + schema version + freshness + policy version

AD-008 is the assertion that dropping any one of them produces a hit that
should have been a miss, and `tests/test_cache_isolation.py` removes them one
at a time to check that.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Optional

from .grant import Grant, GrantAuthority, UnauthorizedExecution
from .principal import AuthorizationScope

__all__ = ["CacheKey", "SemanticCache", "CacheStats"]


@dataclass(frozen=True)
class CacheKey:
    semantic_intent: str
    dataset: str
    revision: str
    capability: str
    authorization_scope: str
    principal_class: str
    schema_version: str
    freshness: Optional[int]
    policy_version: str

    def digest(self) -> str:
        return hashlib.sha256(
            json.dumps(self.__dict__, sort_keys=True, default=str).encode()
        ).hexdigest()

    @classmethod
    def build(
        cls,
        *,
        semantic_intent: str,
        dataset: str,
        revision: str,
        capability: str,
        scope: AuthorizationScope,
        schema_version: str,
        freshness: Optional[int],
        policy_version: str,
    ) -> "CacheKey":
        return cls(
            semantic_intent=semantic_intent,
            dataset=dataset,
            revision=revision,
            capability=capability,
            authorization_scope=scope.digest(),
            principal_class=scope.principal_class,
            schema_version=schema_version,
            freshness=freshness,
            policy_version=policy_version,
        )


@dataclass
class CacheStats:
    lookups: int = 0
    hits: int = 0

    @property
    def hit_rate(self) -> float:
        return self.hits / self.lookups if self.lookups else 0.0

    def to_dict(self) -> dict:
        return {"lookups": self.lookups, "hits": self.hits, "hit_rate": self.hit_rate}


class SemanticCache:
    def __init__(self, authority: GrantAuthority) -> None:
        self._entries: dict[str, Any] = {}
        self._authority = authority
        self.stats = CacheStats()

    def lookup(self, key: CacheKey, grant: Optional[Grant]) -> tuple[bool, Any]:
        """A lookup is an execution and is authorized like one.

        Requiring the grant here is what makes "revoked authorization must not
        hit" true for reasons other than luck. A revoked principal is refused
        at admission and never reaches this call; if some future runtime ever
        reordered the graph, the missing grant would still stop it.
        """
        self.stats.lookups += 1
        try:
            self._authority.verify(
                grant,
                dataset_id=key.dataset,
                dataset_revision=key.revision,
                capability=key.capability,
            )
        except UnauthorizedExecution:
            return False, None
        digest = key.digest()
        if digest in self._entries:
            self.stats.hits += 1
            return True, self._entries[digest]
        return False, None

    def store(self, key: CacheKey, grant: Optional[Grant], value: Any) -> None:
        try:
            self._authority.verify(
                grant,
                dataset_id=key.dataset,
                dataset_revision=key.revision,
                capability=key.capability,
            )
        except UnauthorizedExecution:
            return
        self._entries[key.digest()] = value

    def clear(self) -> None:
        self._entries.clear()
        self.stats = CacheStats()

    def __len__(self) -> int:
        return len(self._entries)
