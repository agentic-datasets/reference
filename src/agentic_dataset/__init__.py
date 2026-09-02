"""An agentic dataset: a governed runtime object, not a data source with a tool.

    The LLM may interpret, propose, rank and explain.
    The control plane decides whether execution is allowed.

The core of this package has no dependencies. Framework ports live in
`agentic_dataset.adapters` and are optional.
"""

from .admission import Environment, Evaluator, PolicyEngine, scope_for
from .cache import CacheKey, SemanticCache
from .capabilities import (
    BoundCapability,
    CapabilityRegistry,
    ExecutionLog,
    dataset_capability,
)
from .descriptor import DatasetCapability, DatasetDescriptor, DescriptorRegistry
from .discovery import SemanticIndex, authorized_recall_at_k, recall_at_k
from .grant import Grant, GrantAuthority, UnauthorizedExecution
from .intent import DatasetIntent, LLMInterpreter, RuleBasedInterpreter
from .ledger import EvidenceLedger
from .principal import AuthorizationScope, Principal
from .provenance import EvidenceRecord
from .runtime import ControlPlane, Request, RunResult, RunState, Runtime
from .verdict import (
    Approved,
    Indeterminate,
    IndeterminateReason,
    Refusal,
    RefusalReason,
    Verdict,
)

__version__ = "0.1.0rc1"

__all__ = [
    "Approved", "AuthorizationScope", "BoundCapability", "CacheKey",
    "CapabilityRegistry", "ControlPlane", "DatasetCapability",
    "DatasetDescriptor", "DatasetIntent", "DescriptorRegistry", "Environment",
    "Evaluator", "EvidenceLedger", "EvidenceRecord", "ExecutionLog", "Grant",
    "GrantAuthority", "Indeterminate", "IndeterminateReason", "LLMInterpreter",
    "PolicyEngine", "Principal", "Refusal", "RefusalReason", "Request",
    "RuleBasedInterpreter", "RunResult", "RunState", "Runtime", "SemanticCache",
    "SemanticIndex", "UnauthorizedExecution", "Verdict", "authorized_recall_at_k",
    "dataset_capability", "recall_at_k", "scope_for",
]
