"""Google ADK port.

Three agents composed by a `SequentialAgent`, run through a real `Runner`, with
capabilities wrapped as real `FunctionTool`s and a guard with ADK's
`before_tool_callback` signature invoked at the point ADK would invoke it.

**One deliberate departure, stated rather than hidden.** No `LlmAgent` is
instantiated, so no model selects the tool. The conformance suite must run
without an API key and without variance, and an `LlmAgent` here would add a
model to the loop without adding anything to what is being tested -- the guard
runs before the tool either way, which is the assertion. What this port
demonstrates is that ADK's agent, tool and callback primitives can express the
control plane; it does not demonstrate anything about ADK's model integration,
and `docs/FINDINGS.md` F-002 records that as a limit of the result.
"""

from __future__ import annotations

import asyncio
from typing import Any, AsyncGenerator, Optional

from google.adk.agents import BaseAgent, SequentialAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.adk.runners import InMemoryRunner
from google.adk.tools import BaseTool, FunctionTool, ToolContext
from google.genai import types

from ..grant import UnauthorizedExecution
from ..runtime import ControlPlane, Request, RunResult, RunState

__all__ = ["ADKRuntime", "admission_before_tool_callback"]

STATE_KEY = "agentic_dataset_request"

# The run state is held on the agents rather than in `session.state`. ADK's
# session service copies what it stores, so a `RunState` put there would be a
# snapshot: the agents would mutate one object and the tools another, and the
# first symptom is a granted run whose executor cannot see the descriptor.
# The session carries the request and trace identifiers, which is what a
# session is for.


def _empty_event(ctx: InvocationContext, author: str, text: str) -> Event:
    return Event(
        invocation_id=ctx.invocation_id,
        author=author,
        content=types.Content(role="model", parts=[types.Part(text=text)]),
    )


def admission_before_tool_callback(
    *, tool: BaseTool, args: dict[str, Any], tool_context: ToolContext, state: RunState
) -> Optional[dict]:
    """ADK's `before_tool_callback` shape: return a dict to short-circuit the tool.

    This is where AD-006 lives in the ADK port. A tool whose name is not the
    admitted capability, or a run with no grant, never reaches `run_async` --
    the callback returns the refusal payload and ADK skips the call.
    """
    if state.verdict is None or state.verdict.approved() is None:
        state.execution.denied.append(tool.name)
        return {"refused": True, "reason": "no approval token"}
    if state.capability_name is None or tool.name != state.capability_name:
        state.execution.denied.append(tool.name)
        return {"refused": True, "reason": "tool is not the admitted capability"}
    return None


class AdmissionAgent(BaseAgent):
    """interpret -> discover -> resolve -> admit. Emits the verdict as an event."""

    plane: Any = None
    state: Any = None

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        state = self.state
        self.plane.interpret(state)
        self.plane.discover(state)
        self.plane.resolve(state)
        self.plane.admit(state)
        assert state.verdict is not None
        yield _empty_event(ctx, self.name, state.verdict.kind)


class ExecutionAgent(BaseAgent):
    """Runs the admitted capability as an ADK `FunctionTool`, or nothing at all."""

    plane: Any = None
    state: Any = None
    tools: dict = {}

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        plane, state = self.plane, self.state
        arm = plane.route(state)
        if arm != "granted":
            state.path.append(arm)
            yield _empty_event(ctx, self.name, f"no execution: {arm}")
            return

        plane.lookup_cache(state)
        if not state.cache_used:
            plane.plan(state)
            for step_spec in state.plan:
                key = (step_spec["dataset"], step_spec["capability"])
                tool = self.tools.get(key)
                if tool is None:
                    state.execution.denied.append(f"{key[0]}.{key[1]}")
                    state.errors.append(f"{key[0]}.{key[1]} is not a registered capability")
                    continue
                tool_context = ToolContext(invocation_context=ctx)
                short_circuit = admission_before_tool_callback(
                    tool=tool, args=step_spec["arguments"], tool_context=tool_context,
                    state=state,
                )
                if short_circuit is not None:
                    state.errors.append(str(short_circuit["reason"]))
                    continue
                try:
                    state.result = await tool.run_async(
                        args=dict(step_spec["arguments"]), tool_context=tool_context
                    )
                except UnauthorizedExecution as exc:
                    state.errors.append(str(exc))
        plane.validate(state)
        plane.store_cache(state)
        yield _empty_event(ctx, self.name, "executed" if state.result is not None else "no result")


class RecordAgent(BaseAgent):
    plane: Any = None
    state: Any = None

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        state = self.state
        self.plane.record(state)
        yield _empty_event(ctx, self.name, "recorded")


class ADKRuntime:
    name = "adk"

    def __init__(self, plane: ControlPlane, app_name: str = "agentic-dataset") -> None:
        self.plane = plane
        self.app_name = app_name

    def _tools(self, state: RunState) -> dict:
        """Wrap each registered capability as a `FunctionTool`.

        The wrapper closes over the grant and the authority, so the tool ADK
        holds is still the guarded capability -- the raw function is no more
        reachable from an ADK tool call than from any other caller.
        """
        tools: dict = {}
        plane = self.plane
        for bound in plane.capabilities.all():
            def make(bound=bound):
                async def call(**arguments: Any) -> Any:
                    assert state.descriptor is not None
                    return plane.capabilities.invoke(
                        dataset=bound.dataset,
                        operation=bound.operation,
                        grant=state.grant,
                        authority=plane.authority,
                        dataset_revision=state.descriptor.revision,
                        requested_scope=state.scope,
                        arguments=arguments,
                        log=state.execution,
                    )

                call.__name__ = bound.operation
                call.__doc__ = bound.__doc__ or bound.operation
                return FunctionTool(call)

            tools[(bound.dataset, bound.operation)] = make()
        return tools

    def _agent(self, state: RunState) -> SequentialAgent:
        return SequentialAgent(
            name="agentic_dataset_control_plane",
            sub_agents=[
                AdmissionAgent(name="admission", plane=self.plane, state=state),
                ExecutionAgent(
                    name="execution", plane=self.plane, state=state,
                    tools=self._tools(state),
                ),
                RecordAgent(name="record", plane=self.plane, state=state),
            ],
        )

    def run(self, request: Request) -> RunResult:
        state = self.plane.begin(request)
        asyncio.run(self._run(state, request))
        return self.plane.finish(state, runtime=self.name)

    async def _run(self, state: RunState, request: Request) -> None:
        runner = InMemoryRunner(agent=self._agent(state), app_name=self.app_name)
        session = await runner.session_service.create_session(
            app_name=self.app_name,
            user_id=request.principal.principal_id,
            state={STATE_KEY: {"request_id": request.request_id, "trace_id": state.trace_id}},
        )
        message = types.Content(role="user", parts=[types.Part(text=request.text)])
        async for _event in runner.run_async(
            user_id=request.principal.principal_id,
            session_id=session.id,
            new_message=message,
        ):
            pass
