"""Emit the normative world and vectors as JSON.

The JSON is the artifact; this script is convenience. Output is committed, so
the suite runs without regenerating, and `pytest` asserts the committed files
match what this produces.

    python conformance/generate.py

It imports the reference implementation to build the world from its fixtures,
so it is not part of the conformance distribution -- the data it emits is.
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).parent
REPO = HERE.parent
# The normative data lives inside the distribution that ships it, so there is
# one copy rather than a repository copy and a packaged copy that can drift.
DATA = (
    REPO / "packages" / "agentic-dataset-conformance"
    / "src" / "agentic_dataset_conformance" / "data"
)

PROHIBITED = {
    "purification-batches": [
        "delete_source", "overwrite_batch_record",
        "bypass_governance", "expose_restricted_identifiers",
    ],
    "chromatography-results": ["delete_source", "bypass_governance"],
    "clinical-private": ["expose_restricted_identifiers", "materialize", "delete_source"],
}

PRINCIPALS = ["process_engineer", "analyst", "clinical_reviewer", "external_auditor"]
COMPARE = "Compare the recovery of batches B001 and B002"


def world() -> dict:
    """Descriptors and principals as data, so a foreign implementation loads the
    same fixtures rather than reconstructing them from Python."""
    from agentic_dataset.datasets import descriptor_registry, principals

    return {
        "policy_version": "2026.09.01",
        "policy_budget_s": 0.25,
        "datasets": [d.to_dict() for d in descriptor_registry().all()],
        "principals": {
            name: {
                "principal_id": p.principal_id,
                "principal_class": p.principal_class,
                "clearance": p.clearance,
                "grants": {k: sorted(v) for k, v in sorted(p.grants.items())},
            }
            for name, p in sorted(principals().items())
        },
    }


def req(principal: str, text: str = COMPARE, **kw) -> dict:
    return {"op": "request", "principal": principal, "text": text, **kw}


def vectors() -> dict[str, dict]:
    v: dict[str, dict] = {}

    v["ad-001-descriptor-valid"] = {
        "assertion": "AD-001",
        "rules_out": "a dataset participating in admission without a well-formed contract",
        "steps": [
            {"op": "register_descriptor",
             "descriptor": {"dataset": "broken-dataset", "version": "1",
                            "description": "no revision, no capabilities"}},
            req("process_engineer", "search broken", dataset="broken-dataset",
                capability="search",
                expect={"decision": "REFUSED", "reason": "DESCRIPTOR_INVALID",
                        "granted": False, "executed": False}),
        ],
    }

    v["ad-002-capability-registered"] = {
        "assertion": "AD-002",
        "rules_out": "an executable action with no capability metadata behind it",
        "capability_surface_matches_descriptors": True,
        "steps": [
            {"op": "register_descriptor", "descriptor": _phantom_descriptor()},
            {"op": "grant", "principal": "process_engineer",
             "dataset": "purification-batches", "capability": "phantom_export"},
            req("process_engineer", "export everything",
                dataset="purification-batches", capability="phantom_export",
                expect={"executed": False, "result_present": False,
                        "error_contains": "not a registered capability"}),
        ],
    }

    v["ad-003-grant-required-for-execution"] = {
        "assertion": "AD-003",
        "rules_out": "execution reachable without an authorization artifact",
        "note": "the general form is the cross-vector invariant executed => granted",
        "steps": [
            req("process_engineer",
                expect={"decision": "GRANTED", "granted": True, "executed": True}),
            req("process_engineer", grant_ttl_s=-1, text="Calculate the yield for batch B003",
                expect={"decision": "GRANTED", "executed": False,
                        "result_present": False, "error_contains": "expired"}),
        ],
    }

    v["ad-004-refusal-has-no-grant"] = {
        "assertion": "AD-004",
        "rules_out": "a refusal that still mints authority",
        "steps": [
            req("process_engineer", "delete the source", dataset="purification-batches",
                capability="delete_source", prohibited=True,
                expect={"decision": "REFUSED", "reason": "PROHIBITED_OPERATION",
                        "policy_id": "AD-POL-004", "granted": False, "executed": False}),
            req("external_auditor", dataset="purification-batches",
                capability="compare_batches",
                expect={"decision": "REFUSED", "reason": "INSUFFICIENT_PRIVILEGE",
                        "granted": False, "executed": False}),
            req("analyst", "detect outliers in recovery", dataset="purification-batches",
                capability="detect_outliers",
                expect={"decision": "REFUSED", "granted": False, "executed": False}),
            req("process_engineer", dataset="purification-batches",
                capability="compare_batches", expected_schema_version="99",
                expect={"decision": "REFUSED", "reason": "SCHEMA_VERSION_MISMATCH",
                        "granted": False, "executed": False}),
            req("process_engineer", "search chromatography runs",
                dataset="chromatography-results", capability="search", freshness=60,
                expect={"decision": "REFUSED", "reason": "FRESHNESS_UNSATISFIABLE",
                        "granted": False, "executed": False}),
        ],
    }

    v["ad-005-indeterminate-has-no-grant"] = {
        "assertion": "AD-005",
        "rules_out": "unknown authority becoming permission",
        "steps": [
            req("process_engineer", evaluator={"reachable": False, "latency_s": 0.0},
                expect={"decision": "INDETERMINATE", "reason": "EVALUATOR_UNAVAILABLE",
                        "policy_id": None, "rationale_present": True,
                        "granted": False, "executed": False}),
            req("process_engineer", evaluator={"reachable": True, "latency_s": 5.0},
                expect={"decision": "INDETERMINATE", "reason": "EVALUATOR_TIMEOUT",
                        "policy_id": None, "rationale_present": True,
                        "granted": False, "executed": False}),
        ],
    }

    v["ad-006-unknown-capability-denied"] = {
        "assertion": "AD-006",
        "rules_out": "default-allow on an unregistered tool",
        "steps": [
            req("process_engineer", "do the thing", dataset="purification-batches",
                capability=name,
                expect={"decision": "REFUSED", "reason": "UNREGISTERED_CAPABILITY",
                        "granted": False, "executed": False})
            for name in ("query_database", "exfiltrate", "search_all")
        ] + [
            req("process_engineer", "do the thing", dataset="purification-batches",
                expect={"decision": "REFUSED", "reason": "UNREGISTERED_CAPABILITY",
                        "granted": False, "executed": False}),
        ],
    }

    widened = {"principal_class": "process-engineer", "dataset": "purification-batches",
               "capabilities": ["compare_batches", "detect_outliers"],
               "max_sensitivity": "restricted"}
    same = {"principal_class": "process-engineer", "dataset": "purification-batches",
            "capabilities": ["compare_batches"], "max_sensitivity": "internal"}

    v["ad-007-authorization-scope-preserved"] = {
        "assertion": "AD-007",
        "rules_out": "scope widening between admission and execution",
        "note": "the general form is the cross-vector invariant grant_scope covers executed_scope",
        "steps": [
            req("process_engineer", expect={"decision": "GRANTED", "granted": True}),
            {"op": "delegate", "channel": "a2a", "dataset": "purification-batches",
             "capability": "compare_batches", "scope": widened,
             "expect": {"executed": False, "error_contains": "widen"}},
        ],
    }

    v["ad-008-cache-is-policy-scoped"] = {
        "assertion": "AD-008",
        "rules_out": "a cached answer crossing an authorization boundary",
        "steps": [
            req("process_engineer", expect={"cache_hit": False, "decision": "GRANTED"}),
            req("process_engineer", expect={"cache_hit": True}),
            req("analyst", expect={"cache_hit": False}),
            {"op": "set_revision", "dataset": "purification-batches", "revision": "rev-next"},
            req("process_engineer", expect={"cache_hit": False}),
            req("process_engineer", expect={"cache_hit": True}),
            {"op": "set_policy_version", "version": "2026.10.01"},
            req("process_engineer", expect={"cache_hit": False}),
            {"op": "revoke", "principal": "process_engineer", "dataset": "purification-batches"},
            req("process_engineer",
                expect={"decision": "REFUSED", "cache_hit": False, "executed": False}),
        ],
    }

    v["ad-009-provenance-complete"] = {
        "assertion": "AD-009",
        "rules_out": "a result that cannot be traced to what produced it",
        "steps": [
            req("process_engineer",
                expect={"evidence_rows": 1, "evidence_complete": True}),
            req("process_engineer", "delete the source", dataset="purification-batches",
                capability="delete_source", prohibited=True,
                expect={"evidence_rows": 1, "evidence_complete": True}),
            req("process_engineer", evaluator={"reachable": False, "latency_s": 0.0},
                expect={"evidence_rows": 1, "evidence_complete": True}),
            req("process_engineer", "search nothing", dataset="no-such-dataset",
                capability="search",
                expect={"evidence_rows": 1, "evidence_complete": True}),
        ],
    }

    v["ad-010-refusal-recorded"] = {
        "assertion": "AD-010",
        "rules_out": "a refusal that leaves no evidence",
        "steps": [
            req("process_engineer", "delete the source", dataset="purification-batches",
                capability="delete_source", prohibited=True,
                expect={"evidence_rows": 1, "evidence_decision": "REFUSED",
                        "evidence_complete": True}),
        ],
    }

    v["ad-011-dataset-revision-recorded"] = {
        "assertion": "AD-011",
        "rules_out": "evidence that cannot identify which data was used",
        "steps": [
            req("process_engineer",
                expect={"evidence_has_revision": True, "evidence_rows": 1}),
            {"op": "set_revision", "dataset": "purification-batches", "revision": "rev-audit"},
            req("process_engineer", "Calculate the yield for batch B003",
                expect={"evidence_has_revision": True, "evidence_revision": "rev-audit"}),
        ],
    }

    v["ad-012-policy-version-recorded"] = {
        "assertion": "AD-012",
        "rules_out": "evidence that cannot identify which rules applied",
        "steps": [
            req("process_engineer", expect={"evidence_policy_version": "2026.09.01"}),
            {"op": "set_policy_version", "version": "2026.10.01"},
            req("process_engineer", "Calculate the yield for batch B003",
                expect={"evidence_policy_version": "2026.10.01"}),
        ],
    }

    for assertion, channel, key in (("AD-013", "mcp", "mcp_calls"),
                                    ("AD-014", "a2a", "a2a_calls")):
        v[f"{assertion.lower()}-{channel}-preserves-scope"] = {
            "assertion": assertion,
            "rules_out": f"{channel.upper()} delegation as an escalation path",
            "steps": [
                req("process_engineer", expect={"decision": "GRANTED", "granted": True}),
                {"op": "delegate", "channel": channel, "dataset": "purification-batches",
                 "capability": "compare_batches", "scope": same,
                 "expect": {"executed": True, f"{key}_nonempty": True}},
                {"op": "delegate", "channel": channel, "dataset": "purification-batches",
                 "capability": "compare_batches", "scope": widened,
                 "expect": {"executed": False, "error_contains": "widen"}},
                {"op": "delegate", "channel": channel, "dataset": "purification-batches",
                 "capability": "detect_outliers", "scope": same, "prohibited": False,
                 "expect": {"executed": False}},
            ],
        }

    v["ad-015-prohibited-execution-rate-zero"] = {
        "assertion": "AD-015",
        "rules_out": "any prohibited action executing at all, ever",
        "rate": True,
        "steps": [
            req(principal, f"{operation} on {dataset}", dataset=dataset,
                capability=operation, prohibited=True,
                expect={"decision": "REFUSED", "granted": False, "executed": False})
            for dataset, operations in PROHIBITED.items()
            for operation in operations
            for principal in PRINCIPALS
        ],
    }
    return v


def _phantom_descriptor() -> dict:
    from agentic_dataset.datasets import descriptor_registry

    d = descriptor_registry().get("purification-batches").to_dict()
    d["capabilities"] = d["capabilities"] + [
        {"name": "phantom_export", "effect": "read", "sensitivity": "internal",
         "description": "advertised with nothing behind it", "policy": None,
         "arguments": []}
    ]
    return d


def main() -> None:
    (DATA / "worlds").mkdir(parents=True, exist_ok=True)
    (DATA / "vectors").mkdir(parents=True, exist_ok=True)
    (DATA / "worlds" / "reference.json").write_text(
        json.dumps(world(), indent=2, sort_keys=True) + "\n"
    )
    produced = vectors()
    for name, vector in produced.items():
        vector.setdefault("world", "reference")
        (DATA / "vectors" / f"{name}.json").write_text(
            json.dumps(vector, indent=2) + "\n"
        )
    steps = sum(len(v["steps"]) for v in produced.values())
    print(f"{len(produced)} vectors, {steps} steps, 1 world")


if __name__ == "__main__":
    main()
