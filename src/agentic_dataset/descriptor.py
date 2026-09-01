"""The dataset contract.

The descriptor is not documentation. It participates directly in admission and
execution: `admission.adjudicate` reads its capabilities, prohibitions, schema
version, freshness and retention contracts, and a dataset without a well-formed
one cannot be operated on at all (AD-001).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

__all__ = [
    "DatasetCapability",
    "DatasetDescriptor",
    "DescriptorRegistry",
    "SENSITIVITY_ORDER",
]

# Ordered least to most restrictive. A principal's clearance must reach at
# least as far as the capability's sensitivity.
SENSITIVITY_ORDER = ("public", "internal", "confidential", "restricted")

EFFECTS = ("read", "compute", "write")


@dataclass(frozen=True)
class DatasetCapability:
    """A bounded operation, not a generic tool.

    `query_database(sql)` is too permissive: it hands the model the
    infrastructure. A capability names one operation and carries the metadata
    the control plane needs -- dataset, effect, classification, policy -- which
    the model never sees.
    """

    name: str
    description: str = ""
    effect: str = "read"
    sensitivity: str = "internal"
    required_policy: Optional[str] = None
    arguments: tuple[str, ...] = ()

    def errors(self) -> list[str]:
        problems = []
        if not self.name:
            problems.append("capability has no name")
        if self.effect not in EFFECTS:
            problems.append(f"{self.name}: effect {self.effect!r} not in {EFFECTS}")
        if self.sensitivity not in SENSITIVITY_ORDER:
            problems.append(
                f"{self.name}: sensitivity {self.sensitivity!r} not in {SENSITIVITY_ORDER}"
            )
        return problems

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "effect": self.effect,
            "sensitivity": self.sensitivity,
            "policy": self.required_policy,
            "arguments": list(self.arguments),
        }


@dataclass(frozen=True)
class DatasetDescriptor:
    dataset_id: str
    version: str
    description: str = ""
    revision: str = ""
    schema_version: str = "1"
    schemas: tuple[str, ...] = ()
    capabilities: tuple[DatasetCapability, ...] = ()
    prohibited: tuple[str, ...] = ()
    policies: tuple[str, ...] = ()
    provenance: Mapping[str, Any] = field(default_factory=dict)
    freshness_max_age_s: Optional[int] = None
    age_s: int = 0
    quality_contract: Mapping[str, Any] = field(default_factory=dict)
    retention_contract: Mapping[str, Any] = field(default_factory=dict)
    endpoints: Mapping[str, Any] = field(default_factory=dict)

    def capability(self, name: str) -> Optional[DatasetCapability]:
        for cap in self.capabilities:
            if cap.name == name:
                return cap
        return None

    def is_prohibited(self, name: str) -> bool:
        return name in self.prohibited

    def errors(self) -> list[str]:
        """AD-001. Empty list means the contract is well formed."""
        problems: list[str] = []
        if not self.dataset_id:
            problems.append("descriptor has no dataset_id")
        if not self.version:
            problems.append(f"{self.dataset_id}: descriptor has no version")
        if not self.revision:
            problems.append(f"{self.dataset_id}: descriptor has no revision")
        if not self.capabilities:
            problems.append(f"{self.dataset_id}: descriptor advertises no capabilities")
        seen: set[str] = set()
        for cap in self.capabilities:
            problems.extend(cap.errors())
            if cap.name in seen:
                problems.append(f"{self.dataset_id}: duplicate capability {cap.name!r}")
            seen.add(cap.name)
            if cap.name in self.prohibited:
                problems.append(
                    f"{self.dataset_id}: {cap.name!r} is both advertised and prohibited"
                )
        return problems

    @property
    def is_valid(self) -> bool:
        return not self.errors()

    # -- semantic surface used by discovery -------------------------------
    @property
    def text(self) -> str:
        parts = [self.dataset_id.replace("-", " "), self.description]
        parts.extend(c.name.replace("_", " ") for c in self.capabilities)
        parts.extend(c.description for c in self.capabilities)
        parts.extend(s.replace("_", " ") for s in self.schemas)
        return " ".join(p for p in parts if p)

    def to_dict(self) -> dict:
        return {
            "dataset": self.dataset_id,
            "version": self.version,
            "revision": self.revision,
            "schema_version": self.schema_version,
            "description": self.description,
            "schemas": list(self.schemas),
            "capabilities": [c.to_dict() for c in self.capabilities],
            "prohibited": list(self.prohibited),
            "policies": list(self.policies),
            "provenance": dict(self.provenance),
            "freshness": {"maximum_age_s": self.freshness_max_age_s},
            "age_s": self.age_s,
            "quality": dict(self.quality_contract),
            "retention": dict(self.retention_contract),
            "endpoints": dict(self.endpoints),
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "DatasetDescriptor":
        caps = tuple(
            DatasetCapability(
                name=c["name"],
                description=c.get("description", ""),
                effect=c.get("effect", "read"),
                sensitivity=c.get("sensitivity", "internal"),
                required_policy=c.get("policy"),
                arguments=tuple(c.get("arguments", ())),
            )
            for c in raw.get("capabilities", ())
        )
        freshness = raw.get("freshness") or {}
        return cls(
            dataset_id=raw["dataset"],
            version=raw.get("version", ""),
            description=raw.get("description", ""),
            revision=raw.get("revision", ""),
            schema_version=str(raw.get("schema_version", "1")),
            schemas=tuple(raw.get("schemas", ())),
            capabilities=caps,
            prohibited=tuple(raw.get("prohibited", ())),
            policies=tuple(raw.get("policies", ())),
            provenance=dict(raw.get("provenance", {})),
            freshness_max_age_s=freshness.get("maximum_age_s"),
            age_s=int(raw.get("age_s", 0)),
            quality_contract=dict(raw.get("quality", {})),
            retention_contract=dict(raw.get("retention", {})),
            endpoints=dict(raw.get("endpoints", {})),
        )


class DescriptorRegistry:
    """The set of datasets the control plane knows about.

    Registration is where a new dataset enters the system. Nothing in the
    graph, the adapters or the conformance suite needs changing to add one --
    that is what AD-002 and milestone M3 are testing.
    """

    def __init__(self, descriptors: Sequence[DatasetDescriptor] = ()) -> None:
        self._by_id: dict[str, DatasetDescriptor] = {}
        for d in descriptors:
            self.register(d)

    def register(self, descriptor: DatasetDescriptor) -> None:
        self._by_id[descriptor.dataset_id] = descriptor

    def get(self, dataset_id: str) -> Optional[DatasetDescriptor]:
        return self._by_id.get(dataset_id)

    def all(self) -> tuple[DatasetDescriptor, ...]:
        return tuple(self._by_id.values())

    def __len__(self) -> int:
        return len(self._by_id)

    def __contains__(self, dataset_id: object) -> bool:
        return dataset_id in self._by_id

    @classmethod
    def from_json_file(cls, path: str | Path) -> "DescriptorRegistry":
        raw = json.loads(Path(path).read_text())
        items = raw if isinstance(raw, list) else raw.get("datasets", [])
        return cls([DatasetDescriptor.from_dict(d) for d in items])
