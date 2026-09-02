"""Broken implementations, and the assertions that must notice.

A suite that passes against a correct implementation has shown one thing: that
it is not obviously wrong. What it has not shown is that it would fail against
a *broken* one, and a suite which cannot fail is decoration.

Each mutant below removes exactly one guarantee from `ToyImplementation` and
declares which assertion must catch it. `TARGETS` is the contract, and
`tests/test_conformance_vectors.py` asserts every mutant is caught by the
assertion named -- not merely by some assertion.

Every one of the fifteen assertions has at least one mutant of its own. The
first version of this file had thirteen mutants covering eleven assertions,
which meant AD-002, AD-009, AD-013 and AD-014 were only ever exercised as
cross-detectors -- visible the moment the detection matrix was drawn, and not
before.

Mutants often break more than their target. That is expected and is reported:
`agentic-dataset-conformance run --matrix` prints which assertion catches
which mutant, and the off-diagonal entries are a fact about how the assertions
overlap rather than noise. Safety invariants that never overlap are usually
invariants that do not cover much.
"""

from __future__ import annotations

from .toy import SENSITIVITY, ToyImplementation

__all__ = ["MUTANTS", "TARGETS"]


class ExecutesWithoutAGrant(ToyImplementation):
    """The grant check is gone. Execution no longer needs an authorization artifact."""

    name = "mutant:executes-without-a-grant"

    def _execute(self, grant_id, dataset, capability):
        return {"dataset": dataset, "capability": capability, "rows": 2}


class RefusalStillMintsAuthority(ToyImplementation):
    """A refusal reports a grant anyway."""

    name = "mutant:refusal-still-mints-authority"

    def _terminal(self, decision, reason, principal, dataset_id, descriptor,
                  capability_name, rationale=None):
        observation = super()._terminal(
            decision, reason, principal, dataset_id, descriptor, capability_name, rationale
        )
        if decision == "REFUSED":
            observation.granted = True
        return observation


class IndeterminateBecomesRefusal(ToyImplementation):
    """"Nobody answered" is recorded as "a rule said no"."""

    name = "mutant:indeterminate-becomes-refusal"

    def _terminal(self, decision, reason, principal, dataset_id, descriptor,
                  capability_name, rationale=None):
        if decision == "INDETERMINATE":
            return super()._terminal(
                "REFUSED", reason, principal, dataset_id, descriptor, capability_name
            )
        return super()._terminal(
            decision, reason, principal, dataset_id, descriptor, capability_name, rationale
        )


class DefaultAllow(ToyImplementation):
    """An unadvertised capability is treated as permitted."""

    name = "mutant:default-allow"

    def _evaluate(self, step, principal, descriptor, capability_name):
        refusal = super()._evaluate(step, principal, descriptor, capability_name)
        return None if refusal == "UNREGISTERED_CAPABILITY" else refusal


class ProhibitionsIgnored(ToyImplementation):
    """The descriptor's prohibitions are not consulted."""

    name = "mutant:prohibitions-ignored"

    def _evaluate(self, step, principal, descriptor, capability_name):
        refusal = super()._evaluate(step, principal, descriptor, capability_name)
        return None if refusal == "PROHIBITED_OPERATION" else refusal


class DescriptorNotValidated(ToyImplementation):
    """A malformed contract is accepted."""

    name = "mutant:descriptor-not-validated"

    def _evaluate(self, step, principal, descriptor, capability_name):
        refusal = super()._evaluate(step, principal, descriptor, capability_name)
        return None if refusal == "DESCRIPTOR_INVALID" else refusal


class DelegationWidensScope(ToyImplementation):
    """The boundary stops checking that the delegate's scope is narrower."""

    name = "mutant:delegation-widens-scope"

    def _op_delegate(self, step):
        observation = super()._op_delegate(step)
        if observation.errors and "widens" in observation.errors[0]:
            observation.errors = []
            calls = [f"{step['channel']}-target:{step['dataset']}.{step['capability']}"]
            observation.mcp_calls = calls if step["channel"] == "mcp" else []
            observation.a2a_calls = calls if step["channel"] == "a2a" else []
            observation.executed_scope = dict(step["scope"])
        return observation


class CacheIgnoresPrincipal(ToyImplementation):
    """The cache key drops the authorization scope: one principal's answer is
    served to another."""

    name = "mutant:cache-ignores-principal"

    def _op_request(self, step):
        observation = super()._op_request(step)
        collapsed = {}
        for key, value in self._cache.items():
            collapsed[(key[0], key[1], key[2], key[3])] = value
        self._cache = {
            (k[0], k[1], k[2], k[3], "", (), "", "", None, self._policy_version): v
            for k, v in self._cache.items()
        }
        return observation


