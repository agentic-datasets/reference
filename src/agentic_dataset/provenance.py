"""Evidence records.

The final answer may summarise this; the authoritative record is
machine-readable. `REQUIRED_FIELDS` is the operational definition of AD-009:
a record missing any of them cannot answer "what produced this result, under
which rules, against which data".

AD-011 and AD-012 are two of those fields, called out separately in the suite
because they are the two most often dropped -- evidence that records a decision
but not which revision it was made against, or not which policy version made
it, is evidence that cannot be replayed.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Optional

__all__ = [
    "EvidenceRecord",
    "ALWAYS_REQUIRED",
    "REQUIRED_WHEN_DATASET_RESOLVED",
    "REQUIRED_FIELDS",
]

# Present on every record, including the ones that describe a run which did
# nothing. A refusal that cannot say who was refused, when, or under which
# policy version is not evidence.
ALWAYS_REQUIRED = (
    "trace_id",
    "request_id",
    "principal_class",
    "decision",
    "reason",
    "policy_version",
    "recorded_at",
)

# Required only once a dataset was actually resolved. A request refused for
# MISSING_DESCRIPTOR has no revision to record, and demanding one would force
# the ledger to invent a value -- which is the failure mode, not the fix.
#
# `dataset_id` is therefore the dataset that was *read*, and `requested_dataset`
# the one that was *asked for*. Writing the requested name into `dataset_id`
# was the first thing AD-009 caught in this implementation: every row then
# claimed a dataset, and three of the four fields describing it were null.
REQUIRED_WHEN_DATASET_RESOLVED = (
    "dataset_version",
    "dataset_revision",
    "schema_version",
)

REQUIRED_FIELDS = ALWAYS_REQUIRED + ("dataset_id",) + REQUIRED_WHEN_DATASET_RESOLVED


@dataclass
class EvidenceRecord:
    trace_id: str
    request_id: str
    principal_class: str
    decision: str
    reason: str
    policy_version: str
    requested_dataset: Optional[str] = None
    dataset_id: Optional[str] = None
    dataset_version: Optional[str] = None
    dataset_revision: Optional[str] = None
    schema_version: Optional[str] = None
    capability: Optional[str] = None
    policy_id: Optional[str] = None
    rationale: Optional[str] = None
    objective: Optional[str] = None
    authorization_scope: Optional[dict] = None
    grant_id: Optional[str] = None
    cache: dict = field(default_factory=lambda: {"used": False})
    execution: dict = field(default_factory=dict)
    result_digest: Optional[str] = None
    recorded_at: float = field(default_factory=time.time)

    def missing_fields(self) -> list[str]:
        """AD-009. Empty means the record can stand on its own."""
        data = asdict(self)
        required = list(ALWAYS_REQUIRED)
        if self.dataset_id:
            required.extend(REQUIRED_WHEN_DATASET_RESOLVED)
        return [f for f in required if data.get(f) in (None, "")]

    @property
    def is_complete(self) -> bool:
        return not self.missing_fields()

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, default=str)


def digest_result(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]
