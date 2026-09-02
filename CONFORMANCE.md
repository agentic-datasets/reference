# Agentic Dataset Conformance Suite

**Fifteen assertions that any implementation of the agentic-dataset model must
satisfy, in any framework.**

> ## Status: IMPLEMENTED, PORTABLE, AND PASSING AGAINST NINE SUBJECTS.
>
> All fifteen are checked **through a public interface**, against four runtimes
> at two dataset boundaries *and* against an independent implementation that
> shares no code with any of them. Thirteen deliberately broken variants are
> each caught by the assertion named for them.
>
> The harness imports nothing from any implementation. The normative artifacts
> — the world, the vectors, the expectations — are JSON in `conformance/`.
>
> Run it: `agentic-dataset-conformance run --subject conformance.subjects:subjects --mutants`
>
> Source: `docs/ARCHITECTURE-ADK.md` §107, generalised.

---

## Why this file exists

Three reference architectures now describe the same control plane on
LangChain/LangGraph, LlamaIndex and Google ADK. Three documents that agree with
each other prove nothing — they were written by the same person from the same
model.

**A conformance suite is what makes the agreement checkable.** If the same
fifteen assertions pass against independent runtimes with different primitives,
the claim *"the governance model is not a property of a framework"* stops being
an argument and becomes a result.

That is the difference between a design document and a research artifact, and
it is the reason [`PLAN.md`](PLAN.md) M2 exists.

**One qualification, stated here rather than in a footnote.** The four ports in
this repository share a single `ControlPlane`. That is deliberate — an
assertion that passed because each port re-implemented its own policy would be
four experiments rather than one — but it means the result is about the model
being *expressible* in four runtimes, not about four independent
implementations agreeing. A second implementation written by someone else from
this file alone is the experiment this artifact does not run.

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

## Non-goals

**Conformance is not a security audit.** Passing AD-002 proves consistency
between declared and observable behaviour within the subject's advertised
capability surface; it does not prove that the subject has disclosed every
capability it possesses. `capabilities()` is the implementation's own report of
itself.

So a conformance pass is a claim an implementation makes about itself, made
checkable. Treating it as a guarantee against a hostile implementation misreads
it, and no interface of this shape could provide one — an adversarial audit
needs access to the binary, not to an interface the binary implements.

Three further things this suite does not attempt:

- **Performance.** Latency, throughput, cost and concurrency are unmeasured and
  unasserted.
- **Semantic quality.** Whether the right dataset was chosen, or the answer was
  any good, is measured statistically elsewhere and deliberately never averaged
  into these fifteen.
- **Completeness of the model.** The assertions rule out the failures named in
  the table above. They are not a claim that no other governance failure exists.

## Gate shape

```
                                  gate      measured
AD-001 .. AD-015                = 100%      15/15 x 9 subjects
Authorized Recall@5            >= 0.95      0.960  (filter before truncation)
                                            0.853  (filter after truncation)
Capability selection accuracy  >= 0.97      1.000
Trajectory validity            >= 0.95      1.000
Groundedness                   >= 0.93      not measured -- no model-generated
                                            answer exists in this build
```

The two Authorized Recall@5 rows are the same retriever and the same corpus,
differing only in where the authorization filter sits. **The gate is a
statement about filter placement, not about retrieval quality.**

> Governance is tested as an invariant. Semantic quality is tested
> statistically. Running the two through one number destroys both.

---

## Framework independence

The suite is implemented once and run against every runtime without changing an
assertion. What differs between them is only where control flows:

| | Native | LangGraph | LlamaIndex Workflows | Google ADK |
|---|---|---|---|---|
| Where admission routes | a function call | conditional edge | typed event dispatch | graph node + before-tool callback |
| Where AD-006 is enforced | capability wrapper | capability wrapper | capability wrapper | wrapper + `before_tool_callback` |
| Where AD-013 applies | `DelegatedExecutor` | `DelegatedExecutor` | `DelegatedExecutor` | `DelegatedExecutor` / `FunctionTool` |
| Where AD-008 is checked | cache key | cache key | cache key | cache key |
| Result | 15/15 | 15/15 | 15/15 | 15/15 |

Each of those is run twice: once against local capabilities, and once with
every dataset behind a real MCP client session. That second axis earned its
place — two of the six defects in [`docs/FINDINGS.md`](docs/FINDINGS.md) were
visible only across the boundary, and two only under the async runtimes.

**If an assertion cannot be expressed in one of the runtimes, that is a finding
about the assertion, not about the framework.** None had to be dropped;
`docs/FINDINGS.md` records the two places where the implementation departed
from the architecture documents instead.

### How to be tested

An implementation is conformance-testable when it exposes four things
(`packages/agentic-dataset-conformance/src/agentic_dataset_conformance/interface.py`):

```
load_world(world)      adopt descriptors, principals and a policy version
capabilities()         report every operation it will actually execute
step(step)             run one control verb, return an Observation
reset()                forget cache and evidence
```

`Observation` is the entire observable surface — decision, reason, policy id,
whether a grant exists, the admitted and executed scopes, tool/MCP/A2A call
lists, cache hit, evidence rows, errors. **If a property cannot be established
from an Observation, a world and a sequence of steps, it is not part of the
portable contract.**

The control verbs are in `verbs.md` beside the interface. The worlds and
vectors are JSON under `conformance/`, so an implementation in Rust, Go,
TypeScript or Java can be checked without reproducing Python object semantics —
Python is one runner, not the specification.

`packages/agentic-dataset-conformance/src/agentic_dataset_conformance/toy.py` is a 250-line worked example that imports
the interface and nothing else, and passes all fifteen.

`docs/PORTABILITY.md` records the three assertions whose shape changed when
they moved outside, the one property that was deliberately widened, and the one
that cannot be checked from outside at all.

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
have a passing implementation, in a language none of these ports use.**

`tests/test_verdict_parity.py` closes that loop: it asserts the Python strings
and rationales against the literals above, and reads `policy.rs` directly when
`ok-governed-motion` is checked out beside this repository. The Rust and Python
verdicts cannot drift without a test failing.
