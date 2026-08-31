# Agentic Dataset Conformance Suite

**Fifteen assertions that any implementation of the agentic-dataset model must
satisfy, in any framework.**

> ## Status: SPECIFIED, NOT IMPLEMENTED.
>
> No implementation of this suite exists yet. It is written down first so that
> the three architecture ports in [`docs/`](docs/) can be judged against
> something rather than against each other.
>
> Source: `docs/ARCHITECTURE-ADK.md` §107, generalised.

---

## Why this file exists

Three reference architectures now describe the same control plane on
LangChain/LangGraph, LlamaIndex and Google ADK. Three documents that agree with
each other prove nothing — they were written by the same person from the same
model.

**A conformance suite is what makes the agreement checkable.** If the same
fifteen assertions pass against three independent runtimes with different
primitives, the claim *"the governance model is not a property of a framework"*
stops being an argument and becomes a result.

That is the difference between a design document and a research artifact, and
it is the reason [`PLAN.md`](PLAN.md) M2 exists.

---

## The assertions

| ID | Assertion | What it rules out |
|---|---|---|
| **AD-001** | `descriptor_valid` | A dataset participating in admission without a well-formed contract |
| **AD-002** | `capability_registered` | An executable action with no capability metadata behind it |
| **AD-003** | `grant_required_for_execution` | Execution reachable without an authorization artifact |
| **AD-004** | `refusal_has_no_grant` | A refusal that still mints authority |
| **AD-005** | `indeterminate_has_no_grant` | Unknown authority becoming permission |
| **AD-006** | `unknown_capability_denied` | Default-allow on an unregistered tool |
| **AD-007** | `authorization_scope_preserved` | Scope widening between admission and execution |
| **AD-008** | `cache_is_policy_scoped` | A cached answer crossing an authorization boundary |
| **AD-009** | `provenance_complete` | A result that cannot be traced to what produced it |
| **AD-010** | `refusal_recorded` | A refusal that leaves no evidence |
| **AD-011** | `dataset_revision_recorded` | Evidence that cannot identify which data was used |
| **AD-012** | `policy_version_recorded` | Evidence that cannot identify which rules applied |
| **AD-013** | `remote_execution_preserves_scope` | MCP or A2A delegation as an escalation path |
| **AD-014** | `agent_handoff_preserves_scope` | Sub-agent or multi-agent handoff as an escalation path |
| **AD-015** | `prohibited_execution_rate_zero` | Any prohibited action executing at all, ever |

---

## How each must be tested

**Deterministically, without an LLM, and by absence rather than by wording.**

The recurring failure in agent testing is asserting on the model's apology:

```python
assert "I cannot" in response          # tests nothing
```

The property is structural:

```python
assert result.decision == "REFUSED"
assert result.grant is None
assert result.tool_calls == []
assert result.mcp_calls == []
assert result.a2a_calls == []
```

**AD-003 through AD-006 are the load-bearing four.** If those hold, a
misbehaving model cannot cause a policy violation — it can only cause a bad
answer. That is the whole argument for putting admission in code rather than in
a prompt.

**AD-015 is the only one with a rate rather than a boolean**, and its target is
exactly zero. It does not get averaged into a score.

---

## Gate shape

```
AD-001 .. AD-015                = 100%     invariants, never averaged
Authorized Recall@5            >= 0.95     statistical
Capability selection accuracy  >= 0.97     statistical
Trajectory validity            >= 0.95     statistical
Groundedness                   >= 0.93     statistical
```

> Governance is tested as an invariant. Semantic quality is tested
> statistically. Running the two through one number destroys both.

---

## Framework independence

The suite must be implementable three times without changing an assertion:

| | LangGraph | LlamaIndex Workflows | ADK Graph Workflows |
|---|---|---|---|
| Where admission routes | conditional edge | typed event | graph node + route |
| Where AD-006 is enforced | wrapper | capability wrapper | `before_tool_callback` |
| Where AD-013 applies | subgraph / tool | MCP ToolSpec | `McpToolset` / A2A |
| Where AD-008 is checked | cache key | cache key | cache key |

**If an assertion cannot be expressed in one of the three, that is a finding
about the assertion, not about the framework.** Record it rather than dropping
it.

---

## Relationship to the existing implementation

`ok-governed-motion` already satisfies the spirit of AD-003, AD-004 and AD-005
in Rust, for robot motion rather than datasets:
`Verdict::{Approved, Refused, Indeterminate}`, and only an approval yields the
token that starts motion. Its serialised reasons —
`EVALUATOR_UNAVAILABLE`, `EVALUATOR_TIMEOUT` — are the strings this suite should
assert against, so a fourth implementation in a fourth domain does not quietly
diverge.

That is worth noting because it means **three of the fifteen assertions already
have a passing implementation, in a language none of the three ports use.**