class CacheIgnoresRevision(ToyImplementation):
    """The cache survives a change to the underlying data."""

    name = "mutant:cache-ignores-revision"

    def _op_set_revision(self, step):
        cached = dict(self._cache)
        result = super()._op_set_revision(step)
        self._cache = {
            (k[0], k[1], step["revision"], *k[3:]) if k[1] == step["dataset"] else k: v
            for k, v in cached.items()
        }
        return result


class RefusalLeavesNoEvidence(ToyImplementation):
    """A refusal is not written down."""

    name = "mutant:refusal-leaves-no-evidence"

    def _terminal(self, decision, reason, principal, dataset_id, descriptor,
                  capability_name, rationale=None):
        observation = super()._terminal(
            decision, reason, principal, dataset_id, descriptor, capability_name, rationale
        )
        if decision == "REFUSED":
            observation.evidence = []
        return observation


class EvidenceOmitsRevision(ToyImplementation):
    """Evidence cannot say which data was used."""

    name = "mutant:evidence-omits-revision"

    def _observe(self, *args, **kwargs):
        observation = super()._observe(*args, **kwargs)
        for row in observation.evidence:
            row.pop("dataset_revision", None)
        return observation


class EvidenceOmitsPolicyVersion(ToyImplementation):
    """Evidence cannot say which rules applied."""

    name = "mutant:evidence-omits-policy-version"

    def _observe(self, *args, **kwargs):
        observation = super()._observe(*args, **kwargs)
        for row in observation.evidence:
            row["policy_version"] = None
        return observation


class ExpiredTokensAccepted(ToyImplementation):
    """A token's expiry is not checked."""

    name = "mutant:expired-tokens-accepted"

    def _execute(self, grant_id, dataset, capability):
        grant = self._grants.get(grant_id)
        if grant is None:
            raise PermissionError("no approval token: execution is unreachable")
        if (dataset, capability) not in self._implemented:
            raise PermissionError(f"{dataset}.{capability} is not a registered capability")
        return {"dataset": dataset, "capability": capability, "rows": 2}


class AdvertisedMeansImplemented(ToyImplementation):
    """Every advertised capability is treated as implemented.

    This is F-011 -- the mistake the toy actually made on its first run --
    planted so it stays reproducible instead of surviving only as an anecdote.
    """

    name = "mutant:advertised-means-implemented"

    def load_world(self, world):
        super().load_world(world)
        self._derive = True

    def _op_register_descriptor(self, step):
        result = super()._op_register_descriptor(step)
        self._implemented |= {
            (step["descriptor"]["dataset"], c["name"])
            for c in step["descriptor"].get("capabilities", ())
        }
        return result


class EvidenceOmitsPrincipal(ToyImplementation):
    """Evidence cannot say who was acting."""

    name = "mutant:evidence-omits-principal"

    def _observe(self, *args, **kwargs):
        observation = super()._observe(*args, **kwargs)
        for row in observation.evidence:
            row["principal_class"] = None
        return observation


class RemoteDelegationUnchecked(ToyImplementation):
    """The MCP seam stops checking the scope. The A2A seam still does."""

    name = "mutant:remote-delegation-unchecked"
    _channel = "mcp"

    def _op_delegate(self, step):
        observation = super()._op_delegate(step)
        if step["channel"] == self._channel and observation.errors:
            observation.errors = []
            calls = [f"{step['channel']}-target:{step['dataset']}.{step['capability']}"]
            observation.mcp_calls = calls if step["channel"] == "mcp" else []
            observation.a2a_calls = calls if step["channel"] == "a2a" else []
            observation.executed_scope = dict(step["scope"])
        return observation


class HandoffUnchecked(RemoteDelegationUnchecked):
    """The agent-handoff seam stops checking the scope. The MCP seam still does."""

    name = "mutant:handoff-unchecked"
    _channel = "a2a"


# mutant class -> the assertion that must catch it
TARGETS: dict[type, str] = {
    DescriptorNotValidated: "AD-001",
    AdvertisedMeansImplemented: "AD-002",
    ExecutesWithoutAGrant: "AD-003",
    ExpiredTokensAccepted: "AD-003",
    RefusalStillMintsAuthority: "AD-004",
    IndeterminateBecomesRefusal: "AD-005",
    DefaultAllow: "AD-006",
    DelegationWidensScope: "AD-007",
    CacheIgnoresPrincipal: "AD-008",
    CacheIgnoresRevision: "AD-008",
    EvidenceOmitsPrincipal: "AD-009",
    RefusalLeavesNoEvidence: "AD-010",
    EvidenceOmitsRevision: "AD-011",
    EvidenceOmitsPolicyVersion: "AD-012",
    RemoteDelegationUnchecked: "AD-013",
    HandoffUnchecked: "AD-014",
    ProhibitionsIgnored: "AD-015",
}

MUTANTS = tuple(TARGETS)
