"""A deliberately boring implementation of the agentic-dataset contract.

Written from `CONFORMANCE.md` and `src/agentic_dataset/conformance/verbs.md`.
It imports the conformance *interface* and nothing else: no `ControlPlane`, no
ledger, no capability registry, no `DelegatedExecutor`. It ships inside the
conformance distribution precisely because it depends on nothing that
distribution does not contain.
There is no framework, no MCP, no descriptor class -- the world arrives as
dicts and stays dicts.

It exists to answer one question: **is the specification implementable without
the reference implementation?** If this passes the same vectors, the harness is
testing the contract rather than testing its own internals.

It is not a good implementation. Grants are integers in a set, the cache is a
dict, and the interpreter is nine keywords. That is the point -- everything
interesting about the reference implementation is absent, and the assertions
still hold.
"""

from __future__ import annotations

import itertools
import re
import time
from typing import Any, Sequence

from .interface import Observation, Scope

SENSITIVITY = ("public", "internal", "confidential", "restricted")

POLICY_IDS = {
    "MISSING_DESCRIPTOR": "AD-POL-001",
    "DESCRIPTOR_INVALID": "AD-POL-002",
    "UNREGISTERED_CAPABILITY": "AD-POL-003",
    "PROHIBITED_OPERATION": "AD-POL-004",
    "INSUFFICIENT_PRIVILEGE": "AD-POL-005",
    "CLASSIFICATION_EXCEEDS_CLEARANCE": "AD-POL-006",
    "SCHEMA_VERSION_MISMATCH": "AD-POL-007",
    "FRESHNESS_UNSATISFIABLE": "AD-POL-008",
}

KEYWORDS = (
    ("compare", "compare_batches"),
    ("outlier", "detect_outliers"),
    ("yield", "calculate_yield"),
    ("recovery", "calculate_yield"),
    ("aggregate", "aggregate"),
    ("search", "search"),
    ("find", "search"),
)


