"""LlamaIndex Workflows: admission routes by event *type*.

The admit step returns a Granted, Refused or Indeterminate event, and the step
that can execute accepts only Granted. There is no handler that takes a Refused
and reaches a capability, so refusal is a dispatch fact.
"""

import inspect
import typing

from agentic_dataset.adapters.llamaindex_port import DatasetWorkflow, LlamaIndexRuntime
from agentic_dataset.datasets import build_control_plane

from _shared import show

runtime = LlamaIndexRuntime(build_control_plane())
show(runtime)

print("steps, by the event each accepts:")
for name in ("interpret", "discover", "resolve", "admit", "execute",
             "record_executed", "record_refused", "record_indeterminate", "finish"):
    fn = getattr(DatasetWorkflow, name)
    hints = typing.get_type_hints(fn)
    accepts = next((v for k, v in hints.items() if k not in ("return", "self")), None)
    returns = hints.get("return")
    fmt = lambda t: getattr(t, "__name__", str(t).replace("typing.", ""))  # noqa: E731
    print(f"  {name:<22} {fmt(accepts):<14} -> {fmt(returns)}")
