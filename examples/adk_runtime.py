"""Google ADK: a SequentialAgent, real FunctionTools, and a before-tool guard.

No LlmAgent is instantiated -- the suite has to run without an API key and
without variance, and the guard runs before the tool either way. See
docs/FINDINGS.md F-002 for what that does and does not establish.
"""

from agentic_dataset.adapters.adk_port import ADKRuntime
from agentic_dataset.datasets import build_control_plane
from agentic_dataset.runtime import Request

from _shared import show, transcripts

plane = build_control_plane()
runtime = ADKRuntime(plane)
show(runtime)

state = plane.begin(transcripts()["granted"])
agent = runtime._agent(state)
print(f"agent tree: {agent.name}")
for sub in agent.sub_agents:
    print(f"  |-- {sub.name} ({type(sub).__name__})")
print(f"\ncapabilities wrapped as ADK FunctionTools: {len(runtime._tools(state))}")
print("the guard has ADK's before_tool_callback signature and returns a refusal")
print("payload, which is how ADK short-circuits a tool call.")
