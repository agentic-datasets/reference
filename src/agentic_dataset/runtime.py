"""The control plane, expressed in no framework at all.

Every node here is an ordinary function of state. `adapters/native.py` calls
them in sequence; `adapters/langgraph_port.py` wires them as graph nodes with a
conditional edge; `adapters/llamaindex_port.py` as steps emitting typed events;
`adapters/adk_port.py` as an ADK agent with a before-tool callback. The four
differ in how control flows and agree on what is permitted, because none of
them contains a policy decision -- they all call `ControlPlane.admit`.

That is the experiment. If a governance model were a property of a framework,
porting it would require re-deciding something. Nothing here is re-decided.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from typing import Any, Optional, Protocol, Sequence

from .admission import Environment, Evaluator, PolicyEngine, scope_for
from .cache import CacheKey, SemanticCache
from .capabilities import CapabilityRegistry, ExecutionLog
from .descriptor import DatasetDescriptor, DescriptorRegistry
from .discovery import DiscoveryResult, SemanticIndex
from .grant import Grant, GrantAuthority, UnauthorizedExecution
from .intent import DatasetIntent, Interpreter, RuleBasedInterpreter
from .ledger import EvidenceLedger
from .principal import AuthorizationScope, Principal
from .provenance import EvidenceRecord, digest_result
from .verdict import Verdict

__all__ = ["Request", "RunResult", "RunState", "ControlPlane", "Runtime"]


@dataclass
class Request:
    text: str
    principal: Principal
    request_id: str = field(default_factory=lambda: "req-" + secrets.token_hex(4))
    dataset: Optional[str] = None
    capability: Optional[str] = None
    filters: Optional[dict] = None
    freshness: Optional[int] = None
    expected_schema_version: Optional[str] = None
    observation_count: int = 0
    evaluator: Evaluator = Evaluator()
    budget_s: Optional[float] = None
    grant_ttl_s: Optional[int] = None

    def hints(self) -> dict:
        out: dict[str, Any] = {}
        if self.dataset is not None:
            out["dataset"] = self.dataset
        if self.capability is not None:
            out["capability"] = self.capability
        if self.filters is not None:
            out["filters"] = self.filters
        if self.freshness is not None:
            out["freshness"] = self.freshness
        return out


@dataclass
class RunResult:
    """What a run did, in the terms the conformance suite asserts in.

    Note what is not here: the model's wording. `AD-004` is not "the answer
    said no", it is `grant is None and execution.tool_calls == []`.
    """

    request_id: str
    trace_id: str
    decision: str
    reason: str
    policy_id: Optional[str] = None
    rationale: Optional[str] = None
    dataset: Optional[str] = None
    capability: Optional[str] = None
    grant: Optional[Grant] = None
    result: Any = None
    cache_used: bool = False
    execution: ExecutionLog = field(default_factory=ExecutionLog)
    evidence: list[EvidenceRecord] = field(default_factory=list)
    path: list[str] = field(default_factory=list)
    candidates: tuple[str, ...] = ()
    authorized_candidates: tuple[str, ...] = ()
    withheld: tuple[str, ...] = ()
    scope: Optional[AuthorizationScope] = None
    errors: list[str] = field(default_factory=list)
    runtime: str = "native"

    @property
    def executed(self) -> bool:
        return self.execution.executed_anything

    def to_dict(self) -> dict:
        return {
            "runtime": self.runtime,
            "request_id": self.request_id,
            "trace_id": self.trace_id,
            "decision": self.decision,
            "reason": self.reason,
            "policy_id": self.policy_id,
            "rationale": self.rationale,
            "dataset": self.dataset,
            "capability": self.capability,
            "grant": self.grant.grant_id if self.grant else None,
            "cache_used": self.cache_used,
            "execution": self.execution.to_dict(),
            "path": list(self.path),
            "candidates": list(self.candidates),
            "authorized_candidates": list(self.authorized_candidates),
            "withheld": list(self.withheld),
            "scope": self.scope.to_dict() if self.scope else None,
            "evidence": [e.to_dict() for e in self.evidence],
            "errors": list(self.errors),
        }


@dataclass
class RunState:
    """Mutable state threaded through the nodes.

    Conversation history is not equivalent to system state, so there is no
    message list here. Every adapter maps its own state container onto this
    one rather than the other way round.
    """

    request: Request
    trace_id: str
    intent: Optional[DatasetIntent] = None
    discovery: Optional[DiscoveryResult] = None
    descriptor: Optional[DatasetDescriptor] = None
    capability_name: Optional[str] = None
    verdict: Optional[Verdict] = None
    scope: Optional[AuthorizationScope] = None
    grant: Optional[Grant] = None
    plan: list[dict] = field(default_factory=list)
    result: Any = None
    cache_used: bool = False
    execution: ExecutionLog = field(default_factory=ExecutionLog)
    evidence: list[EvidenceRecord] = field(default_factory=list)
    path: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class Runtime(Protocol):
    """What every adapter is. Four implementations, one signature."""

    name: str

    def run(self, request: Request) -> RunResult: ...


class ControlPlane:
    def __init__(
        self,
        *,
        descriptors: DescriptorRegistry,
        capabilities: CapabilityRegistry,
        policy: Optional[PolicyEngine] = None,
        authority: Optional[GrantAuthority] = None,
        ledger: Optional[EvidenceLedger] = None,
        cache: Optional[SemanticCache] = None,
        interpreter: Optional[Interpreter] = None,
    ) -> None:
        self.descriptors = descriptors
        self.capabilities = capabilities
        # `is None`, not `or`. `EvidenceLedger` and `SemanticCache` both define
        # __len__, so an empty one is falsy and `ledger or EvidenceLedger()`
        # silently throws away the configured ledger -- including the one
        # writing to disk. Found by tests/test_ledger.py.
        self.policy = policy if policy is not None else PolicyEngine()
        self.authority = authority if authority is not None else GrantAuthority()
        self.ledger = ledger if ledger is not None else EvidenceLedger()
        self.cache = cache if cache is not None else SemanticCache(self.authority)
        self.interpreter: Interpreter = (
            interpreter if interpreter is not None else RuleBasedInterpreter()
        )
        self.index = SemanticIndex(descriptors)

    # -- lifecycle --------------------------------------------------------
    def register_dataset(self, descriptor: DatasetDescriptor) -> None:
        """Add a dataset. Nothing else changes -- that is milestone M3's point.

        No adapter, no graph, no conformance assertion and no policy rule
        mentions a dataset by name, so registration is the whole integration.
        """
        self.descriptors.register(descriptor)
        self.index.reindex()

    def begin(self, request: Request) -> RunState:
        return RunState(request=request, trace_id="tr-" + secrets.token_hex(4))

    # -- nodes ------------------------------------------------------------
    def interpret(self, state: RunState) -> RunState:
        state.path.append("interpret")
        state.intent = self.interpreter.interpret(
            state.request.request_id, state.request.text, **state.request.hints()
        )
        return state

    def discover(self, state: RunState) -> RunState:
        state.path.append("discover")
        assert state.intent is not None
        state.discovery = self.index.discover(
            state.intent.objective,
            state.request.principal,
            k=10,
            required_capability=state.intent.required_capability,
        )
        return state

    def resolve(self, state: RunState) -> RunState:
        """Choose the dataset and the capability. Decide nothing about rights.

        When discovery surfaces nothing the principal may use, this
        deliberately falls back to the top-ranked candidate rather than
        stopping. Admission then refuses it by name, and the ledger says
        INSUFFICIENT_PRIVILEGE on a specific dataset instead of shrugging.
        """
        state.path.append("resolve")
        assert state.intent is not None and state.discovery is not None
        dataset_id = state.intent.candidate_dataset
        if dataset_id is None:
            if state.discovery.authorized_ids:
                dataset_id = state.discovery.authorized_ids[0]
            elif state.discovery.ranked_ids:
                dataset_id = state.discovery.ranked_ids[0]
        state.descriptor = self.descriptors.get(dataset_id) if dataset_id else None
        state.capability_name = state.intent.required_capability
        return state

    def admit(self, state: RunState) -> RunState:
        state.path.append("admit")
        assert state.intent is not None
        request = state.request
        environment = Environment(
            expected_schema_version=request.expected_schema_version,
            observation_count=request.observation_count,
            trace_id=state.trace_id,
        )
        state.verdict = self.policy.adjudicate(
            principal=request.principal,
            intent=state.intent,
            descriptor=state.descriptor,
            capability_name=state.capability_name,
            environment=environment,
            evaluator=request.evaluator,
            budget_s=request.budget_s,
        )
        approval = state.verdict.approved()
        if approval is not None:
            assert state.descriptor is not None and state.capability_name is not None
            capability = state.descriptor.capability(state.capability_name)
            assert capability is not None
            state.scope = scope_for(request.principal, state.descriptor, capability)
            state.grant = self.authority.mint(
                approval,
                dataset_revision=state.descriptor.revision,
                schema_version=state.descriptor.schema_version,
                scope=state.scope,
                ttl_s=request.grant_ttl_s,
            )
        return state

    @staticmethod
    def route(state: RunState) -> str:
        """The one branch in the system. Everything else is a straight line."""
        assert state.verdict is not None
        return {
            Verdict.GRANTED: "granted",
            Verdict.REFUSED: "refused",
            Verdict.INDETERMINATE: "indeterminate",
        }[state.verdict.kind]

    def lookup_cache(self, state: RunState) -> RunState:
        state.path.append("cache")
        key = self._cache_key(state)
        if key is None:
            return state
        hit, value = self.cache.lookup(key, state.grant)
        if hit:
            state.cache_used = True
            state.result = value
        return state

    def plan(self, state: RunState) -> RunState:
        """Planning happens after admissibility, and may not invent authority.

        The check that every step names the admitted capability is in
        `execute`, not here. Validating a list immediately after building it
        proves only that this function is self-consistent; the plan has to be
        checked where it is consumed, because that is the only place a plan
        that arrived from somewhere else would be caught.
        """
        state.path.append("plan")
        assert state.capability_name is not None and state.descriptor is not None
        assert state.intent is not None
        state.plan = [
            {
                "dataset": state.descriptor.dataset_id,
                "capability": state.capability_name,
                "arguments": dict(state.intent.filters),
            }
        ]
        return state

    def execute(self, state: RunState) -> RunState:
        state.path.append("execute")
        assert state.descriptor is not None
        try:
            for step in state.plan:
                # The planner is not allowed to invent new authority. A step
                # naming a second capability is not a richer plan, it is an
                # unadmitted one, and one admitted capability does not
                # authorise a sequence of them.
                if (
                    step["capability"] != state.capability_name
                    or step["dataset"] != state.descriptor.dataset_id
                ):
                    raise UnauthorizedExecution(
                        f"the plan names {step['dataset']}.{step['capability']}, "
                        f"which was not admitted"
                    )
                state.result = self.capabilities.invoke(
                    dataset=step["dataset"],
                    operation=step["capability"],
                    grant=state.grant,
                    authority=self.authority,
                    dataset_revision=state.descriptor.revision,
                    requested_scope=state.scope,
                    arguments=step["arguments"],
                    log=state.execution,
                )
        except UnauthorizedExecution as exc:
            state.errors.append(str(exc))
        return state

    def validate(self, state: RunState) -> RunState:
        """Machine-checkable properties are checked by machine.

        The LLM may explain the result. It is not the thing that decides
        whether the result satisfies the dataset's quality contract.
        """
        state.path.append("validate")
        if state.result is None or state.descriptor is None:
            return state
        contract = state.descriptor.quality_contract
        required = contract.get("required_fields", ())
        if required and isinstance(state.result, dict):
            missing = [f for f in required if f not in state.result]
            if missing:
                state.errors.append(
                    f"result is missing contracted fields: {', '.join(missing)}"
                )
        return state

    def store_cache(self, state: RunState) -> RunState:
        if state.result is None or state.cache_used:
            return state
        key = self._cache_key(state)
        if key is not None:
            self.cache.store(key, state.grant, state.result)
        return state

    def record(self, state: RunState) -> RunState:
        """Every terminal arm records, including the two that did nothing.

        AD-010 exists because a refusal that leaves no evidence is
        indistinguishable, three months later, from a request nobody made.
        """
        state.path.append("record")
        assert state.verdict is not None and state.intent is not None
        descriptor = state.descriptor
        record = EvidenceRecord(
            trace_id=state.trace_id,
            request_id=state.request.request_id,
            principal_class=state.request.principal.principal_class,
            decision=state.verdict.kind,
            reason=state.verdict.reason,
            policy_id=state.verdict.policy_id,
            policy_version=self.policy.policy_version,
            rationale=(
                state.verdict.indeterminate.rationale
                if state.verdict.indeterminate is not None
                else None
            ),
            requested_dataset=state.intent.candidate_dataset,
            dataset_id=descriptor.dataset_id if descriptor else None,
            dataset_version=descriptor.version if descriptor else None,
            dataset_revision=descriptor.revision if descriptor else None,
            schema_version=descriptor.schema_version if descriptor else None,
            capability=state.capability_name,
            objective=state.intent.objective,
            authorization_scope=state.scope.to_dict() if state.scope else None,
            grant_id=state.grant.grant_id if state.grant else None,
            cache={"used": state.cache_used},
            execution=state.execution.to_dict(),
            result_digest=digest_result(state.result) if state.result is not None else None,
        )
        state.evidence.append(record)
        self.ledger.append(record)
        return state

    # -- helpers ----------------------------------------------------------
    def _cache_key(self, state: RunState) -> Optional[CacheKey]:
        if state.descriptor is None or state.capability_name is None or state.scope is None:
            return None
        assert state.intent is not None
        return CacheKey.build(
            semantic_intent=state.intent.semantic_key(),
            dataset=state.descriptor.dataset_id,
            revision=state.descriptor.revision,
            capability=state.capability_name,
            scope=state.scope,
            schema_version=state.descriptor.schema_version,
            freshness=state.intent.freshness_requirement,
            policy_version=self.policy.policy_version,
        )

    def finish(self, state: RunState, runtime: str = "native") -> RunResult:
        assert state.verdict is not None
        discovery = state.discovery
        return RunResult(
            request_id=state.request.request_id,
            trace_id=state.trace_id,
            decision=state.verdict.kind,
            reason=state.verdict.reason,
            policy_id=state.verdict.policy_id,
            rationale=(
                state.verdict.indeterminate.rationale
                if state.verdict.indeterminate is not None
                else None
            ),
            dataset=state.descriptor.dataset_id if state.descriptor else None,
            capability=state.capability_name,
            grant=state.grant,
            result=state.result,
            cache_used=state.cache_used,
            execution=state.execution,
            evidence=list(state.evidence),
            path=list(state.path),
            candidates=discovery.ranked_ids if discovery else (),
            authorized_candidates=discovery.authorized_ids if discovery else (),
            withheld=discovery.withheld if discovery else (),
            scope=state.scope,
            errors=list(state.errors),
            runtime=runtime,
        )
