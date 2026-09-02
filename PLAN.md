# Plan

Milestones are ordered so that **each one produces something that runs**. A
milestone that only produces more design does not belong in this file.

**M1 through M6 are done.** What each produced, and what it did not, is in
[`docs/RESULTS.md`](docs/RESULTS.md).

---

## M1 — The contract, and a graph that refuses ✅

- [x] `DatasetDescriptor` and `DatasetCapability` as typed models
- [x] Three synthetic datasets with descriptors: 8 capabilities, 9 prohibitions
- [x] `Verdict = Approved | Refused | Indeterminate`, with typed reasons,
      ported from `ok-governed-motion` — same names, same serialised strings
- [x] Approval token: only `Approved` mints one; execution requires one
- [x] `interpret -> discover -> resolve -> admit -> {execute | refuse | indeterminate}`
- [x] Evidence record per decision, written to a hash-chained append-only file

**Done when** three transcripts exist: one granted and executed, one refused,
one indeterminate — and in the latter two, no execution occurred and the
evidence says why. All four runtimes produce all three.

**The test that matters is not that a refusal message was produced.** It is
that after a refusal there was no capability to execute with, which is asserted
as `grant is None and tool_calls == mcp_calls == a2a_calls == []`.

## M2 — Conformance suite ✅

- [x] Deterministic contract tests: policy verdicts, no LLM, no tolerance
- [x] Routing: every admission arm, in every runtime, parametrised
- [x] Negative paths — indeterminate does not fall through to execution;
      evaluator timeout yields indeterminate, not refusal; missing descriptor,
      schema-version mismatch and expired token each prevent execution
- [x] Capability metadata tests: dataset, effect, classification, policy id
- [x] Adversarial: the model cannot reach a raw tool that bypasses the wrapper

**Done when** the suite fails if any invariant is removed. It did fail, six
times, on this implementation — [`docs/FINDINGS.md`](docs/FINDINGS.md) F-004 …
F-009. Two of those were visible only at the MCP boundary and two only under
the async runtimes.

## M3 — MCP boundary ✅

- [x] Every dataset behind an MCP server: descriptor, schema, lineage and
      policy as resources; capabilities as tools
- [x] The control plane consumes it through a real client session
- [x] A second dataset registered **without touching the graph** —
      `tests/test_mcp_boundary.py`, and the entire conformance matrix is run a
      second time with every dataset behind the boundary

The far side verifies the grant for itself. A boundary whose far side trusts
its callers is not a boundary.

## M4 — Semantic cache, authorization-scoped ✅

- [x] Key over intent **and** dataset revision, capability, authorization
      scope, principal class, schema version, freshness, policy version
- [x] Isolation tests, including one per key dimension: change it, get a
      different key, or the dimension is not protecting anything
- [x] Revoked access does not hit
- [ ] **Hit rate not reported.** `SemanticCache.stats` computes it, and it is
      not published anywhere, because on a fixture workload it would be a
      property of the fixture. It is a property of the traffic, and there is no
      traffic here.

**This is the security-critical milestone.** A semantic cache whose lookup is
not authorization-aware is a policy bypass with good latency. The cache here is
lexical, not semantic, and [`docs/FINDINGS.md`](docs/FINDINGS.md) says so:
under-hitting costs latency, over-hitting crosses a principal boundary.

## M5 — Evaluation ✅

- [x] Labelled datasets: admission, discovery, adversarial
- [x] Separate evaluators, not one judge — dataset selection, capability
      selection, policy decision, refusal reason, prohibited execution,
      trajectory validity, provenance completeness
- [x] Deterministic evaluators wherever the property is mechanical
- [x] Repetitions — and the honest reading of them: every spread is zero
      because the interpreter is deterministic, so repetition currently
      measures nothing
- [ ] **Groundedness not measured.** It needs a model-generated answer. This
      build synthesises no prose, so the metric would score its own formatter.
- [ ] **Not wired to LangSmith.** The evaluators are plain functions over
      `RunResult`. Tracing is an integration, not a result, and adding it
      would make the suite depend on a hosted service to produce a number.

