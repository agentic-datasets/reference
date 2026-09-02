"""LangGraph: admission is a routed edge, not a prompt.

`add_conditional_edges("admit", ...)` makes the three-valued verdict a property
of the topology, so "the model talked its way past the gate" would require the
graph to have a different shape.
"""

from agentic_dataset.adapters.langgraph_port import LangGraphRuntime
from agentic_dataset.datasets import build_control_plane

from _shared import show

runtime = LangGraphRuntime(build_control_plane())
show(runtime)

graph = runtime.graph.get_graph()
print("nodes:", ", ".join(n for n in graph.nodes if n not in ("__start__", "__end__")))
print("\nthe only branch in the system, as the graph was wired:")
for arm, target in {
    "granted": "cache", "refused": "refuse", "indeterminate": "indeterminate"
}.items():
    print(f"  admit --[{arm}]--> {target}")
print("\n`refuse` and `indeterminate` reach `record` without passing through")
print("`plan` or `execute`, so a refused run has no path to a capability --")
print("not a discouraged one, none.")
