# agentic-dataset-reference

**A reference implementation, conformance suite and semantic benchmark for
agentic datasets — the same control plane expressed on four runtimes.**

> ## Status: RUNS.
>
> `python -m agentic_dataset.conformance` executes AD-001 … AD-015 against
> four runtimes at two dataset boundaries and passes 15/15 in all eight
> configurations. `pytest` is 234 tests. Milestone M6 has produced a number.
>
> What is *not* here is equally short: no deployment, no real data, no model in
> the loop by default, no latency or cost claim. See
> [`docs/RESULTS.md`](docs/RESULTS.md) §5.

---

## What this is

The agentic-dataset model is published: a dataset that describes itself,
advertises bounded capabilities, accepts a semantic intent, decides whether an
action is admissible, executes only what was admitted, refuses the rest, and
leaves evidence. It exists across IEEE CCECE 2026, EMBC 2026 and
BigDataService 2026, and its mechanisms exist in code — `ok-governed-motion`
implements the three-valued verdict, `dk-semantic-gateway-v2` the retrieval and
capability mesh, `dk-nfcore-admission-gate` the per-task gate.

What did not exist was one artifact a third party can run, point at, and
disagree with. This is that artifact.

## The claim, and how it is tested

> **The governance model is not a property of a framework.**

Three architecture documents that agree with each other prove nothing — they
were written by one person from one model. So the fifteen assertions in
[`CONFORMANCE.md`](CONFORMANCE.md) are implemented once and run against every
runtime:

```
RUNTIME           RESULT  PASSED        Where admission routes
native+local      PASS    15/15         a function call
langgraph+local   PASS    15/15         a conditional edge
llamaindex+local  PASS    15/15         typed event dispatch
adk+local         PASS    15/15         a graph node + before-tool callback
native+mcp        PASS    15/15         (each of the four again, with every
langgraph+mcp     PASS    15/15          dataset behind a real MCP session)
llamaindex+mcp    PASS    15/15
adk+mcp           PASS    15/15

AD-015 prohibited execution rate: 0.000 (target exactly 0)
```

The four ports share one `ControlPlane`, deliberately: an assertion that passed
because each port re-implemented its own policy would be four experiments, not
one. What the matrix shows is that the model is *expressible* in four runtimes
with different primitives — not that four independent implementations agree.
[`docs/RESULTS.md`](docs/RESULTS.md) §1 states both halves.

The suite failed on this implementation five times before it passed, twice only
in the MCP configuration and twice only under the async runtimes. Those are
written down in [`docs/FINDINGS.md`](docs/FINDINGS.md).

## The load-bearing idea

    The LLM may interpret, propose, rank and explain.
    The control plane decides whether execution is allowed.

Admission returns one of three verdicts, and **only an approval mints the token
that permits execution**:

```
GRANTED        -> approval token -> execution reachable
REFUSED        -> no token       -> execution unreachable
INDETERMINATE  -> no token       -> execution unreachable
```

`INDETERMINATE` is not a refusal. An evaluator that is unreachable or out of
budget has not decided anything, and recording that as a refusal invents an
authority nobody exercised. The two serialised reasons —
`EVALUATOR_UNAVAILABLE`, `EVALUATOR_TIMEOUT` — and their rationales are copied
from `ok-governed-motion`'s `policy.rs`, and
`tests/test_verdict_parity.py` reads that file to check they have not drifted.

## Quickstart

```bash
pip install -e ".[all]"                      # or ".[dev]" for the core alone

python -m agentic_dataset.conformance        # AD-001..AD-015, every runtime
python -m agentic_dataset.conformance --json # machine-readable
python -m agentic_dataset.conformance --local   # skip the MCP boundary
pytest -q                                    # 234 tests

python evals/authorized_recall.py            # milestone M6, the metric
python evals/evaluate.py                     # milestone M5, six evaluators
python evals/corpus.py                       # regenerate the eval corpus
```

The conformance runner exits non-zero on any failure, so it works as a CI gate.
Runtimes whose framework is not installed are reported as skipped rather than
quietly omitted — a suite that shrinks silently is a suite that always passes.

A minimal run:

