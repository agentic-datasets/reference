"""Natural language in, structured intent out.

This is the one place in the control plane where a language model is the right
tool: the task is semantic interpretation. Its output is structured and
validated *before* it reaches admission, and nothing downstream trusts it for
anything but what to attempt.

The default interpreter here is deterministic rather than model-backed, so the
conformance suite runs without an API key and without a spread. `LLMInterpreter`
takes any callable returning the same structure; swapping it in changes what is
attempted and cannot change what is permitted, which is the thesis.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Optional, Protocol

__all__ = ["DatasetIntent", "Interpreter", "RuleBasedInterpreter", "LLMInterpreter"]


@dataclass(frozen=True)
class DatasetIntent:
    request_id: str
    objective: str
    operation: Optional[str] = None
    candidate_dataset: Optional[str] = None
    required_capability: Optional[str] = None
    filters: Mapping[str, Any] = field(default_factory=dict)
    freshness_requirement: Optional[int] = None
    temporal_requirement: Optional[Mapping[str, Any]] = None
    requested_output: Optional[str] = None

    def semantic_key(self) -> str:
        """A stable hash of what was asked, not of how it was worded.

        Lexical, not semantic, and the name is the most generous thing about
        it: case, punctuation, word order and a short closed list of function
        words are normalised away, and nothing else is. Two questions that mean
        the same thing in different words will miss.

        That is the safe direction to be wrong in. A cache that under-hits
        costs latency; a cache that over-hits returns one principal's answer to
        another principal's question. The closed word list is short for the
        same reason -- every word removed is a pair of sentences that might now
        collide. An embedding-keyed variant belongs behind the same
        authorization dimensions, not instead of them.

        Filters are not normalised at all: different batch ids are different
        questions.
        """
        words = sorted(
            w
            for w in re.findall(r"[a-z0-9]+", self.objective.lower())
            if w not in _FUNCTION_WORDS
        )
        payload = {
            "objective": words,
            "operation": self.operation,
            "capability": self.required_capability,
            "filters": self.filters,
            "output": self.requested_output,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "objective": self.objective,
            "operation": self.operation,
            "candidate_dataset": self.candidate_dataset,
            "required_capability": self.required_capability,
            "filters": dict(self.filters),
            "freshness_requirement": self.freshness_requirement,
            "temporal_requirement": dict(self.temporal_requirement or {}) or None,
            "requested_output": self.requested_output,
        }


class Interpreter(Protocol):
    def interpret(self, request_id: str, request: str, **hints: Any) -> DatasetIntent: ...


# operation -> (verbs that imply it, capability it usually needs)
#
# Ordered most specific first, and the order is load-bearing. With "recovery"
# ahead of "outlier", *detect outliers in the recovery distribution* resolves to
# `calculate_yield`: the broader term matches first and the sentence never
# reaches the rule that was written for it. `evals/evaluate.py` caught that as
# capability selection 0.800 against a 0.97 gate, which is the argument for
# having the evaluator rather than for having a better keyword table.
_OPERATIONS: tuple[tuple[str, tuple[str, ...], str], ...] = (
    ("compare", ("compare", "versus", " vs ", "difference between"), "compare_batches"),
    ("outlier", ("outlier", "anomaly", "anomalous", "deviation"), "detect_outliers"),
    ("aggregate", ("aggregate", "total", "sum", "average", "mean"), "aggregate"),
    ("yield", ("yield", "recovery"), "calculate_yield"),
    ("materialize", ("materialize", "export", "extract to", "write"), "materialize"),
    ("delete", ("delete", "drop", "purge", "erase"), "delete_source"),
    ("overwrite", ("overwrite", "rewrite", "amend the record"), "overwrite_batch_record"),
    ("retrieve", ("retrieve", "fetch", "get", "show me", "list"), "retrieve"),
    ("search", ("search", "find", "which", "what", "why", "where"), "search"),
)

_BATCH_RE = re.compile(r"\b([A-Z]{1,3}\d{2,4})\b")

# Deliberately short. See `DatasetIntent.semantic_key`: every addition here
# widens the set of sentences that share a cache entry.
_FUNCTION_WORDS = frozenset({"the", "a", "an", "of", "for", "in", "on", "at", "to"})


class RuleBasedInterpreter:
    """Deterministic interpretation. No model, no key, no variance.

    It is not clever, and it does not have to be: a wrong capability guess ends
    in a refusal or a bad answer, never in an unauthorised execution. That is
    exactly the property the split between intelligence and authority buys.
    """

    def interpret(self, request_id: str, request: str, **hints: Any) -> DatasetIntent:
        lowered = f" {request.lower()} "
        operation: Optional[str] = None
        capability: Optional[str] = None
        for op, verbs, cap in _OPERATIONS:
            if any(v in lowered for v in verbs):
                operation, capability = op, cap
                break

        filters: dict[str, Any] = {}
        batches = _BATCH_RE.findall(request)
        if batches:
            filters["batch_ids"] = batches

        return DatasetIntent(
            request_id=request_id,
            objective=request.strip(),
            operation=operation,
            candidate_dataset=hints.get("dataset"),
            required_capability=hints.get("capability", capability),
            filters=hints.get("filters", filters),
            freshness_requirement=hints.get("freshness"),
            temporal_requirement=hints.get("temporal"),
            requested_output=hints.get("output"),
        )


class LLMInterpreter:
    """Model-backed interpretation, structurally identical downstream.

    `call` takes the request and returns a mapping. Whatever it returns is
    coerced into a `DatasetIntent` and then treated with exactly the suspicion
    the rule-based one is: `tests/test_adversarial.py` runs the suite with an
    interpreter that actively tries to name prohibited capabilities.
    """

    def __init__(self, call: Callable[[str], Mapping[str, Any]]) -> None:
        self._call = call

    def interpret(self, request_id: str, request: str, **hints: Any) -> DatasetIntent:
        raw = dict(self._call(request))
        return DatasetIntent(
            request_id=request_id,
            objective=str(raw.get("objective", request)),
            operation=raw.get("operation"),
            candidate_dataset=raw.get("candidate_dataset", hints.get("dataset")),
            required_capability=raw.get("required_capability", hints.get("capability")),
            filters=raw.get("filters", {}) or {},
            freshness_requirement=raw.get("freshness_requirement", hints.get("freshness")),
            temporal_requirement=raw.get("temporal_requirement"),
            requested_output=raw.get("requested_output"),
        )
