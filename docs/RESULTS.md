# Results

```
15 normative assertions, 85 language-neutral vector steps

reference architecture      4 runtimes x 2 dataset boundaries   15/15 each
independent implementation  shares no code with the above       15/15
mutation analysis           17 targeted violations              17/17 detected
                            15/15 assertions covered             2.2 assertions
                                                                 per mutant
execution safety            0 / 39  prohibited steps, per subject
                            0 / 576 prohibited executions, white-box matrix
                            0 /  24 prohibited executions, evaluation
tests                       405 passed

Authorized Recall@5         filter after truncation     0.853
                            filter before truncation    0.960
                                                       +0.107
```

The two prohibited-execution denominators are separate because they are
separate experiments: 576 is 72 attempts in each of the 8 conformance
configurations, 24 is the adversarial set in the evaluation. Reporting 0/600
would merge two populations that were never sampled together.

Everything below was produced by running the code in this repository. Raw
output is in [`runs/`](runs/); the commands that produce it are in the README.

Measured 2026-09-01 on Python 3.12.13, Linux, with:

```
langgraph 1.2.11 · langchain-core 1.6.1 · llama-index-core 0.14.24
google-adk 2.8.0 · mcp 2.1.1 · pytest 9.1.1
```

---

## 1. The conformance result

AD-001 … AD-015 against four runtimes, at two dataset boundaries.

```
RUNTIME           RESULT  PASSED
native+local      PASS    15/15
langgraph+local   PASS    15/15
llamaindex+local  PASS    15/15
adk+local         PASS    15/15
native+mcp        PASS    15/15
langgraph+mcp     PASS    15/15
llamaindex+mcp    PASS    15/15
adk+mcp           PASS    15/15

AD-015 prohibited execution rate: 0.000 (target exactly 0)
```

120 assertion-runs, no failures, no assertion dropped as inexpressible.

**What this supports.** The same fifteen assertions hold across four runtimes
with genuinely different primitives — a conditional edge in LangGraph, typed
event dispatch in LlamaIndex Workflows, a before-tool callback in ADK, and a
straight function sequence in the framework-free reference — and across two
dataset boundaries, local and MCP. The governance model is not a property of
the framework.

**What this does not support.** The four runtimes share one `ControlPlane`.
That is deliberate — an assertion that passed because each port re-implemented
its own policy would be four experiments, not one — but it means the result is
about the *expressibility* of the model in four runtimes, not about four
independent implementations agreeing. A second implementation by someone else,
from `CONFORMANCE.md` alone, is the experiment this one is not.

**A ninth subject shares nothing.** `conformance/toy_implementation.py` is 250
lines written from the specification — no framework, no MCP, no descriptor
class, no policy engine; grants are integers in a dict — and it passes all
fifteen. That is the evidence that the assertions are properties of the
contract rather than of the reference architecture.

**What is still missing is independence of authorship.** The toy was written by
the same person who wrote the specification, and one person's reading of their
own document is the weakest kind of independence. The outstanding experiment is
a second reading by somebody else.

**And the suite would now notice a broken implementation.** Seventeen variants,
each removing exactly one guarantee, are each caught by the assertion named for
them, and every one of the fifteen assertions has a mutant of its own —
`python -m agentic_dataset.conformance --matrix`.

The detection matrix in `PORTABILITY.md` reports two separate things, because
they mean different things: **target detection** (17/17) says the suite is
sensitive to each named violation, and **cross-detection** (2.2 assertions per
mutant) says the assertions are not orthogonal. The second is a characterisation
rather than a score. It is also how the coverage gap was found: the first
version of the analysis had 13 mutants covering 11 assertions, and nothing in
the pass/fail output revealed that four assertions were never under test.

The move outside cost something, and `PORTABILITY.md` records it: AD-003 and
AD-007 became universally quantified invariants over every observation rather
than single pokes at a call site (stronger), and AD-008 became behavioural
rather than structural (wider, and the structural version survives in
`agentic_dataset.reference_suite`).

