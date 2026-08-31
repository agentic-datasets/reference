# Agentic Datasets on the LangChain Stack

**Reference architecture for governed, testable, observable agentic data
services.**

> ## Status: DRAFT ARCHITECTURE. Design, not deployment.
>
> Nothing described here has been built or run. This is the same discipline as
> `dk-job-applications/AWS-REFERENCE-DESIGNS.md`, which states it on its first
> page for the same reason: a design argued on a page inherits none of the
> constraints a running system would have imposed.
>
> **What makes it credible anyway** is that it is a *port*. The three-valued
> verdict, the approval token, capability-over-generic-tools, policy-aware
> discovery and the authorization-scoped cache key are not proposals — they
> exist in `ok-governed-motion`, `dk-semantic-gateway-v2` and
> `dk-nfcore-admission-gate`. This document expresses known behaviour in a
> mainstream stack. It does not invent architecture.
>
> **Import note.** Reconstructed 2026-08-31 from the source design document.
> The source was truncated in transit partway through §19; sections from there
> to the end — cache security invariants in full, persistence semantics,
> deployment, security posture and the reference repository layout — are
> summarised from the accompanying discussion rather than transcribed, and are
> marked. Reconcile against the original when it is to hand.

---

## 1. Summary

An agentic dataset is more than a data source exposed to an LLM. It is a
governed runtime object that can describe itself, advertise bounded
capabilities, accept semantic intents, determine whether an action is
admissible, execute approved operations, refuse prohibited ones, preserve
provenance, and expose evidence about every consequential decision.

The stack:

| Layer | Role |
|---|---|
| **LangChain** | Models, tools, structured output, middleware, retrievers, integration |
| **LangGraph** | Explicit state-machine orchestration; deterministic and agentic nodes in one graph |
| **MCP** | The dataset boundary — resources, tools, prompts |
| **LangSmith** | Tracing, offline evaluation, regression, production evaluation |
| **External policy runtime** | Deterministic authorization and admission |
| **Evidence ledger** | Durable, append-oriented record of intent, decision, execution, refusal, provenance |
| **Semantic discovery and cache** | Policy-aware dataset selection and safe reuse |

The governing principle:

> The LLM may interpret, propose, rank and explain.
> The control plane decides whether execution is allowed.

That separates **intelligence** from **authority**.

## 2. Goals

**2.1 Semantic discovery.** Agents find datasets by meaning, not by hard-coded
source names. *"Why did recovery drop after the polishing step?"* should resolve
to candidate datasets without the caller knowing their identifiers.

**2.2 Bounded capabilities.** A dataset exposes operations — `search`,
`retrieve`, `sample`, `aggregate`, `compare_batches`, `calculate_yield`,
`detect_outliers`, `materialize` — not credentials to S3, SQL or internal APIs.

**2.3 Deterministic admission.** Every consequential operation is evaluated
before execution, returning exactly one of `GRANTED`, `REFUSED`,
`INDETERMINATE`. **No approval token is minted for the latter two.**

`INDETERMINATE` is distinct from refusal: the evaluator was unavailable, an
input was missing, authorization timed out, the descriptor was incomplete, or
the requested history could not be established.

**2.4 Provenance and evidence.** What was requested, which dataset and
capability were selected, which policy version was evaluated, the decision and
its reason, what executed, which data revision, whether a cached result was
reused, what was returned, and the trace identifiers.

**2.5 Testability.** Discovery, capability selection, policy decisions,
refusal, indeterminacy, graph transitions, execution, prohibited execution,
cache isolation, provenance, grounding, trajectories, latency, cost, and
regression across models and prompts.

## 3. High-level architecture

```
                     USER / APPLICATION / AGENT
                                │
                                ▼
                     Natural-language request
                                │
                                ▼
                    ┌─────────────────────────┐
                    │   LANGCHAIN INTERFACE   │
                    │   models / tools / I/O  │
                    └────────────┬────────────┘
                                 ▼
                    ┌─────────────────────────┐
                    │        LANGGRAPH        │
                    │  semantic control plane │
                    └────────────┬────────────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          ▼                      ▼                      ▼
   Dataset discovery      Admission / policy        Planning
          │                      │                      │
          │            GRANTED / REFUSED /              │
          │              INDETERMINATE                  │
          └──────────────────────┼──────────────────────┘
                                 ▼
                       Capability resolution
                                 ▼
                        Semantic cache lookup
                     ┌───────────┴───────────┐
                    HIT                     MISS
                     │                       ▼
                     │                  MCP / tools
                     │                 S3 / SQL / API
                     └───────────┬───────────┘
                                 ▼
                          Result validation
                                 ▼
                        Provenance / evidence
                  ┌──────────────┼──────────────┐
                  ▼              ▼              ▼
           Evidence ledger   LangSmith     Application
```

## 4. The dataset abstraction

