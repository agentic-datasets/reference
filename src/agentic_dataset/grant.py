"""The approval token.

    GRANTED        -> approval token -> execution reachable
    REFUSED        -> no token       -> execution unreachable
    INDETERMINATE  -> no token       -> execution unreachable

`mint` takes an `Approved` by value and there is no other constructor, so the
sentence "execution ran on a refused intent" requires forging an approval
first. The token is HMAC-signed over everything it claims, which is what stops
a model that can emit arbitrary strings from emitting a plausible one.
"""

from __future__ import annotations

import hmac
import json
import os
import secrets
import time
from dataclasses import dataclass
from hashlib import sha256
from typing import Optional

from .principal import AuthorizationScope
from .verdict import Approved

__all__ = ["Grant", "GrantAuthority", "UnauthorizedExecution"]

DEFAULT_TTL_S = 300


class UnauthorizedExecution(RuntimeError):
    """Raised at the execution boundary, never caught by the control plane.

    A capability invoked without a valid grant is not a bad answer to be
    recovered from; it is the invariant AD-003 exists to detect.
    """


@dataclass(frozen=True)
class Grant:
    grant_id: str
    request_id: str
    dataset_id: str
    dataset_revision: str
    capability: str
    scope: AuthorizationScope
    policy_id: Optional[str]
    policy_version: str
    schema_version: str
    issued_at: float
    expires_at: float
    signature: str

    def claims(self) -> dict:
        return {
            "grant_id": self.grant_id,
            "request_id": self.request_id,
            "dataset": self.dataset_id,
            "revision": self.dataset_revision,
            "capability": self.capability,
            "scope": self.scope.to_dict(),
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "schema_version": self.schema_version,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
        }

    def to_dict(self) -> dict:
        return {**self.claims(), "signature": self.signature}

    @classmethod
    def from_dict(cls, raw: dict) -> "Grant":
        """Rebuild a grant that crossed a wire.

        Nothing here is trusted: the signature is recomputed over the rebuilt
        claims by `GrantAuthority.verify`, so a token edited in transit fails
        the same check a forged one does.
        """
        scope = raw["scope"]
        return cls(
            grant_id=raw["grant_id"],
            request_id=raw["request_id"],
            dataset_id=raw["dataset"],
            dataset_revision=raw["revision"],
            capability=raw["capability"],
            scope=AuthorizationScope(
                principal_class=scope["principal_class"],
                dataset_id=scope["dataset"],
                capabilities=frozenset(scope["capabilities"]),
                max_sensitivity=scope["max_sensitivity"],
            ),
            policy_id=raw["policy_id"],
            policy_version=raw["policy_version"],
            schema_version=raw["schema_version"],
            issued_at=raw["issued_at"],
            expires_at=raw["expires_at"],
            signature=raw["signature"],
        )


class GrantAuthority:
    """Holds the signing key. One per control plane, never handed to a tool."""

    def __init__(self, secret: Optional[bytes] = None, ttl_s: int = DEFAULT_TTL_S) -> None:
        self._secret = secret or os.environ.get("AD_GRANT_SECRET", "").encode() or secrets.token_bytes(32)
        self._ttl_s = ttl_s

    def _sign(self, claims: dict) -> str:
        payload = json.dumps(claims, sort_keys=True).encode()
        return hmac.new(self._secret, payload, sha256).hexdigest()

    def mint(
        self,
        approval: Approved,
        *,
        dataset_revision: str,
        schema_version: str,
        scope: AuthorizationScope,
        now: Optional[float] = None,
        ttl_s: Optional[int] = None,
    ) -> Grant:
        """The only way a `Grant` comes into existence.

        Its parameter is an `Approved`, which `verdict.mint_approval` is the
        only source of, which `admission.adjudicate` is the only caller of.
        """
        if not isinstance(approval, Approved):
            raise UnauthorizedExecution("a grant may only be minted from an approval")
        issued = time.time() if now is None else now
        expires = issued + (self._ttl_s if ttl_s is None else ttl_s)
        claims = {
            "grant_id": secrets.token_hex(8),
            "request_id": approval.request_id,
            "dataset": approval.dataset_id,
            "revision": dataset_revision,
            "capability": approval.capability,
            "scope": scope.to_dict(),
            "policy_id": approval.policy_id,
            "policy_version": approval.policy_version,
            "schema_version": schema_version,
            "issued_at": issued,
            "expires_at": expires,
        }
        return Grant(
            grant_id=claims["grant_id"],
            request_id=approval.request_id,
            dataset_id=approval.dataset_id,
            dataset_revision=dataset_revision,
            capability=approval.capability,
            scope=scope,
            policy_id=approval.policy_id,
            policy_version=approval.policy_version,
            schema_version=schema_version,
            issued_at=issued,
            expires_at=expires,
            signature=self._sign(claims),
        )

    def verify(
        self,
        grant: Optional[Grant],
        *,
        dataset_id: str,
        dataset_revision: str,
        capability: str,
        requested_scope: Optional[AuthorizationScope] = None,
        now: Optional[float] = None,
    ) -> None:
        """Raise `UnauthorizedExecution` unless this grant permits this call.

        Checked in order, because the order is the argument: does a grant
        exist, was it issued by us, has it expired, is it for this dataset at
        this revision, for this capability, and is the scope being executed
        under no wider than the scope admitted.
        """
        if grant is None:
            raise UnauthorizedExecution("no approval token: execution is unreachable")
        if not hmac.compare_digest(grant.signature, self._sign(grant.claims())):
            raise UnauthorizedExecution("approval token signature does not verify")
        moment = time.time() if now is None else now
        if moment > grant.expires_at:
            raise UnauthorizedExecution("approval token has expired")
        if grant.dataset_id != dataset_id:
            raise UnauthorizedExecution(
                f"approval token is for {grant.dataset_id}, not {dataset_id}"
            )
        if grant.dataset_revision != dataset_revision:
            raise UnauthorizedExecution(
                "approval token is for a different dataset revision"
            )
        if grant.capability != capability:
            raise UnauthorizedExecution(
                f"approval token is for {grant.capability}, not {capability}"
            )
        if requested_scope is not None and not grant.scope.covers(requested_scope):
            raise UnauthorizedExecution(
                "requested scope is wider than the scope that was admitted"
            )