The suite failed on this implementation five times before it passed; see
[`FINDINGS.md`](FINDINGS.md) F-004 … F-009. Two of those were visible only in
the MCP configuration and two only under the async runtimes, which is the
argument for the matrix rather than a single run.

## 1a. Mutation analysis

Seventeen variants, each removing exactly one guarantee, run against the same
vectors. `T` is the assertion the mutant was written for; `x` is a redundant
detection.

```
        M01 M02 M03 M04 M05 M06 M07 M08 M09 M10 M11 M12 M13 M14 M15 M16 M17
        --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---
AD-001   T   .   .   .   x   .   .   .   .   .   .   .   .   .   .   .   .    2
AD-002   .   T   x   .   .   .   .   .   .   .   .   .   .   .   .   .   .    2
AD-003   .   .   T   T   .   .   .   .   .   .   .   .   .   .   .   .   .    2
AD-004   .   .   .   .   T   .   .   .   .   .   .   .   .   .   .   .   x    2
AD-005   .   .   .   .   .   T   .   .   .   .   .   .   .   .   .   .   .    1
AD-006   .   .   .   .   x   .   T   .   .   .   .   .   .   .   .   .   .    2
AD-007   .   .   .   .   .   .   .   T   .   .   .   .   .   .   x   x   .    3
AD-008   .   .   .   .   .   .   .   .   T   T   .   .   .   .   .   .   .    2
AD-009   .   .   .   .   .   .   .   .   .   .   T   x   x   x   .   .   x    5
AD-010   .   .   .   .   .   .   .   .   .   .   x   T   x   x   .   .   x    5
AD-011   .   .   .   .   .   .   .   .   .   .   .   .   T   .   .   .   .    1
AD-012   .   .   .   .   .   .   .   .   .   .   .   .   .   T   .   .   .    1
AD-013   .   .   x   x   .   .   .   x   .   .   .   .   .   .   T   .   .    4
AD-014   .   .   x   x   .   .   .   x   .   .   .   .   .   .   .   T   .    4
AD-015   .   .   .   .   x   .   .   .   .   .   .   .   .   .   .   .   T    2

M01  AD-001  descriptor-not-validated
M02  AD-002  advertised-means-implemented
M03  AD-003  executes-without-a-grant
M04  AD-003  expired-tokens-accepted
M05  AD-004  refusal-still-mints-authority
M06  AD-005  indeterminate-becomes-refusal
M07  AD-006  default-allow
M08  AD-007  delegation-widens-scope
M09  AD-008  cache-ignores-principal
M10  AD-008  cache-ignores-revision
M11  AD-009  evidence-omits-principal
M12  AD-010  refusal-leaves-no-evidence
M13  AD-011  evidence-omits-revision
M14  AD-012  evidence-omits-policy-version
M15  AD-013  remote-delegation-unchecked
M16  AD-014  handoff-unchecked
M17  AD-015  prohibitions-ignored

target detection : 17/17 mutants caught by their intended assertion
cross-detection  : 2.2 assertions per mutant on average
coverage         : 15/15 assertions have a mutant of their own

T = caught by its target assertion   x = caught redundantly
. = not detected                     ! = target failed to catch it
```

**Three separate figures, because they mean three different things.** Target
detection says the suite is sensitive to each named violation. Coverage says
every assertion is exercised as the assertion under test rather than only as a
bystander. Cross-detection says the assertions are not orthogonal.

The last one is a characterisation, not a score, and is deliberately not being
driven anywhere. AD-005, AD-011 and AD-012 detect only their own mutant — a
single behavioural check carries the whole detection burden for each — and that
is worth knowing about those three rather than concealing.

Coverage was 11/15 in the first version of this analysis, and nothing in the
pass/fail output showed it. Drawing the matrix did.

## 2. Authorized Recall@K — milestone M6

Defined and measured in `agentic_dataset.authorized_recall`, which has no
dependency on the rest of the repository. Its
[README](../src/agentic_dataset/authorized_recall/README.md) carries the
mathematical definition, the two conventions, and a proof that the
pre/post-filter gap is non-negative for every ranking, K and predicate — so the
sign of every gap below is guaranteed and only the size is empirical.