```python
class DatasetCapability(BaseModel):
    name: str
    description: str
    effect: str                       # read | compute | write
    sensitivity: str | None = None
    required_policy: str | None = None

class DatasetDescriptor(BaseModel):
    dataset_id: str
    version: str
    description: str
    schemas: list[str]
    capabilities: list[DatasetCapability]
    provenance: dict
    policies: list[str]
    freshness: str | None = None
    quality_contract: dict = {}
    retention_contract: dict = {}
    endpoints: dict = {}
```

The descriptor is not documentation. It participates directly in admission and
execution. A serialised example carries `capabilities`, an explicit
`prohibited` list (`delete_source`, `overwrite_batch_record`,
`expose_restricted_identifiers`), `freshness`, `retention` and `provenance`.

**The interesting property is `capabilities`.** The agent discovers what a
dataset *knows* and what it *permits*, rather than discovering chunks.

## 5. Dataset intent

The first transformation is natural language → structured intent: objective,
operation, candidate dataset, required capability, filters, freshness and
temporal requirements, requested output. An LLM is appropriate here, because
the task is semantic interpretation. The output is structured and validated
**before** it enters the control plane.

## 6. LangChain's responsibilities — and its limits

Use it for: model abstraction, structured output, tool definition and schemas,
retrievers, embeddings, middleware, MCP integration, prompt construction,
response synthesis.

**Do not** make it the source of truth for: authorization, policy evaluation,
retention enforcement, schema compatibility, execution authority, audit
records. Those stay deterministic.

## 7. LangGraph as the control plane

```
START → interpret → discover → resolve → admit
                                          │
              ┌───────────────────────────┼───────────────────────────┐
              ▼                           ▼                           ▼
           GRANTED                     REFUSED                 INDETERMINATE
              │                           │                           │
            cache                  record refusal            record evidence
              │                           ▼                           ▼
       hit ───┴─── miss                  END                         END
        │           ▼
        │         plan → execute
        └──────────┬──────┘
                   ▼
              validate → record evidence → synthesize → END
```

Routing is conditional on the verdict, evaluated deterministically:

```python
graph.add_conditional_edges(
    "admit", admission_route,
    {"granted": "cache", "refused": "refuse", "indeterminate": "indeterminate"},
)
```

This is preferable to hiding policy inside an unconstrained ReAct loop.
**Policy admission must not be a prompt.**

## 8. Graph state

Conversation history is not system state. The envelope carries `request_id`,
`trace_id`, `principal`, `intent`, candidate and selected dataset, `capability`,
`policy_decision`, `authorization_token`, `plan`, `observations`,
`called_tools`, `cache_result`, `result`, `provenance`, `errors`.

Messages are one field among many.

## 9. Intelligence versus authority

| Function | LLM? |
|---|---|
| Interpret natural-language intent | Yes |
| Rank candidate datasets | Yes |
| Semantic retrieval | Yes |
| Suggest a query strategy | Yes |
| Explain results, summarise evidence | Yes |
| Determine access rights | **No** |
| Validate schema constraints | **No** |
| Validate retention constraints | **No** |
| Enforce allowed operations | **No** |
| Mint execution authorization | **No** |
| Write authoritative provenance | **No** |

`LLM proposes → control plane decides → runtime executes`, never
`LLM decides and executes`.

## 10. Admission

A deterministic function over principal, intent, descriptor, capability,
environment and policy version, returning a verdict, a reason, a policy id and
evidence. Examples: `GRANTED / PRINCIPAL_AUTHORIZED`,
`REFUSED / INSUFFICIENT_PRIVILEGE`, `INDETERMINATE / EVALUATOR_TIMEOUT`.

**An unavailable evaluator must not be recorded as a refusal.** No policy made
that decision.

> Already implemented, in Rust: `ok-governed-motion` defines
> `Verdict::{Approved, Refused, Indeterminate}` and
> `IndeterminateReason::{EvaluatorUnavailable, EvaluatorTimeout}`, serialised as
> `EVALUATOR_UNAVAILABLE` / `EVALUATOR_TIMEOUT`. The port must preserve those
> exact strings — see PLAN.md, open question 1.

## 11. The authorization token

```
GRANTED       → approval token
REFUSED       → no token
INDETERMINATE → no token
```

Execution accepts `(capability, authorization, arguments)`. **No token, no
execution.** This makes refusal structural rather than conversational — and it
is the same mechanism as *"only an approval yields the token that starts
motion"* in the robotics control plane.

## 12. Capabilities, not generic tools

A raw `query_database(sql)` tool is too permissive. A capability carries
metadata the LLM never sees:

```python
@dataset_capability(
    dataset="purification", operation="compare_batches",
    effect="read", sensitivity="internal", policy="BPD-DATA-014",
)
async def compare_batches(batch_a: str, batch_b: str) -> Comparison: ...
```

The model sees `compare_batches(batch_a, batch_b)`. The runtime knows the
dataset, effect, classification and policy. Every invocation therefore runs
`resolve metadata → verify authorization → execute → validate → record
provenance`.

## 13. MCP as the dataset boundary

