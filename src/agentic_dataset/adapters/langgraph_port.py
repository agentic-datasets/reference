"""LangGraph port.

Admission is a routed edge, not a prompt. That is the only reason to reach for
a graph runtime here: `add_conditional_edges("admit", route, {...})` makes the
three-valued verdict a property of the topology, so "the model talked its way
past the gate" would require the graph to have a different shape.

Every node delegates to `ControlPlane`. If this file contained a policy
decision the experiment would be circular.
"""

from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from ..runtime import ControlPlane, Request, RunResult, RunState

__all__ = ["LangGraphRuntime", "build_graph"]


class GraphState(TypedDict):
    """The graph's state is a handle to the control plane's state.

    Deliberately thin. Mirroring `RunState`'s fields into a graph schema would
    create a second definition of what a run is, and the two would drift.
    """

    run: Any


def build_graph(plane: ControlPlane):
    graph = StateGraph(GraphState)

    def node(fn):
        def wrapped(state: GraphState) -> GraphState:
            return {"run": fn(state["run"])}

        return wrapped

    def terminal(name: str):
        def wrapped(state: GraphState) -> GraphState:
            run: RunState = state["run"]
            run.path.append(name)
            return {"run": run}

        return wrapped

    def cache_or_execute(state: GraphState) -> str:
        return "hit" if state["run"].cache_used else "miss"

    graph.add_node("interpret", node(plane.interpret))
    graph.add_node("discover", node(plane.discover))
    graph.add_node("resolve", node(plane.resolve))
    graph.add_node("admit", node(plane.admit))
    graph.add_node("cache", node(plane.lookup_cache))
    graph.add_node("plan", node(plane.plan))
    graph.add_node("execute", node(plane.execute))
    graph.add_node("validate", node(plane.validate))
    graph.add_node("store", node(plane.store_cache))
    graph.add_node("record", node(plane.record))
    graph.add_node("refuse", terminal("refused"))
    graph.add_node("indeterminate", terminal("indeterminate"))

    graph.add_edge(START, "interpret")
    graph.add_edge("interpret", "discover")
    graph.add_edge("discover", "resolve")
    graph.add_edge("resolve", "admit")

    # The one branch. `refuse` and `indeterminate` reach `record` without
    # passing through `plan` or `execute`, so a refused run has no path to a
    # capability -- not a discouraged one, none.
    graph.add_conditional_edges(
        "admit",
        lambda state: plane.route(state["run"]),
        {"granted": "cache", "refused": "refuse", "indeterminate": "indeterminate"},
    )
    graph.add_conditional_edges(
        "cache", cache_or_execute, {"hit": "validate", "miss": "plan"}
    )
    graph.add_edge("plan", "execute")
    graph.add_edge("execute", "validate")
    graph.add_edge("validate", "store")
    graph.add_edge("store", "record")
    graph.add_edge("refuse", "record")
    graph.add_edge("indeterminate", "record")
    graph.add_edge("record", END)
    return graph.compile()


class LangGraphRuntime:
    name = "langgraph"

    def __init__(self, plane: ControlPlane) -> None:
        self.plane = plane
        self.graph = build_graph(plane)

    def run(self, request: Request) -> RunResult:
        state = self.plane.begin(request)
        final = self.graph.invoke({"run": state})
        return self.plane.finish(final["run"], runtime=self.name)