40 synthetic datasets across 8 domains, 24 queries, 4 authorization profiles,
96 query-principal pairs. Relevance is defined by construction: a dataset is
relevant to a query if it is in the query's domain.

```
  K   Recall  ARecall  ARecall    gap     P@K   nDCG unusable
                 post      pre                       in top-K
  1    0.200    0.750    0.750 +0.000   1.000  1.000    68.8%
  3    0.483    0.835    0.863 +0.027   0.806  0.843    68.8%
  5    0.867    0.954    0.988 +0.033   0.867  0.874    68.5%
 10    1.000    1.000    1.000 +0.000   0.500  0.952    39.1%
```

Excluding the 66 pairs where nothing relevant is authorized at all — those
score 1.0 by convention, which inflates the mean:

```
  K  ARecall post  ARecall pre     gap
  1         0.200        0.200  +0.000
  3         0.473        0.560  +0.087
  5         0.853        0.960  +0.107
 10         1.000        1.000  +0.000
```

**The number.** At K=5, moving the authorization filter ahead of truncation
takes Authorized Recall@5 from **0.853 to 0.960 (+0.107)**. Plain Recall@5
stays at 0.867 and cannot see the difference. Against the ≥ 0.95 gate in
`CONFORMANCE.md`, filter-after-truncate fails and filter-before-truncate
passes.

**68.8% of what retrieval surfaces is unusable to the principal who asked.**
Standard Recall@K scores every one of those as a success.

**Caveats, in order of how much they matter.**

1. The corpus is synthetic and the relevance judgements are by construction.
   The absolute numbers are properties of that construction. The *gap* between
   the two ARecall columns is a property of where the filter sits, which is
   what the metric was defined to isolate.
2. Retrieval is TF-IDF cosine, not embeddings. MRR is 1.000, so the retrieval
   task is easy; a harder corpus would move all three columns.
3. The 1.0-for-empty convention is a decision, not arithmetic. Both means are
   reported so the decision is visible.

**This metric now has a number. It did not before.** It has one number, from
one synthetic corpus, from the implementation that proposed it.

## 3. Evaluation — milestone M5

Six evaluators, reported separately, five repetitions.

```
METRIC                   KIND          VALUE  GATE  STATUS
policy decision correct  invariant     1.000  1.00  PASS
refusal reason correct   invariant     1.000  1.00  PASS
provenance complete      invariant     1.000  1.00  PASS
capability selection     statistical   1.000  0.97  PASS
dataset selection        statistical   1.000  0.95  PASS
trajectory validity      statistical   1.000  0.95  PASS
prohibited executions    invariant     1.000  1.00  PASS   0 of 24 executed
groundedness             not-measured    n/a    --  N/A
```

**Every spread is zero, and that is not a result.** The interpreter is
deterministic, so repetition measures nothing here. Substituting
`LLMInterpreter` is what makes the statistical rows carry a spread — and the
invariant rows are the ones that must not move when it does.

**Groundedness is not measured.** It needs a model-generated answer, and this
build synthesises no prose; scoring the deterministic formatter against its own
input would produce 1.000 and mean nothing. Reported as N/A rather than as a
number.

Capability selection measured 0.800 on the first run — see
[`FINDINGS.md`](FINDINGS.md) F-008.

## 4. Tests

```
405 passed
```

`pytest` parametrises the conformance suite down to one test per assertion per
configuration, so a failure names the assertion and the runtime.
`tests/test_verdict_parity.py` reads `ok-governed-motion`'s `policy.rs`
directly when it is checked out beside this repository, and skips otherwise.
The run above was with it present, so the serialised strings are verified
against the Rust source rather than against a copy of it.

## 5. What is not here

- **No production deployment.** Everything runs in one process. The MCP
  boundary is a real client session over an in-memory transport, not a network.
- **No model in the loop by default.** The interpreter is rule-based so the
  suite is deterministic. `LLMInterpreter` accepts any callable.
- **No real data.** The datasets are synthetic, and the capability bodies are
  trivial on purpose: if a conformance run passes it is because the gate held,
  not because the payload was clever.
- **Latency and cost are not measured.** Nothing here is a performance claim.
