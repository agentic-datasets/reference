"""The reference runtime: the control plane called in order, by nothing.

This adapter has no dependency and no framework. It exists so that every
framework port has something to be compared against that cannot be accused of
having inherited the property under test from its runtime.
"""

from __future__ import annotations

from ..runtime import ControlPlane, Request, RunResult

__all__ = ["NativeRuntime"]


class NativeRuntime:
    name = "native"

    def __init__(self, plane: ControlPlane) -> None:
        self.plane = plane

    def run(self, request: Request) -> RunResult:
        plane = self.plane
        state = plane.begin(request)
        plane.interpret(state)
        plane.discover(state)
        plane.resolve(state)
        plane.admit(state)

        arm = plane.route(state)
        if arm == "granted":
            plane.lookup_cache(state)
            if not state.cache_used:
                plane.plan(state)
                plane.execute(state)
            plane.validate(state)
            plane.store_cache(state)
        else:
            # Both non-granted arms are terminal in the same way: no plan, no
            # execution, no token. They differ only in what gets recorded.
            state.path.append(arm)
        plane.record(state)
        return plane.finish(state, runtime=self.name)
