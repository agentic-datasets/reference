"""Which implementations to test, and how to build them.

This file lives outside `agentic_dataset.conformance` so that the harness has
no import of any implementation -- including the reference one. Adding a
subject is editing this list; nothing in the package changes.

A foreign implementation registers itself here the same way: import it, return
something that satisfies `ConformanceSubject`.
"""

from __future__ import annotations

from typing import Any


def subjects() -> list[Any]:
    found: list[Any] = []

    # The reference implementation, on every runtime and both dataset
    # boundaries. Optional: the harness runs without it.
    try:
        from agentic_dataset.adapters import available
        from agentic_dataset.adapters.conformance_subject import ReferenceSubject
        from agentic_dataset.datasets import build_control_plane, build_mcp_control_plane

        for boundary, factory in (("local", build_control_plane),
                                  ("mcp", build_mcp_control_plane)):
            for name, cls in available().items():
                found.append(ReferenceSubject(cls, factory, f"{name}+{boundary}"))
    except Exception:
        pass

    # An implementation that shares nothing with the one above.
    try:
        from toy_implementation import ToyImplementation

        found.append(ToyImplementation())
    except Exception:
        pass

    return found
