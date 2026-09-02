"""MCP as the dataset boundary.

A dataset exposes its descriptor, schema, lineage and policy metadata as MCP
*resources*, and its bounded capabilities as MCP *tools*. The control plane
consumes it through a real client session over an in-memory transport: a real
initialize handshake, real `list_resources` / `read_resource` / `list_tools` /
`call_tool`.

Two gates, not one. The client verifies the grant before calling, because that
is where admission happened; the server verifies it again on arrival, because
a boundary whose far side trusts its callers is not a boundary. The token is
HMAC-signed over its claims, so the second check is meaningful even though both
sides happen to be in one process here.

The point of the boundary is registration: `register_dataset` plus
`register_mcp_capabilities` is the whole integration for a new dataset. No
adapter, graph, policy rule or conformance assertion mentions a dataset by
name, so adding one touches nothing.
"""

from __future__ import annotations

import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Optional

from mcp.client import Client
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.resources import FunctionResource

from .capabilities import BoundCapability, CapabilityRegistry
from .descriptor import DatasetDescriptor, DescriptorRegistry
from .grant import Grant, GrantAuthority, UnauthorizedExecution

__all__ = ["build_dataset_server", "MCPDatasetClient", "register_mcp_capabilities"]

TOOL_SEPARATOR = "__"


def _tool_name(dataset: str, operation: str) -> str:
    return f"{dataset.replace('-', '_')}{TOOL_SEPARATOR}{operation}"


def build_dataset_server(
    descriptors: DescriptorRegistry,
    capabilities: CapabilityRegistry,
    authority: GrantAuthority,
    name: str = "agentic-dataset",
) -> MCPServer:
    server = MCPServer(name=name, version="0.1.0")

    for descriptor in descriptors.all():
        _add_resources(server, descriptor)
        for capability in descriptor.capabilities:
            bound = capabilities.get(descriptor.dataset_id, capability.name)
            if bound is None:
                continue
            _add_tool(server, descriptors, descriptor.dataset_id, bound, authority)
    return server


def _add_resources(server: MCPServer, descriptor: DatasetDescriptor) -> None:
    base = f"dataset://{descriptor.dataset_id}"
    payloads = {
        "descriptor": lambda d=descriptor: json.dumps(d.to_dict(), indent=2),
        "schema": lambda d=descriptor: json.dumps(
            {"schema_version": d.schema_version, "schemas": list(d.schemas)}, indent=2
        ),
        "lineage": lambda d=descriptor: json.dumps(
            {"revision": d.revision, "version": d.version, "provenance": dict(d.provenance)},
            indent=2,
        ),
        "policy": lambda d=descriptor: json.dumps(
            {"policies": list(d.policies), "prohibited": list(d.prohibited)}, indent=2
        ),
    }
    for suffix, fn in payloads.items():
        server.add_resource(
            FunctionResource(
                uri=f"{base}/{suffix}",
                name=f"{descriptor.dataset_id} {suffix}",
                description=f"{suffix} for {descriptor.dataset_id}",
                mime_type="application/json",
                fn=fn,
            )
        )


def _add_tool(
    server: MCPServer,
    descriptors: DescriptorRegistry,
    dataset_id: str,
    bound: BoundCapability,
    authority: GrantAuthority,
) -> None:
    def call(authorization: dict, arguments: Optional[dict] = None) -> dict:
        """Execute a bounded capability. Requires a valid approval token."""
        # The revision is read from the registry at call time, not captured
        # when the tool was built. A server that keeps serving the revision it
        # was constructed with will happily accept a grant for data it no
        # longer holds -- see docs/FINDINGS.md F-010, which the portable suite
        # found and the white-box suite did not.
        descriptor = descriptors.get(dataset_id)
        revision = descriptor.revision if descriptor else ""
        try:
            grant = Grant.from_dict(authorization)
            # The far side verifies for itself. If this line were removed, an
            # unauthenticated caller reaching the server directly would execute.
            authority.verify(
                grant,
                dataset_id=dataset_id,
                dataset_revision=revision,
                capability=bound.operation,
                requested_scope=grant.scope,
            )
        except (UnauthorizedExecution, KeyError, TypeError) as exc:
            # A refusal is an answer, not a transport failure. Returning it as
            # a value keeps the reason legible on the caller's side; raising
            # would reach the client as "error executing tool", and a control
            # plane cannot record what it cannot read.
            return {"refused": True, "reason": str(exc) or type(exc).__name__}
        return bound(
            authorization=grant,
            authority=authority,
            dataset_revision=revision,
            requested_scope=grant.scope,
            **(arguments or {}),
        )

    call.__name__ = _tool_name(dataset_id, bound.operation)
    server.add_tool(
        call,
        name=call.__name__,
        description=(
            f"{bound.operation} on {dataset_id} "
            f"(effect={bound.effect}, sensitivity={bound.sensitivity}, policy={bound.policy})"
        ),
    )


