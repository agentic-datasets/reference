# Plan

Milestones are ordered so that **each one produces something that runs**. A
milestone that only produces more design does not belong in this file.

---

## M1 — The contract, and a graph that refuses (target: ~250 lines)

The smallest thing that demonstrates the thesis end to end.

- [ ] `DatasetDescriptor` and `DatasetCapability` as typed models
- [ ] One synthetic dataset with a descriptor: 3 capabilities, 2 prohibited operations
- [ ] `Verdict = Approved | Refused | Indeterminate`, with typed reasons,
      ported from `ok-governed-motion` — same names, same serialised strings
- [ ] Approval token: only `Approved` mints one; execution requires one
- [ ] LangGraph: `interpret -> discover -> resolve -> admit -> {execute | refuse | indeterminate}`
- [ ] Evidence record per decision, written to a local append-only file

**Done when** three transcripts exist: one granted and executed, one refused, one
indeterminate — and in the latter two, no execution occurred and the evidence
says why.

**The test that matters is not that a refusal message was produced.** It is that
after a refusal there was no capability to execute with. Assert on the absence
of an execution record, not on the wording of an apology.

## M2 — Conformance suite

**Now specified in [CONFORMANCE.md](CONFORMANCE.md) as AD-001 … AD-015.** M2 is
implementing it, not designing it. AD-003 through AD-006 first: if those hold, a
misbehaving model cannot cause a policy violation, only a bad answer.

- [ ] Deterministic contract tests: policy verdicts, no LLM, no tolerance
- [ ] Graph routing: every admission arm, parametrised
- [ ] Negative paths — the interesting half:
      indeterminate does not fall through to execution;
      evaluator timeout yields indeterminate, not refusal;
      missing descriptor prevents execution;
      schema-version mismatch prevents execution;
      expired token prevents execution
- [ ] Capability metadata tests: dataset, effect, classification, policy id
- [ ] Adversarial: the model cannot reach a raw tool that bypasses the wrapper

**Done when** the suite fails if any invariant is removed. A suite that passes
against a broken control plane is decoration.

## M3 — MCP boundary

- [ ] One dataset behind an MCP server: descriptor, schema and lineage as
      resources; capabilities as tools
- [ ] Control plane consumes it through the LangChain MCP adapter
- [ ] A second dataset registered **without touching the graph** — the point of
      the boundary

## M4 — Semantic cache, authorization-scoped

- [ ] Cache key over intent **and** dataset revision, capability,
      authorization scope, principal class, schema version, freshness, policy
      version
- [ ] Isolation tests: same question, different principal class -> different key
- [ ] Revoked access must not hit
- [ ] Hit rate reported, with the honest note that it is a property of the
      traffic and not of the cache

**This is the security-critical milestone.** A semantic cache whose lookup is
not authorization-aware is a policy bypass with good latency.

## M5 — Evaluation

- [ ] LangSmith datasets: admission, discovery, adversarial
- [ ] Separate evaluators, not one judge — dataset selection, capability
      selection, policy decision, prohibited-tool calls, trajectory validity,
      provenance completeness
- [ ] Deterministic evaluators wherever the property is mechanical; LLM-judge
      only for semantic questions
- [ ] Repetitions, so the probabilistic numbers carry a spread rather than a
      single figure

**Gate shape**: 100% required for control-plane invariants (policy correctness,
prohibited execution, provenance). Thresholds for probabilistic quality.

## M6 — Authorized Recall@K

The one genuinely new idea, and currently measured nowhere.

Retrieval quality over the subset a principal may actually use, rather than
over the corpus. Discovery that surfaces a dataset the caller cannot touch has
not helped, and standard Recall@K scores it as a success.

- [ ] Define it precisely enough to be disagreed with
- [ ] Measure it against plain Recall@K on the same corpus
- [ ] Report the gap

**Do not cite this metric anywhere until M6 has a number.**

---

## Open questions

1. **Reuse or reimplement the verdict types?** Porting to Python risks drift
   from the Rust original. Binding to it is heavier but keeps one definition.
   Leaning: reimplement, with a conformance test that asserts the serialised
   strings match `ok-governed-motion` exactly.
2. **Which policy runtime?** Cedar, OPA/Rego, or a small internal evaluator.
   The architecture must not depend on the answer.
3. **Is the evidence ledger in scope, or a dependency?** `VOLUME_SPEC` already
   defines decision records. Preference is to depend on it rather than invent a
   second format.
4. **Public or private?** Private for now. A reference implementation is more
   useful public, and that is a separate decision under the prefix policy —
   `dk-` becomes `ok-` on a rename, not a copy.
5. **Does this become a paper?** It is a systems artifact, not a result. It
   would strengthen the existing descriptor papers rather than stand alone —
   unless M6 produces a number, in which case the metric is the paper.

## Not in scope

- A general agent framework
- A production deployment
- Anything requiring the current employer's systems, data or people

## Provenance of this plan

Derived from an architecture document written 2026-08-31 mapping the published
agentic-dataset control plane onto LangChain, LangGraph and MCP. That document
is design; import it to `docs/ARCHITECTURE.md` and keep it labelled as such.