Each dataset exposes resources (descriptor, schema, lineage, quality, policy
metadata), tools (its capabilities) and prompts (usage guidance). The control
plane consumes them, so a newly registered dataset becomes discoverable through
its descriptor without rewiring the agent.

## 14–15. Discovery, and policy-aware discovery

Do not hand a model 200 tools. Instead:

```
request → semantic discovery → 10 candidates → policy filtering
        → 3 accessible → capability matching → 5 operations → LLM
```

Retrieval quality alone is insufficient. If discovery surfaces a dataset the
principal cannot use, it has not helped, and standard `Recall@K` scores that as
success. Hence **Authorized Recall@K**:

> How effectively does the control plane expose the semantically relevant
> subset of datasets the principal is actually permitted to use?

**This metric is new and is measured nowhere.** Do not cite it until it has a
number — see PLAN.md M6.

## 16–17. Planning and execution

Planning happens *after* admissibility is established, and every proposed
operation must map to an admitted capability: **the planner may not invent
authority.** Execution goes through an adapter layer (S3, SQL, REST, files,
streams, warehouses, vector stores) receiving dataset, revision, capability,
validated arguments, token and trace id. Infrastructure stays hidden from the
agent.

## 18. Semantic cache

Placed **after** authorization and **before** expensive execution. The key is
not `embedding(question)`. It is:

```
semantic intent + dataset + dataset revision + capability
+ authorization scope + principal class + schema version
+ freshness requirement + policy version
```

**A semantic cache whose lookup is not authorization-aware is a policy bypass
with good latency.**

## 19. Cache security invariants

> *Source truncated here. Reconstructed from the accompanying discussion.*

Required tests: semantically equivalent query → **HIT**; different dataset
revision → **MISS**; different authorization scope → **MISS**; different
freshness requirement → **MISS**; same question after access revoked → **MUST
NOT HIT**; same intent, different principal class → **must not leak**.

## 20. Persistence has two meanings

> *Reconstructed.*

LangGraph's **checkpointer** holds workflow execution state — current node,
messages, observations, intermediate results — and is for orchestration and
recovery.

The **evidence ledger** holds intent, admission decision, refusal, policy
version, dataset version, provenance, action, result metadata and trace id. It
is the regulatory record.

**Do not use LangGraph's store as the audit record.** Keep the ledger external
and append-oriented; put immutable identifiers into graph state.

## 21. Testing as a fourth plane

> *Reconstructed.*

Five layers, ordered by how early they catch a defect:

1. **Deterministic contract tests** — no LLM, no judge, no tolerance. The
   critical assertion is not that a refusal message appeared but that
   **execution was unreachable after refusal**.
2. **Graph tests** — every admission arm, parametrised; and the negative paths:
   indeterminate must not fall through, timeout yields indeterminate not
   refusal, missing descriptor and schema mismatch and expired token each
   prevent execution.
3. **Capability tests** — metadata, selection, arguments, authorization,
   invocation, output validation, provenance; plus the adversarial one: the
   model cannot reach a raw tool that bypasses the wrapper.
4. **Trajectory evaluation** — an agent that answers correctly *after querying
   three prohibited datasets* passes output evaluation and fails trajectory
   evaluation. The latter is what matters here.
5. **LangSmith datasets** — admission, discovery, adversarial; canonical corpus
   for regression across prompt, model, graph, retriever and tool changes.

**Evaluators separated by concern**, not one judge: dataset selection,
capability selection, policy decision, prohibited tool calls, trajectory
validity, grounding, provenance completeness, citation correctness, result
correctness, latency, cache behaviour. Deterministic wherever the property is
mechanical — never ask a judge whether access was allowed, because that is a
fact already known.

**Repetitions** for the probabilistic half, so results carry a spread rather
than a single figure.

## 22. CI/CD

> *Reconstructed.*

**Every commit** — descriptor, policy, graph routing, capability, provenance and
cache-isolation tests, plus a small smoke evaluation. Seconds to minutes.

**Pull request / release** — full regression experiment: representative intents,
repetitions, trajectory evaluation, retrieval metrics, grounding, admission,
cache correctness, latency, token and cost.

Gate shape, and the distinction is fundamental:

```
Control-plane invariants        = 100%   (policy, prohibited execution, provenance)
Probabilistic quality           ≥ threshold
Latency / token regression      ≤ budget
```

## 23. Production closes the loop

> *Reconstructed.*

Production traces → online evaluators → an unusual or failed run → added to the
dataset → offline regression → implementation → deployment. Unusual
interactions become executable test cases, which is particularly appropriate
for an agentic dataset.

---

## What the claim becomes

Not *"a dataset exposes tools to an agent"*, but:

> An agentic dataset exposes a bounded, testable capability surface whose
> discovery, admission, execution, refusal, provenance and semantic behaviour
> can be independently evaluated.

**Testable** is the load-bearing word. It turns `GRANTED / REFUSED /
INDETERMINATE`, provenance, capability selection, discovery and caching from
architectural concepts into measurable properties.
