# Contributing

The most valuable contribution to this repository is not a pull request.

## Wanted: an independent conformance implementation

The four runtime ports here share one reference `ControlPlane`. That is
deliberate — an assertion that passed because each port re-implemented its own
policy would be four experiments rather than one — but it caps what the result
can claim. Today the matrix shows that **one governance model is expressible in
four runtimes**. It does not show that **independent implementations agree on
the governance semantics**, which is the stronger and more interesting claim.

Closing that gap needs someone else's implementation, written from
[`CONFORMANCE.md`](CONFORMANCE.md), in any language, that does not use this
reference control plane. Publishing whether it passes — and especially which
assertions turned out to be ambiguous, under-specified or unimplementable —
is more useful to this project than any amount of code review.

If you do this, please open an issue. A finding that AD-007 is ambiguous is a
better outcome than a green tick.

### How to do it

1. Implement `ConformanceSubject` — four methods, in
   [`interface.py`](src/agentic_dataset/conformance/interface.py). The control
   verbs are in `verbs.md` beside it.
2. Register it in [`conformance/subjects.py`](conformance/subjects.py).
3. `python -m agentic_dataset.conformance`.

The world and the vectors are JSON under [`conformance/`](conformance/), so an
implementation in another language needs a runner for that JSON rather than a
reimplementation of this harness. `conformance/toy_implementation.py` is a
250-line worked example that imports the interface and nothing else.

### What is honest about the current state

The toy is independent of the reference implementation but **not of its
author**. One person's reading of their own specification is the weakest kind
of independence, and it is the reason this section exists. A second reading is
the experiment.

[`docs/PORTABILITY.md`](docs/PORTABILITY.md) records where the contract had to
change shape to leave the building — AD-003 and AD-007 became universally
quantified invariants, AD-008 became behavioural rather than structural — and
the one thing conformance cannot establish at all: a subject that under-reports
its own capabilities passes AD-002 while hiding a tool. Conformance here is a
claim an implementation makes about itself, made checkable. It is not an
adversarial audit.

## Other contributions that would help

- **A harder discovery corpus.** MRR is 1.000 on the current one, so the
  retrieval task is easy and the Authorized Recall numbers are measured in easy
  conditions.
- **Authorized Recall@K applied to a real corpus** with real authorization
  data. `agentic_dataset.authorized_recall` is deliberately separable from
  everything else so this needs no adoption of the control plane.
- **A fifth runtime adapter.** The bar is that it contains no policy decision.
  If you find yourself re-deciding something to make it fit, that is a finding
  about the model and worth an issue.
- **An assertion that cannot be expressed** in some runtime. Per
  `CONFORMANCE.md`, that is a finding about the assertion, not the framework.

## Running things

```bash
pip install -e ".[all]"

python -m agentic_dataset.conformance      # AD-001..AD-015, every runtime
python -m agentic_dataset.authorized_recall
python evals/evaluate.py
pytest -q
```

`python -m agentic_dataset.conformance` exits non-zero on any failure. CI also
runs the core with **no** framework installed, which is where an import leaking
out of `adapters/` fails.

## House rules for code

- The core stays dependency-free. Framework imports live in `adapters/` and
  `mcp_boundary.py`, nowhere else.
- No policy decision in an adapter. Every runtime calls `ControlPlane.admit`.
- Assert on absence, not on wording. `assert "I cannot" in response` tests
  nothing; `assert result.grant is None and result.execution.tool_calls == []`
  tests the property.
- If the implementation disagrees with a document in `docs/`, record it in
  `docs/FINDINGS.md` rather than editing the document to agree. The
  architecture documents predate the code and are evidence of what was designed
  before it was built.
