"""Milestone M3: the dataset behind MCP, and what the boundary is worth.

The claim being tested is not "MCP works". It is that registering a second
dataset is the whole integration -- no adapter, graph, policy rule or
conformance assertion changes -- and that the boundary is not an escalation
path.
"""

from __future__ import annotations

import pytest

from agentic_dataset.adapters import NativeRuntime
from agentic_dataset.datasets import (
    build_mcp_control_plane,
    capability_registry,
    descriptor_registry,
    principals,
)
from agentic_dataset.descriptor import DatasetCapability, DatasetDescriptor
from agentic_dataset.grant import GrantAuthority, UnauthorizedExecution
from agentic_dataset.mcp_boundary import (
    MCPDatasetClient,
    build_dataset_server,
    register_mcp_capabilities,
)
from agentic_dataset.runtime import Request

QUESTION = "Compare the recovery of batches B001 and B002"


@pytest.fixture(scope="module")
def client() -> MCPDatasetClient:
    authority = GrantAuthority(secret=b"test")
    server = build_dataset_server(descriptor_registry(), capability_registry(), authority)
    return MCPDatasetClient(server)


def test_the_dataset_exposes_its_contract_as_resources(client):
    resources = client.list_resources()
    for suffix in ("descriptor", "schema", "lineage", "policy"):
        assert f"dataset://purification-batches/{suffix}" in resources


def test_capabilities_are_exposed_as_tools(client):
    tools = client.list_tools()
    assert "purification_batches__compare_batches" in tools
    assert "purification_batches__delete_source" not in tools


def test_prohibited_operations_are_not_on_the_tool_surface(client):
    """A prohibited operation is refused by policy *and* absent from the
    boundary. Defence in depth is cheap here and the alternative is a tool
    whose only protection is a rule somewhere else."""
    tools = client.list_tools()
    assert not any("delete_source" in t or "bypass_governance" in t for t in tools)


def test_the_descriptor_survives_the_round_trip(client):
    remote = client.read_descriptor("purification-batches")
    local = descriptor_registry().get("purification-batches")
    assert remote.to_dict() == local.to_dict()


def test_the_control_plane_learns_the_datasets_from_the_boundary(client):
    registry = client.descriptors()
    assert {d.dataset_id for d in registry.all()} == {
        "purification-batches", "chromatography-results", "clinical-private"
    }


def test_a_run_over_mcp_produces_the_same_answer_as_a_local_one():
    plane = build_mcp_control_plane()
    result = NativeRuntime(plane).run(
        Request(text=QUESTION, principal=principals()["process_engineer"])
    )
    assert result.decision == "GRANTED"
    assert result.result["delta_recovery"] == 0.178


def test_the_far_side_verifies_the_grant_for_itself(client):
    """A boundary whose far side trusts its callers is not a boundary."""
    with pytest.raises(UnauthorizedExecution):
        client.call("purification-batches", "compare_batches", _forged_grant(), {})


def _forged_grant():
    from agentic_dataset.grant import Grant
    from agentic_dataset.principal import AuthorizationScope
    from agentic_dataset.verdict import mint_approval

    other = GrantAuthority(secret=b"not-the-servers-key")
    approval = mint_approval(
        request_id="r", dataset_id="purification-batches",
        capability="compare_batches", policy_id="BPD-DATA-014",
        policy_version="v", trace="t",
    )
    return other.mint(
        approval,
        dataset_revision="s3-etag-4c1f9a",
        schema_version="3",
        scope=AuthorizationScope(
            "process-engineer", "purification-batches",
            frozenset({"compare_batches"}), "internal",
        ),
    )


def test_a_second_dataset_is_registered_without_touching_the_graph():
    """The point of the boundary, stated as a test.

    Nothing below mentions a graph, an adapter, a policy rule or a conformance
    assertion. Registration is the whole integration.
    """
    plane = build_mcp_control_plane()
    runtime = NativeRuntime(plane)

    authority = plane.authority
    new_descriptor = DatasetDescriptor(
        dataset_id="stability-studies",
        version="2026.09.01",
        revision="rev-stab-01",
        schema_version="1",
        description="Stability study results: potency over time at storage conditions.",
        capabilities=(
            DatasetCapability("search", "find stability studies", "read", "internal"),
        ),
        prohibited=("delete_source",),
    )
    registry = capability_registry()

    @registry.capability(dataset="stability-studies", operation="search")
    def search(query: str = "", **_: object) -> dict:
        return {"studies": ["ST-01"], "query": query}

    from agentic_dataset.descriptor import DescriptorRegistry

    server = build_dataset_server(
        DescriptorRegistry([new_descriptor]), registry, authority
    )
    new_client = MCPDatasetClient(server)
    plane.register_dataset(new_client.read_descriptor("stability-studies"))
    register_mcp_capabilities(
        new_client, DescriptorRegistry([new_descriptor]), plane.capabilities
    )

    who = principals()["process_engineer"]
    entitled = type(who)(
        principal_id=who.principal_id,
        principal_class=who.principal_class,
        grants={**who.grants, "stability-studies": frozenset({"search"})},
        clearance=who.clearance,
    )
    result = runtime.run(
        Request(text="search stability studies for potency over time", principal=entitled)
    )
    assert result.dataset == "stability-studies"
    assert result.decision == "GRANTED"
    assert result.result["studies"] == ["ST-01"]

    refused = runtime.run(
        Request(text="delete", principal=entitled,
                dataset="stability-studies", capability="delete_source")
    )
    assert refused.decision == "REFUSED"
    assert refused.reason == "PROHIBITED_OPERATION"
