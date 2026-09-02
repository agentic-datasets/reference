"""The control plane with no framework at all.

Read this one first. It is the whole state machine as a sequence of function
calls, and every other runtime is that sequence expressed in a framework's
primitives.
"""

from agentic_dataset.adapters import NativeRuntime
from agentic_dataset.datasets import build_control_plane

from _shared import show

runtime = NativeRuntime(build_control_plane())
show(runtime)

print("the sequence, and the one branch:")
print("  interpret -> discover -> resolve -> admit")
print("                                       |-- granted       -> cache -> plan -> execute")
print("                                       |-- refused       -> record")
print("                                       '-- indeterminate -> record")
