"""Framework ports.

Every adapter satisfies `runtime.Runtime` and returns the same `RunResult`.
`available()` reports which ones this environment can actually run, so the
conformance suite reports skipped runtimes rather than silently testing fewer.
"""

from __future__ import annotations

import importlib
from typing import Callable

from .native import NativeRuntime

__all__ = ["NativeRuntime", "available", "ADAPTERS"]

# name -> (module, class, import that must succeed)
ADAPTERS: dict[str, tuple[str, str, str]] = {
    "native": (".native", "NativeRuntime", ""),
    "langgraph": (".langgraph_port", "LangGraphRuntime", "langgraph.graph"),
    "llamaindex": (".llamaindex_port", "LlamaIndexRuntime", "llama_index.core.workflow"),
    "adk": (".adk_port", "ADKRuntime", "google.adk.agents"),
}


def available() -> dict[str, Callable]:
    """Adapter classes whose framework is importable here."""
    found: dict[str, Callable] = {}
    for name, (module, cls, requires) in ADAPTERS.items():
        if requires:
            try:
                importlib.import_module(requires)
            except Exception:
                continue
        try:
            found[name] = getattr(importlib.import_module(module, __name__), cls)
        except Exception:
            continue
    return found
