# Examples

One script per runtime. Each runs the same three requests — granted, refused,
indeterminate — and then prints what is *different* about that runtime's
wiring, which is the only thing that differs.

```bash
python examples/native_runtime.py
python examples/langgraph_runtime.py
python examples/llamaindex_runtime.py
python examples/adk_runtime.py
python examples/mcp_boundary.py
```

The point of reading them side by side: no script contains a policy decision.
Every one calls `ControlPlane.admit`, and the runtime only decides where
control goes next.
