from __future__ import annotations

import pytest

from agentic_dataset.adapters import ADAPTERS, available
from agentic_dataset.datasets import build_control_plane, build_mcp_control_plane

RUNTIMES = available()
BOUNDARIES = {"local": build_control_plane, "mcp": build_mcp_control_plane}


def pytest_report_header(config):
    missing = sorted(set(ADAPTERS) - set(RUNTIMES))
    line = f"runtimes: {', '.join(sorted(RUNTIMES))}"
    return line + (f" | not installed: {', '.join(missing)}" if missing else "")


@pytest.fixture(params=sorted(RUNTIMES), ids=sorted(RUNTIMES))
def runtime_cls(request):
    return RUNTIMES[request.param]


@pytest.fixture(params=sorted(BOUNDARIES), ids=sorted(BOUNDARIES))
def plane_factory(request):
    return BOUNDARIES[request.param]


@pytest.fixture
def plane():
    return build_control_plane()


@pytest.fixture
def native(plane):
    from agentic_dataset.adapters import NativeRuntime

    return NativeRuntime(plane)
