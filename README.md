# agentic-dataset-reference

**One governance contract. Four agent runtimes. Two dataset boundaries.**

```
15 conformance assertions x 8 configurations = 120 assertion-runs, all passed

  0 / 576   prohibited executions, conformance matrix
  0 /  24   prohibited executions, evaluation
    247     tests passed

Authorized Recall@5
  filter after truncation     0.853
  filter before truncation    0.960
                             +0.107   -- plain Recall@5 stays at 0.867
                                         and cannot see the difference
```

Measured across a framework-free reference runtime, LangGraph, LlamaIndex
Workflows and Google ADK, each over local and MCP dataset boundaries.
Reproduce it with `python -m agentic_dataset.conformance`; the raw output is in
[`docs/runs/`](docs/runs/) and the caveats on every number are in
[`docs/RESULTS.md`](docs/RESULTS.md).

The two prohibited-execution denominators are kept apart on purpose. They come
from different experiments — the conformance matrix and the evaluation set —
and adding them into one 0/600 would merge two populations that were never
sampled together.

> ## Status: runs, and is not finished.
>
> No deployment, no real data, no model in the loop by default, no latency or
> cost claim. And the conformance suite is **not yet portable**: only 2 of the
> 15 assertions are checked through the public interface, so it cannot today be
> pointed at somebody else's implementation. See
> [`CONTRIBUTING.md`](CONTRIBUTING.md).

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

### Independent conformance implementations wanted

The gap above is the interesting one, and it cannot be closed from inside this
repository. An implementation written by someone else from
[`CONFORMANCE.md`](CONFORMANCE.md) alone, in any language, **without using this
reference `ControlPlane`**, would test whether the specification is complete
enough to be implemented twice and whether two implementations agree on the
governance semantics.

Two honest cautions before anyone tries. Only **AD-004 and AD-005** are
currently checked through the public `Runtime` interface; the other thirteen
reach into this implementation's internals, so the harness cannot yet be
pointed at a foreign implementation. And a finding that an assertion is
ambiguous is a more useful result than a passing run.
[`CONTRIBUTING.md`](CONTRIBUTING.md) says what would have to exist to make the
suite portable.

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
pytest -q                                    # 247 tests

python -m agentic_dataset.authorized_recall  # milestone M6, the metric
python evals/evaluate.py                     # milestone M5, six evaluators
python -m agentic_dataset.authorized_recall.corpus   # regenerate the corpus
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
    authorized_recall/  the metric, standalone: no dependency on any of the above
    datasets/         the synthetic reference dataset family
examples/             one runnable script per runtime, plus the MCP boundary
tests/                247 tests
evals/                the M5 evaluators and the committed corpus record
docs/                 architecture (three ports), results, findings, raw runs
```

## Documents

- [`CONFORMANCE.md`](CONFORMANCE.md) — **AD-001 … AD-015**, the fifteen
  assertions any implementation must satisfy in any framework. This is the
  specification; everything else in the repository is one worked example of it.
- [`src/agentic_dataset/authorized_recall/README.md`](src/agentic_dataset/authorized_recall/README.md)
  — Authorized Recall@K: the definition, the two conventions, and the proof
  that the pre/post-filter gap is non-negative. The package has no dependency
  on the control plane, so the metric can be used without adopting any of this.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — what an independent implementation
  would need, and what is missing before the suite can check one.
- [`RELEASE.md`](RELEASE.md) — what has to change together before this is
  published.
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