```python
from agentic_dataset.adapters import NativeRuntime
from agentic_dataset.datasets import build_control_plane, principals
from agentic_dataset.runtime import Request

runtime = NativeRuntime(build_control_plane())
result = runtime.run(Request(
    text="Compare the recovery of batches B001 and B002",
    principal=principals()["process_engineer"],
))
print(result.decision, result.reason, result.result)
# GRANTED PRINCIPAL_AUTHORIZED {'batch_ids': ['B001', 'B002'], ...}

refused = runtime.run(Request(
    text="Delete the source records",
    principal=principals()["process_engineer"],
    dataset="purification-batches", capability="delete_source",
))
print(refused.decision, refused.grant, refused.execution.tool_calls)
# REFUSED None []
```

The second example is the one that matters. The test is not that a refusal
message was produced; it is that **after a refusal there was no capability to
execute with**.

## The stack, and why each piece

| Layer | Choice | Why |
|---|---|---|
| Core control plane | **No dependencies** | If the governance model needed a framework, the claim above would be false. Everything in `src/agentic_dataset/` outside `adapters/` and `mcp_boundary.py` is standard library |
| Orchestration | **LangGraph** · **LlamaIndex Workflows** · **Google ADK** | Three mainstream runtimes with different primitives. Admission must be a routed edge, a typed event or a callback — never a prompt |
| Dataset boundary | **MCP** | A dataset exposes descriptor, schema, lineage and policy as resources and its capabilities as tools; new datasets become discoverable without rewiring anything |
| Policy | **Deterministic evaluator, in code** | Authority is not a probabilistic judgement. Swapping in Cedar or OPA changes one class and no assertion |
| Evidence | **Hash-chained append-only ledger, separate from runtime state** | Orchestration checkpoints and an audit record have different lifetimes and different readers |

## Layout

```
src/agentic_dataset/
    verdict.py        the three-valued verdict, ported from ok-governed-motion
    descriptor.py     dataset contract: schemas, capabilities, prohibitions, provenance
    principal.py      principals and authorization scopes
    intent.py         natural language -> structured intent (rule-based or LLM)
    admission.py      deterministic policy evaluation -> Verdict
    grant.py          the approval token: minting, expiry, HMAC verification
    capabilities.py   bounded operations; the wrapper nothing gets past
    cache.py          authorization-scoped semantic cache
    discovery.py      policy-aware discovery and Authorized Recall@K
    delegation.py     the MCP and A2A seams (AD-013, AD-014)
    provenance.py     evidence records
    ledger.py         hash-chained append-only ledger
    runtime.py        the control plane: nodes, state, RunResult
    mcp_boundary.py   a dataset behind MCP, and the client that consumes it
    adapters/         native · langgraph · llamaindex · adk
    conformance/      AD-001..AD-015, implemented once
    datasets/         the synthetic reference dataset family
tests/                234 tests
evals/                the corpus, the M5 evaluators, the M6 measurement
docs/                 architecture (three ports), results, findings
```

## Documents

- [`CONFORMANCE.md`](CONFORMANCE.md) — **AD-001 … AD-015**, the fifteen
  assertions any implementation must satisfy in any framework.
- [`docs/RESULTS.md`](docs/RESULTS.md) — what was measured, with the caveats
  attached to each number.
- [`docs/FINDINGS.md`](docs/FINDINGS.md) — where the implementation disagreed
  with the architecture, and the six defects the suite found.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — LangChain / LangGraph / MCP
  / LangSmith. Design, written before the code.
- [`docs/ARCHITECTURE-LLAMAINDEX.md`](docs/ARCHITECTURE-LLAMAINDEX.md) —
  LlamaIndex Workflows variant.
- [`docs/ARCHITECTURE-ADK.md`](docs/ARCHITECTURE-ADK.md) — Google ADK variant.
- [`PLAN.md`](PLAN.md) — milestones M1–M6 and the open questions, with the
  answers that were taken.

The three architecture documents are **design, and predate the
implementation**. Where the code disagrees with them, `docs/FINDINGS.md` says
so and says why; they have not been retrofitted to match.

## Related

- `ok-governed-motion` — the three-valued verdict, in Rust. IEEE CBS 2026
- `dk-semantic-gateway-v2` — retrieval, capability mesh over MCP, ontology
- `dk-nfcore-admission-gate` — the per-task gate, measured on AWS HealthOmics
- `dk-semantic-discovery-engine` — `VOLUME_SPEC`, descriptor semantics