class MCPDatasetClient:
    """The control-plane side of the boundary.

    Synchronous by design: the control plane is synchronous, and hiding an
    event loop behind each capability call would put an await in the middle of
    the admission path for no benefit.
    """

    def __init__(self, server: MCPServer) -> None:
        self._server = server

    def _call(self, coro_fn) -> Any:
        async def run() -> Any:
            async with Client(self._server) as client:
                return await coro_fn(client)

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(run())
        # Two of the four runtimes drive their own event loop -- LlamaIndex
        # Workflows and ADK are async -- so a synchronous client called from
        # inside a capability is already on a loop. Own the loop on a worker
        # thread rather than making the whole control plane async: admission is
        # not an I/O-bound problem, and colouring it async to accommodate one
        # transport would push await into every policy call site.
        with ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, run()).result()

    def list_resources(self) -> list[str]:
        result = self._call(lambda c: c.list_resources())
        return [str(r.uri) for r in result.resources]

    def list_tools(self) -> list[str]:
        result = self._call(lambda c: c.list_tools())
        return [t.name for t in result.tools]

    def read_descriptor(self, dataset_id: str) -> DatasetDescriptor:
        result = self._call(
            lambda c: c.read_resource(f"dataset://{dataset_id}/descriptor")
        )
        raw = json.loads(result.contents[0].text)
        return DatasetDescriptor.from_dict(raw)

    def descriptors(self) -> DescriptorRegistry:
        """Build a registry from what the server advertises.

        This is the discoverability claim in M3: the control plane learns what
        a dataset is and what it can do from the boundary, not from a constant
        compiled into itself.
        """
        ids = sorted(
            {
                uri.split("//", 1)[1].split("/", 1)[0]
                for uri in self.list_resources()
                if uri.startswith("dataset://") and uri.endswith("/descriptor")
            }
        )
        return DescriptorRegistry([self.read_descriptor(i) for i in ids])

    def call(self, dataset_id: str, operation: str, grant: Grant, arguments: dict) -> Any:
        name = _tool_name(dataset_id, operation)

        async def invoke(client: Client) -> Any:
            return await client.call_tool(
                name, {"authorization": grant.to_dict(), "arguments": arguments}
            )

        result = self._call(invoke)
        if getattr(result, "is_error", False):
            text = result.content[0].text if result.content else "remote error"
            raise UnauthorizedExecution(f"remote capability failed: {text}")
        payload = getattr(result, "structured_content", None)
        if payload is None and result.content:
            payload = json.loads(result.content[0].text)
        if isinstance(payload, dict):
            payload = payload.get("result", payload)
        if isinstance(payload, dict) and payload.get("refused"):
            raise UnauthorizedExecution(
                f"remote capability refused: {payload.get('reason')}"
            )
        return payload


def register_mcp_capabilities(
    client: MCPDatasetClient,
    descriptors: DescriptorRegistry,
    registry: CapabilityRegistry,
) -> int:
    """Register every remote capability as a locally guarded capability.

    The returned object is a `BoundCapability` like any other, so admission,
    the grant check, scope preservation and the execution log all apply
    unchanged. Being remote is a property of the body, not of the gate.
    """
    added = 0
    for descriptor in descriptors.all():
        for capability in descriptor.capabilities:
            def body(
                _authorization: Optional[Grant] = None,
                _dataset: str = descriptor.dataset_id,
                _operation: str = capability.name,
                **arguments: Any,
            ) -> Any:
                if _authorization is None:
                    raise UnauthorizedExecution("no approval token to forward")
                return client.call(_dataset, _operation, _authorization, arguments)

            registry.register(
                BoundCapability(
                    body,
                    dataset=descriptor.dataset_id,
                    operation=capability.name,
                    effect=capability.effect,
                    sensitivity=capability.sensitivity,
                    policy=capability.required_policy,
                    forward_authorization=True,
                )
            )
            added += 1
    return added
