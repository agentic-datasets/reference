# Control verbs

A vector is a world plus a sequence of steps. Every step is one of these, and
an implementation that supports all of them is conformance-testable.

| `op` | fields | meaning |
|---|---|---|
| `request` | `principal`, `text`, `dataset?`, `capability?`, `freshness?`, `expected_schema_version?`, `evaluator?`, `grant_ttl_s?` | The ordinary path: interpret, admit, maybe execute. Returns an `Observation`. |
| `delegate` | `channel` (`mcp`\|`a2a`), `dataset`, `capability`, `scope` | Execute across a boundary using the grant from the previous `request`. Returns an `Observation` whose `mcp_calls`/`a2a_calls` say whether it crossed. |
| `grant` | `principal`, `dataset`, `capability` | Add a capability to a principal's standing entitlement. |
| `revoke` | `principal`, `dataset` | Remove a principal's standing entitlement on a dataset. |
| `set_revision` | `dataset`, `revision` | The dataset's data changed underneath. |
| `set_policy_version` | `version` | The rules changed. |
| `register_descriptor` | `descriptor` | Add or replace a descriptor, including a malformed one. |
| `reset` | — | Forget cache and evidence. |

`evaluator` is `{"reachable": bool, "latency_s": number}` and is how a vector
makes the policy authority unavailable or slow without the harness knowing how
the authority is implemented.

## Expectations

Each step may carry `expect`, checked against the returned `Observation`:

| key | meaning |
|---|---|
| `decision` | exactly `GRANTED`, `REFUSED` or `INDETERMINATE` |
| `reason` | the serialised reason string |
| `policy_id` | the rule that decided, or `null` — and `null` is asserted, not skipped |
| `rationale_present` | a non-empty rationale exists |
| `granted` | an authorization artifact exists |
| `executed` | any tool, MCP or A2A call happened |
| `cache_hit` | the answer was reused |
| `result_present` | a result was produced |
| `dataset`, `capability` | what was selected |
| `evidence_rows` | how many evidence records this step produced |
| `evidence_complete` | every record carries the required fields |
| `evidence_decision` | the decision recorded in evidence matches |
| `evidence_has_revision` | the record identifies which data was used |
| `evidence_policy_version` | the record identifies which rules applied |
| `error_contains` | a substring of a reported error |

A step tagged `"prohibited": true` contributes to the AD-015 rate.