class ToyImplementation:
    name = "toy"

    def __init__(self) -> None:
        self._ids = itertools.count(1)
        self._world: dict = {}
        self.reset()

    # -- interface --------------------------------------------------------
    def load_world(self, world: dict) -> None:
        self._world = world
        self._datasets = {d["dataset"]: dict(d) for d in world.get("datasets", ())}
        # What this implementation actually has code for, fixed at load time.
        # The first version of this file derived it from the descriptors
        # instead, which made every advertised capability executable by
        # construction -- AD-002 caught that on the first run, which is the
        # clearest evidence available that the suite is not vacuous.
        self._implemented = {
            (d["dataset"], c["name"])
            for d in world.get("datasets", ())
            for c in d.get("capabilities", ())
        }
        self._principals = {k: _copy_principal(v) for k, v in world.get("principals", {}).items()}
        self._policy_version = world.get("policy_version", "0")
        self._budget_s = world.get("policy_budget_s", 0.25)
        self.reset()

    def capabilities(self) -> Sequence[dict]:
        """Everything this implementation will execute.

        Reported from `_implemented`, not from the descriptors. Advertising a
        capability and having one are different facts, and AD-002 is the
        assertion that notices when they are conflated.
        """
        return [
            {"dataset": dataset_id, "name": c["name"], "effect": c.get("effect", "read"),
             "sensitivity": c.get("sensitivity", "internal"), "policy": c.get("policy")}
            for dataset_id, d in self._datasets.items()
            for c in d.get("capabilities", ())
            if (dataset_id, c["name"]) in self._implemented
        ]

    def reset(self) -> None:
        self._cache: dict[tuple, Any] = {}
        self._grants: dict[int, dict] = {}
        self._last: dict | None = None

    def step(self, step: dict) -> Observation | None:
        return getattr(self, f"_op_{step['op']}")(step)

    # -- verbs ------------------------------------------------------------
    def _op_request(self, step: dict) -> Observation:
        principal = self._principals[step["principal"]]
        dataset_id, capability_name = self._resolve(step, principal)
        descriptor = self._datasets.get(dataset_id) if dataset_id else None

        evaluator = step.get("evaluator") or {}
        if not evaluator.get("reachable", True):
            return self._terminal(
                "INDETERMINATE", "EVALUATOR_UNAVAILABLE", principal, dataset_id,
                descriptor, capability_name,
                rationale="the policy authority could not be reached",
            )
        if evaluator.get("latency_s", 0.0) > self._budget_s:
            return self._terminal(
                "INDETERMINATE", "EVALUATOR_TIMEOUT", principal, dataset_id,
                descriptor, capability_name,
                rationale="the policy authority did not answer within the budget",
            )

        refusal = self._evaluate(step, principal, descriptor, capability_name)
        if refusal is not None:
            return self._terminal(
                "REFUSED", refusal, principal, dataset_id, descriptor, capability_name
            )

        capability = _capability(descriptor, capability_name)
        scope = Scope(
            principal_class=principal["principal_class"],
            dataset=dataset_id,
            capabilities=frozenset({capability_name}),
            max_sensitivity=min(
                capability.get("sensitivity", "internal"), principal["clearance"],
                key=SENSITIVITY.index,
            ),
        )
        ttl = step.get("grant_ttl_s")
        grant_id = next(self._ids)
        self._grants[grant_id] = {
            "dataset": dataset_id, "revision": descriptor["revision"],
            "capability": capability_name, "scope": scope,
            "expires_at": time.time() + (300 if ttl is None else ttl),
        }
        self._last = {"grant": grant_id, "scope": scope}

        key = (
            _intent_key(step["text"]), dataset_id, descriptor["revision"], capability_name,
            scope.principal_class, tuple(sorted(scope.capabilities)), scope.max_sensitivity,
            str(descriptor.get("schema_version", "1")), step.get("freshness"),
            self._policy_version,
        )
        errors: list[str] = []
        executed: list[str] = []
        cache_hit = key in self._cache
        result = self._cache.get(key)
        if not cache_hit:
            try:
                result = self._execute(grant_id, dataset_id, capability_name)
                executed.append(f"{dataset_id}.{capability_name}")
                self._cache[key] = result
            except PermissionError as exc:
                errors.append(str(exc))
                result = None

        return self._observe(
            "GRANTED", "PRINCIPAL_AUTHORIZED", principal, dataset_id, descriptor,
            capability_name, policy_id=capability.get("policy"),
            grant_scope=scope, executed_scope=scope if executed else None,
            tool_calls=executed, cache_hit=cache_hit,
            result_present=result is not None, errors=errors,
        )

    def _op_delegate(self, step: dict) -> Observation:
        requested = Scope.from_dict(step["scope"])
        parent = self._last
        errors: list[str] = []
        calls: list[str] = []
        if parent is None or not parent["scope"].covers(requested):
            errors.append(f"{step['channel']} delegation widens the authorization scope")
        else:
            try:
                self._execute(parent["grant"], step["dataset"], step["capability"])
                calls.append(f"{step['channel']}-target:{step['dataset']}.{step['capability']}")
            except PermissionError as exc:
                errors.append(str(exc))
        return Observation(
            decision="GRANTED", reason="PRINCIPAL_AUTHORIZED",
            granted=parent is not None,
            grant_scope=parent["scope"].__dict__ | {
                "capabilities": sorted(parent["scope"].capabilities)} if parent else None,
            executed_scope=(
                {"principal_class": requested.principal_class, "dataset": requested.dataset,
                 "capabilities": sorted(requested.capabilities),
                 "max_sensitivity": requested.max_sensitivity} if calls else None),
            dataset=step["dataset"], capability=step["capability"],
            mcp_calls=calls if step["channel"] == "mcp" else [],
            a2a_calls=calls if step["channel"] == "a2a" else [],
            errors=errors,
        )

    def _op_grant(self, step: dict) -> None:
        self._principals[step["principal"]]["grants"].setdefault(
            step["dataset"], []
        ).append(step["capability"])
        return None

    def _op_revoke(self, step: dict) -> None:
        self._principals[step["principal"]]["grants"].pop(step["dataset"], None)
        return None

    def _op_set_revision(self, step: dict) -> None:
        self._datasets[step["dataset"]]["revision"] = step["revision"]
        return None

    def _op_set_policy_version(self, step: dict) -> None:
        self._policy_version = step["version"]
        return None

    def _op_register_descriptor(self, step: dict) -> None:
        self._datasets[step["descriptor"]["dataset"]] = dict(step["descriptor"])
        return None

    def _op_reset(self, step: dict) -> None:
        self.reset()
        return None

    # -- the rules --------------------------------------------------------
    def _resolve(self, step: dict, principal: dict) -> tuple[str | None, str | None]:
        capability = step.get("capability")
        if capability is None:
            lowered = f" {step['text'].lower()} "
            capability = next((c for word, c in KEYWORDS if word in lowered), None)
        dataset = step.get("dataset")
        if dataset is None:
            candidates = [
                d for d, spec in self._datasets.items()
                if any(c["name"] == capability for c in spec.get("capabilities", ()))
            ]
            allowed = [d for d in candidates if principal["grants"].get(d)]
            dataset = (allowed or candidates or [None])[0]
        return dataset, capability

    def _evaluate(
        self, step: dict, principal: dict, descriptor: dict | None, capability_name: str | None
    ) -> str | None:
        if descriptor is None:
            return "MISSING_DESCRIPTOR"
        if not descriptor.get("revision") or not descriptor.get("capabilities"):
            return "DESCRIPTOR_INVALID"
        if capability_name is None:
            return "UNREGISTERED_CAPABILITY"
        if capability_name in descriptor.get("prohibited", ()):
            return "PROHIBITED_OPERATION"
        capability = _capability(descriptor, capability_name)
        if capability is None:
            return "UNREGISTERED_CAPABILITY"
        expected = step.get("expected_schema_version")
        if expected is not None and expected != str(descriptor.get("schema_version", "1")):
            return "SCHEMA_VERSION_MISMATCH"
        held = principal["grants"].get(descriptor["dataset"], [])
        if capability_name not in held:
            return "INSUFFICIENT_PRIVILEGE"
        if SENSITIVITY.index(principal["clearance"]) < SENSITIVITY.index(
            capability.get("sensitivity", "internal")
        ):
            return "CLASSIFICATION_EXCEEDS_CLEARANCE"
        freshness = step.get("freshness")
        if freshness is not None and descriptor.get("age_s", 0) > freshness:
            return "FRESHNESS_UNSATISFIABLE"
        return None

    def _execute(self, grant_id: int, dataset: str, capability: str) -> dict:
        """No grant, no execution. The only door."""
        grant = self._grants.get(grant_id)
        if grant is None:
            raise PermissionError("no approval token: execution is unreachable")
        if time.time() > grant["expires_at"]:
            raise PermissionError("approval token has expired")
        if grant["dataset"] != dataset or grant["capability"] != capability:
            raise PermissionError("approval token is for a different dataset or capability")
        if grant["revision"] != self._datasets[dataset]["revision"]:
            raise PermissionError("approval token is for a different dataset revision")
        if (dataset, capability) not in self._implemented:
            raise PermissionError(
                f"{dataset}.{capability} is not a registered capability"
            )
        return {"dataset": dataset, "capability": capability, "rows": 2}

    # -- evidence ---------------------------------------------------------
    def _terminal(self, decision, reason, principal, dataset_id, descriptor,
                  capability_name, rationale=None) -> Observation:
        return self._observe(
            decision, reason, principal, dataset_id, descriptor, capability_name,
            policy_id=POLICY_IDS.get(reason) if decision == "REFUSED" else None,
            rationale=rationale,
        )

    def _observe(self, decision, reason, principal, dataset_id, descriptor,
                 capability_name, policy_id=None, rationale=None, grant_scope=None,
                 executed_scope=None, tool_calls=None, cache_hit=False,
                 result_present=False, errors=None) -> Observation:
        row = {
            "trace_id": f"tr-{next(self._ids)}",
            "request_id": f"req-{next(self._ids)}",
            "principal_class": principal["principal_class"],
            "decision": decision, "reason": reason,
            "policy_version": self._policy_version,
            "policy_id": policy_id, "rationale": rationale,
            "capability": capability_name,
            "recorded_at": time.time(),
        }
        if descriptor is not None and descriptor.get("revision"):
            row |= {
                "dataset_id": descriptor["dataset"],
                "dataset_version": descriptor.get("version"),
                "dataset_revision": descriptor["revision"],
                "schema_version": str(descriptor.get("schema_version", "1")),
            }
        as_dict = (
            lambda s: {"principal_class": s.principal_class, "dataset": s.dataset,
                       "capabilities": sorted(s.capabilities),
                       "max_sensitivity": s.max_sensitivity} if s else None
        )
        return Observation(
            decision=decision, reason=reason, policy_id=policy_id, rationale=rationale,
            granted=grant_scope is not None, grant_scope=as_dict(grant_scope),
            executed_scope=as_dict(executed_scope),
            dataset=descriptor["dataset"] if descriptor else None,
            capability=capability_name, tool_calls=list(tool_calls or []),
            cache_hit=cache_hit, result_present=result_present,
            evidence=[row], errors=list(errors or []),
        )


def _capability(descriptor: dict | None, name: str | None) -> dict | None:
    if descriptor is None or name is None:
        return None
    return next((c for c in descriptor.get("capabilities", ()) if c["name"] == name), None)


def _copy_principal(spec: dict) -> dict:
    return {**spec, "grants": {k: list(v) for k, v in spec["grants"].items()}}


def _intent_key(text: str) -> tuple[str, ...]:
    stop = {"the", "a", "an", "of", "for", "in", "on", "at", "to"}
    return tuple(sorted(w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in stop))
