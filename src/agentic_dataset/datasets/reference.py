"""One synthetic dataset family, and the principals that exercise it.

Synthetic on purpose. The interesting behaviour is entirely in the control
plane, and real process data would add nothing to it while making the artifact
un-runnable by anyone who does not have that data. What matters is that the
descriptors carry real prohibitions and real sensitivity levels, so the
refusals are refusals of something.

Every capability body here is trivial. That is also on purpose: if a
conformance run passes, it is because the gate held, not because the payload
was clever.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from ..cache import SemanticCache
from ..capabilities import BoundCapability, CapabilityRegistry
from ..descriptor import DescriptorRegistry
from ..grant import GrantAuthority
from ..intent import Interpreter
from ..ledger import EvidenceLedger
from ..principal import Principal
from ..runtime import ControlPlane

DESCRIPTORS_JSON = Path(__file__).with_name("descriptors.json")

# Deterministic stand-in data. Two batches that differ, so `compare_batches`
# has something to say and the quality contract has something to check.
_BATCHES = {
    "B001": {"recovery": 0.912, "step_yield": 0.964, "column": "CEX-1", "load_g_l": 41.0},
    "B002": {"recovery": 0.734, "step_yield": 0.812, "column": "CEX-1", "load_g_l": 58.5},
    "B003": {"recovery": 0.889, "step_yield": 0.951, "column": "CEX-2", "load_g_l": 39.2},
}


def descriptor_registry() -> DescriptorRegistry:
    return DescriptorRegistry.from_json_file(DESCRIPTORS_JSON)


def capability_registry() -> CapabilityRegistry:
    """A fresh registry per call, so tests never share mutable state."""
    registry = CapabilityRegistry()

    @registry.capability(
        dataset="purification-batches", operation="search", effect="read",
        sensitivity="internal",
    )
    def search(query: str = "", **_: object) -> dict:
        hits = [b for b, row in _BATCHES.items() if query.lower() in f"{b} {row['column']}".lower()]
        return {"batch_ids": hits or sorted(_BATCHES), "recovery": None, "query": query}

    @registry.capability(
        dataset="purification-batches", operation="compare_batches", effect="read",
        sensitivity="internal", policy="BPD-DATA-014",
    )
    def compare_batches(batch_ids: Optional[list[str]] = None, **_: object) -> dict:
        ids = list(batch_ids or [])[:2] or ["B001", "B002"]
        rows = {b: _BATCHES.get(b, {}) for b in ids}
        return {
            "batch_ids": ids,
            "recovery": {b: rows[b].get("recovery") for b in ids},
            "delta_recovery": round(
                (rows[ids[0]].get("recovery", 0.0) - rows[ids[-1]].get("recovery", 0.0)), 4
            ),
        }

    @registry.capability(
        dataset="purification-batches", operation="calculate_yield", effect="compute",
        sensitivity="internal",
    )
    def calculate_yield(batch_ids: Optional[list[str]] = None, **_: object) -> dict:
        ids = list(batch_ids or ["B001"])
        return {
            "batch_ids": ids,
            "recovery": {b: _BATCHES.get(b, {}).get("recovery") for b in ids},
            "step_yield": {b: _BATCHES.get(b, {}).get("step_yield") for b in ids},
        }

    @registry.capability(
        dataset="purification-batches", operation="detect_outliers", effect="compute",
        sensitivity="confidential", policy="BPD-DATA-021",
    )
    def detect_outliers(metric: str = "recovery", **_: object) -> dict:
        values = {b: row.get(metric) for b, row in _BATCHES.items()}
        mean = sum(v for v in values.values() if v is not None) / max(len(values), 1)
        return {
            "batch_ids": sorted(values),
            "recovery": values,
            "outliers": [b for b, v in values.items() if v is not None and abs(v - mean) > 0.1],
        }

    @registry.capability(
        dataset="chromatography-results", operation="search", effect="read",
        sensitivity="internal",
    )
    def chrom_search(query: str = "", **_: object) -> dict:
        return {"runs": ["R-118", "R-119"], "query": query}

    @registry.capability(
        dataset="chromatography-results", operation="aggregate", effect="compute",
        sensitivity="internal",
    )
    def chrom_aggregate(metric: str = "resolution", **_: object) -> dict:
        return {"metric": metric, "mean": 1.84, "n": 2}

    @registry.capability(
        dataset="clinical-private", operation="search", effect="read",
        sensitivity="restricted", policy="BPD-CLIN-002",
    )
    def clinical_search(query: str = "", **_: object) -> dict:
        return {"subjects": ["S-0001", "S-0002"], "query": query}

    @registry.capability(
        dataset="clinical-private", operation="aggregate", effect="compute",
        sensitivity="restricted", policy="BPD-CLIN-002",
    )
    def clinical_aggregate(metric: str = "endpoint", **_: object) -> dict:
        return {"metric": metric, "mean": 0.41, "n": 2}

    return registry


def principals() -> dict[str, Principal]:
    """Four principals whose differences are the point.

    `process_engineer` and `analyst` differ only in whether they hold
    `detect_outliers`, which is the pair the cache isolation tests use: same
    question, same dataset, same revision, different authorization scope.
    """
    return {
        "process_engineer": Principal(
            principal_id="u-eng-01",
            principal_class="process-engineer",
            grants={
                "purification-batches": frozenset(
                    {"search", "compare_batches", "calculate_yield", "detect_outliers"}
                ),
                "chromatography-results": frozenset({"search", "aggregate"}),
            },
            clearance="confidential",
        ),
        "analyst": Principal(
            principal_id="u-ana-01",
            principal_class="analyst",
            grants={
                "purification-batches": frozenset({"search", "compare_batches"}),
                "chromatography-results": frozenset({"search"}),
            },
            clearance="internal",
        ),
        "clinical_reviewer": Principal(
            principal_id="u-clin-01",
            principal_class="clinical-reviewer",
            grants={
                "clinical-private": frozenset({"search", "aggregate"}),
                "purification-batches": frozenset({"search"}),
            },
            clearance="restricted",
        ),
        "external_auditor": Principal(
            principal_id="u-ext-01",
            principal_class="external-auditor",
            grants={"purification-batches": frozenset({"search"})},
            clearance="public",
        ),
    }


def build_control_plane(
    *,
    ledger_path: Optional[str] = None,
    interpreter: Optional[Interpreter] = None,
    authority: Optional[GrantAuthority] = None,
) -> ControlPlane:
    auth = authority or GrantAuthority(secret=b"reference-implementation-secret")
    return ControlPlane(
        descriptors=descriptor_registry(),
        capabilities=capability_registry(),
        authority=auth,
        ledger=EvidenceLedger(ledger_path),
        cache=SemanticCache(auth),
        interpreter=interpreter,
    )


def build_mcp_control_plane(
    *,
    ledger_path: Optional[str] = None,
    interpreter: Optional[Interpreter] = None,
    authority: Optional[GrantAuthority] = None,
) -> ControlPlane:
    """The same control plane with every dataset behind an MCP server.

    Descriptors are read off the wire rather than off disk, and every
    capability executes through a client session. Nothing else changes -- which
    is the claim milestone M3 exists to test, and the conformance suite is run
    against this factory as well as the local one to check it.
    """
    from ..mcp_boundary import (
        MCPDatasetClient,
        build_dataset_server,
        register_mcp_capabilities,
    )

    auth = authority or GrantAuthority(secret=b"reference-implementation-secret")
    server_side = descriptor_registry()
    server = build_dataset_server(server_side, capability_registry(), auth)
    client = MCPDatasetClient(server)
    remote_descriptors = client.descriptors()

    registry = CapabilityRegistry()
    register_mcp_capabilities(client, remote_descriptors, registry)

    plane = ControlPlane(
        descriptors=remote_descriptors,
        capabilities=registry,
        authority=auth,
        ledger=EvidenceLedger(ledger_path),
        cache=SemanticCache(auth),
        interpreter=interpreter,
    )
    # The dataset's own view of itself, on the far side of the boundary. A
    # revision change has to reach both sides; keeping the handle is what lets
    # a caller express "the data changed" rather than "my copy of the metadata
    # changed".
    plane.remote_descriptors = server_side
    return plane
