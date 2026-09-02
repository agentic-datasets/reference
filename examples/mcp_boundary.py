"""The dataset behind MCP: resources, tools, and a run across the boundary.

Both sides verify the grant. The client checks it because that is where
admission happened; the server checks it again on arrival, because a boundary
whose far side trusts its callers is not a boundary.
"""

from agentic_dataset.adapters import NativeRuntime
from agentic_dataset.datasets import (
    build_mcp_control_plane,
    capability_registry,
    descriptor_registry,
)
from agentic_dataset.grant import GrantAuthority
from agentic_dataset.mcp_boundary import MCPDatasetClient, build_dataset_server

from _shared import show

authority = GrantAuthority(secret=b"example")
client = MCPDatasetClient(
    build_dataset_server(descriptor_registry(), capability_registry(), authority)
)

print("resources the dataset advertises:")
for uri in client.list_resources()[:4]:
    print(f"  {uri}")
print(f"  ... {len(client.list_resources())} in total\n")

print("capabilities exposed as tools:")
for tool in client.list_tools():
    print(f"  {tool}")
print("\nprohibited operations are absent from the tool surface entirely,")
print("as well as being refused by policy.\n")

show(NativeRuntime(build_mcp_control_plane()))
