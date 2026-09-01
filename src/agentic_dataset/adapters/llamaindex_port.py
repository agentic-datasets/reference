"""LlamaIndex Workflows port.

Where LangGraph routes on a conditional edge, a Workflow routes by *type*: the
admission step returns a `Granted`, `Refused` or `Indeterminate` event, and the
steps that can execute accept only `Granted`. The three-valued verdict becomes
a fact about which handler can be dispatched to.

That difference is exactly what the conformance suite is for. Two runtimes
express the same invariant with different primitives; if AD-003 passes in both,
the invariant is not a feature of either primitive.
"""

from __future__ import annotations

import asyncio
from typing import Any

from llama_index.core.workflow import (
    Context,
    Event,
    StartEvent,
    StopEvent,
    Workflow,
    step,
)

from ..runtime import ControlPlane, Request, RunResult, RunState

__all__ = ["LlamaIndexRuntime", "DatasetWorkflow"]


class _RunEvent(Event):
    """Carries the control plane's state between steps.

    `arbitrary_types_allowed` because `RunState` is a plain dataclass and the
    alternative -- restating it as a pydantic model -- would be a second
    definition of what a run is.
    """

    model_config = {"arbitrary_types_allowed": True}
    run: Any


class Interpreted(_RunEvent): ...
class Discovered(_RunEvent): ...
class Resolved(_RunEvent): ...
class Granted(_RunEvent): ...
class Refused(_RunEvent): ...
class Indeterminate(_RunEvent): ...
class Executed(_RunEvent): ...
class Recorded(_RunEvent): ...


class DatasetWorkflow(Workflow):
    def __init__(self, plane: ControlPlane, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.plane = plane

    @step
    async def interpret(self, ev: StartEvent) -> Interpreted:
        state: RunState = ev.state
        return Interpreted(run=self.plane.interpret(state))

    @step
    async def discover(self, ev: Interpreted) -> Discovered:
        return Discovered(run=self.plane.discover(ev.run))

    @step
    async def resolve(self, ev: Discovered) -> Resolved:
        return Resolved(run=self.plane.resolve(ev.run))

    @step
    async def admit(self, ev: Resolved) -> Granted | Refused | Indeterminate:
        state = self.plane.admit(ev.run)
        arm = self.plane.route(state)
        if arm == "granted":
            return Granted(run=state)
        state.path.append(arm)
        return Refused(run=state) if arm == "refused" else Indeterminate(run=state)

    @step
    async def execute(self, ev: Granted) -> Executed:
        """Accepts `Granted` and nothing else.

        A `Refused` event cannot be dispatched here: there is no handler that
        takes one and reaches a capability. Refusal is a routing fact.
        """
        plane, state = self.plane, ev.run
        plane.lookup_cache(state)
        if not state.cache_used:
            plane.plan(state)
            plane.execute(state)
        plane.validate(state)
        plane.store_cache(state)
        return Executed(run=state)

    @step
    async def record_executed(self, ev: Executed) -> Recorded:
        return Recorded(run=self.plane.record(ev.run))

    @step
    async def record_refused(self, ev: Refused) -> Recorded:
        return Recorded(run=self.plane.record(ev.run))

    @step
    async def record_indeterminate(self, ev: Indeterminate) -> Recorded:
        return Recorded(run=self.plane.record(ev.run))

    @step
    async def finish(self, ev: Recorded) -> StopEvent:
        return StopEvent(result=ev.run)


class LlamaIndexRuntime:
    name = "llamaindex"

    def __init__(self, plane: ControlPlane, timeout: float = 60.0) -> None:
        self.plane = plane
        self.workflow = DatasetWorkflow(plane, timeout=timeout, disable_validation=False)

    def run(self, request: Request) -> RunResult:
        state = self.plane.begin(request)
        final = asyncio.run(self._run(state))
        return self.plane.finish(final, runtime=self.name)

    async def _run(self, state: RunState) -> RunState:
        result = await self.workflow.run(state=state)
        return result if isinstance(result, RunState) else state
