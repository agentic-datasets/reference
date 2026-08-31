# dk-agentic-dataset-reference

**A reference implementation, conformance suite and semantic benchmark for
agentic datasets, on the LangChain stack.**

> ## Status: PLANNED. Nothing is built.
>
> This repository is a plan. There is no runnable code in it, no measured
> result, and nothing here may be cited as delivered work — not in a résumé, an
> application, a paper, or a talk. When something runs, this block says so and
> names what runs. Until then it says this.

---

## What this is

The agentic-dataset model is published: a dataset that describes itself,
advertises bounded capabilities, accepts a semantic intent, decides whether an
action is admissible, executes only what was admitted, refuses the rest, and
leaves evidence. It exists across IEEE CCECE 2026, EMBC 2026 and
BigDataService 2026, and its mechanisms exist in code — `ok-governed-motion`
implements the three-valued verdict, `dk-semantic-gateway-v2` the retrieval and
capability mesh, `dk-nfcore-admission-gate` the per-task gate.

What does *not* exist is one artifact a third party can run, point at, and
disagree with.

This repository is intended to be that artifact: **the same control plane
expressed on a mainstream stack**, so the claim stops depending on reading four
repositories in three languages.

## What it is not

**Not a LangChain demo.** The interesting object is the contract — descriptor,
capability, intent, admission, refusal, evidence, provenance. LangGraph is a
good runtime in which to demonstrate those semantics; it is not the
contribution.

**Not a new framework.** Everything structural here already exists in the
repositories above. This is a port, and its credibility comes from porting
known behaviour rather than from inventing architecture on a page.

## The stack, and why each piece

| Layer | Choice | Why |
|---|---|---|
| Orchestration | **LangGraph** | Deterministic nodes and LLM nodes in one graph; admission must be a routed edge, not a prompt |
| Integration | **LangChain** | Models, tools, structured output, middleware |
| Dataset boundary | **MCP** | A dataset exposes resources, tools and prompts; new datasets become discoverable without rewiring the agent |
| Policy | **External deterministic runtime** | Authority is not a probabilistic judgement |
| Evaluation | **LangSmith** | Trajectory evaluation and regression, not answer-only scoring |
| Evidence | **Append-oriented ledger, separate from LangGraph state** | Orchestration checkpoints and an audit record have different lifetimes and different readers |

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
authority nobody exercised. This is already implemented in Rust in
`ok-governed-motion` (`Verdict`, `IndeterminateReason`); the port must preserve
it rather than collapse to permit/deny.

## Layout

```
src/agentic_dataset/
    descriptor.py     dataset contract: schemas, capabilities, policies, provenance
    capabilities.py   bounded operations; the decorator that carries metadata
    admission.py      deterministic policy evaluation -> Verdict
    graph.py          the LangGraph state machine
    cache.py          authorization-scoped semantic cache
    provenance.py     evidence records
tests/                deterministic contract, graph-routing and capability tests
evals/                LangSmith datasets, trajectory and discovery evaluators
docs/                 architecture; see docs/ARCHITECTURE.md
```

## Related

- `ok-governed-motion` — the three-valued verdict, in Rust. IEEE CBS 2026
- `dk-semantic-gateway-v2` — retrieval, capability mesh over MCP, ontology
- `dk-nfcore-admission-gate` — the per-task gate, measured on AWS HealthOmics
- `dk-semantic-discovery-engine` — `VOLUME_SPEC`, descriptor semantics
- `dk-agentic-datasets` — topic scratchpad, not an implementation home

See [PLAN.md](PLAN.md) for milestones and the open questions.
