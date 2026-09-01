"""The two seams where authority is most often lost.

AD-013 (MCP or A2A delegation) and AD-014 (sub-agent handoff) are the same
assertion at two places: a delegate may execute under the caller's scope or a
narrowing of it, and never under a wider one. Both are enforced here rather
than in the adapters, because a boundary check that each runtime implements for
itself is a boundary check with four chances to be wrong.

The check is `parent.covers(child)` *and* the grant's own scope check inside
`GrantAuthority.verify`. Two independent gates, because the failure being
guarded against is precisely that one of them is forgotten at a seam.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from .capabilities import CapabilityRegistry, ExecutionLog
from .grant import Grant, GrantAuthority, UnauthorizedExecution
from .principal import AuthorizationScope

__all__ = ["Delegation", "DelegatedExecutor"]

CHANNELS = ("mcp", "a2a")


@dataclass(frozen=True)
class Delegation:
    channel: str
    target: str
    scope: AuthorizationScope


class DelegatedExecutor:
    """Execution across a boundary: an MCP server, or another agent.

    The boundary is real in the sense that matters for the assertion -- the
    caller hands over a scope and a grant and gets back a result -- and
    simulated in the sense that it is an in-process call. `mcp_server.py` puts
    the same registry behind an actual MCP session; this is what both sides of
    that session go through.
    """

    def __init__(
        self, channel: str, registry: CapabilityRegistry, authority: GrantAuthority
    ) -> None:
        if channel not in CHANNELS:
            raise ValueError(f"channel must be one of {CHANNELS}")
        self.channel = channel
        self.registry = registry
        self.authority = authority

    def invoke(
        self,
        *,
        target: str,
        dataset: str,
        operation: str,
        grant: Optional[Grant],
        parent_scope: Optional[AuthorizationScope],
        requested_scope: Optional[AuthorizationScope],
        dataset_revision: str,
        arguments: Optional[dict] = None,
        log: Optional[ExecutionLog] = None,
    ) -> Any:
        channel_log = None
        if log is not None:
            channel_log = log.mcp_calls if self.channel == "mcp" else log.a2a_calls

        if parent_scope is None or requested_scope is None:
            self._deny(log, target, operation)
            raise UnauthorizedExecution(
                f"{self.channel} delegation without a scope on both sides"
            )
        if not parent_scope.covers(requested_scope):
            # The escalation path this assertion exists to close: a delegate
            # asking for authority the caller never had, on the theory that
            # the far side will not check.
            self._deny(log, target, operation)
            raise UnauthorizedExecution(
                f"{self.channel} delegation to {target} widens the authorization scope"
            )
        try:
            result = self.registry.invoke(
                dataset=dataset,
                operation=operation,
                grant=grant,
                authority=self.authority,
                dataset_revision=dataset_revision,
                requested_scope=requested_scope,
                arguments=arguments,
                log=log,
            )
        except UnauthorizedExecution:
            self._deny(log, target, operation)
            raise
        if channel_log is not None:
            channel_log.append(f"{target}:{dataset}.{operation}")
        return result

    def _deny(self, log: Optional[ExecutionLog], target: str, operation: str) -> None:
        if log is not None:
            log.denied.append(f"{self.channel}:{target}.{operation}")