**Gate shape**: 100% required for control-plane invariants. Thresholds for
probabilistic quality. Both hold — see [`docs/RESULTS.md`](docs/RESULTS.md) §3.

## M6 — Authorized Recall@K ✅

- [x] Defined precisely enough to be disagreed with — including the two edge
      cases decided rather than left to fall out of the arithmetic
- [x] Measured against plain Recall@K on the same corpus
- [x] Gap reported

**At K=5, moving the authorization filter ahead of truncation takes Authorized
Recall@5 from 0.853 to 0.960 (+0.107). Plain Recall@5 stays at 0.867 and cannot
see the difference. 68.8% of what retrieval surfaces is unusable to the
principal who asked.**

The corpus is synthetic and the relevance judgements are by construction, so
the absolute numbers belong to that construction. The gap is a property of
where the filter sits, which is what the metric was defined to isolate.
[`docs/RESULTS.md`](docs/RESULTS.md) §2 carries the caveats.

---

## Open questions, and the answers taken

1. **Reuse or reimplement the verdict types?** *Reimplemented*, with
   `tests/test_verdict_parity.py` asserting the serialised strings and
   rationales, and reading `ok-governed-motion`'s `policy.rs` directly when it
   is checked out beside this repository. The Rust `Seal` — which makes
   `Approved` unnameable outside its module — has no exact Python equivalent;
   the module-private sentinel used instead makes forging an approval
   deliberate rather than accidental, and `verdict.py` says so.
2. **Which policy runtime?** *A small internal evaluator.* Everything outside
   `PolicyEngine` sees a `Verdict`; replacing the body of `evaluate` with a
   Rego call changes no other module and no assertion. The architecture does
   not depend on the answer, which was the actual requirement.
3. **Is the evidence ledger in scope, or a dependency?** *In scope, minimally.*
   A hash-chained JSONL file, with `verify_chain` stating exactly what that
   buys: truncation and in-place edits become detectable, and nothing more. A
   real deployment substitutes an event store; `verify_chain` is what such a
   store would have to keep true.
4. **Public or private?** Open. The prefix policy makes `dk-` private and `ok-`
   public, so publishing is a rename rather than a copy.
5. **Does this become a paper?** M6 produced a number, which was the stated
   condition. The number is from one synthetic corpus and one implementation —
   enough to justify the measurement, not yet enough to be the paper.

## Not in scope

- A general agent framework
- A production deployment
- Anything requiring the current employer's systems, data or people

## M7 — a portable conformance suite ✅

Before: 2 of 15 assertions checked through a public interface. After: 15.

- [x] The conformance interface declared — four methods, one `Observation` type
- [x] World, vectors and expectations as JSON; Python is one runner
- [x] The conformance package imports nothing from any implementation, and a
      test asserts it
- [x] An independent implementation exists — `packages/agentic-dataset-conformance/src/agentic_dataset_conformance/toy.py`,
      250 lines, no framework, no MCP, no shared code — and passes 15/15
- [x] 13 broken variants, each caught by the assertion named for it
- [x] `docs/PORTABILITY.md` records what changed shape and what cannot be
      reached from outside

**The first finding came from the toy itself.** Its initial version derived
`capabilities()` from the descriptors, making every advertised capability
executable by construction. AD-002 caught it on the first run — which is the
clearest evidence available that the suite is not vacuous.

**The second came from the vectors.** AD-008 failed at the MCP boundary only:
after a revision change the server kept serving the revision it was constructed
with. The white-box suite had never noticed, because it only asserted the miss
and not the subsequent hit. `docs/FINDINGS.md` F-010.

## What would strengthen the result

In rough order of how much each would add:

1. **A second implementation by someone else.** The toy is independent of the
   reference implementation but not of its author, and one person's reading of
   their own specification is the weakest kind of independence. M7 made the ask
   reasonable — four methods and a JSON suite — but did not answer it.
2. **A model in the loop**, so the statistical rows carry a spread and the
   invariant rows can be watched not moving.
3. **A harder discovery corpus**, where MRR is not 1.000.
4. **An embedding-keyed cache**, behind the same authorization dimensions.
