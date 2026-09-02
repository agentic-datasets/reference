"""Which implementations to test, and how to build them.

The harness is a separate distribution and imports no implementation. This file
is how *this* repository registers its own subjects with it; a foreign
implementation does the same thing from its own package, or passes
`--subject module:attribute` on the command line and writes no file at all.
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

    # An implementation that shares nothing with the one above, shipped with the
    # conformance distribution rather than with this repository.
    try:
        from agentic_dataset_conformance.toy import ToyImplementation

        found.append(ToyImplementation())
    except Exception:
        pass

    return found
