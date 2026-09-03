# Frozen claims

**Frozen 2026-09-02, before the release candidate.** This file exists so that
the remaining work — licence alignment, rename, publication, a technical report
— cannot quietly strengthen what is being asserted. Anything said about this
project in a README, an abstract, a post or a paper should be checkable against
this table.

A claim moves out of this file only by being measured differently, and the
measurement changes with it.

| # | Claim | Status |
|---|---|---|
| 1 | The governance model is a framework-independent behavioural contract | **Supported** |
| 2 | It can be expressed as language-neutral executable vectors | **Supported** — 15 vectors, 85 steps, JSON |
| 3 | Conformance can be evaluated without access to an implementation's internals | **Supported** — the harness imports no implementation, asserted by test |
| 4 | All 15 assertions are portable | **Supported** — 15/15 through the public interface, and in **two languages** since 2026-09-03 |
| 5 | Four runtimes across two dataset boundaries all conform | **Supported** — 8 configurations, 15/15 each |
| 6 | An implementation sharing no code with the reference conforms | **Supported, with the limitation stated**: the toy is independent of the reference *code*, not of its author |
| 7 | The suite detects targeted violations | **Supported** — 17/17 mutants caught by their named assertion |
| 8 | Every assertion is exercised as the assertion under test | **Supported** — 15/15 coverage |
| 9 | The portability conversion exposed a real defect | **Strong evidence** — F-010, invisible to the white-box suite |
| 10 | The suite catches unplanned implementation mistakes, not only planted ones | **Strong evidence** — F-011, made by the toy in earnest |
| 11 | No prohibited action executed | **Supported for the measured matrix** — 0/576 white-box, 0/39 per portable subject, 0/24 evaluation |
| 12 | Authorized Recall@K improves when the filter precedes truncation | **Supported**, sign proved and magnitude measured on one synthetic corpus |
| 13 | A security guarantee, or exhaustive discovery of an implementation's capabilities | **Explicitly not claimed** |

## On claim 4

**Extended 2026-09-03. This is the freeze working as intended: the claim did not
change, the measurement did.**

Until now every measured subject was Python, so "language-neutral" described the
*form* of the vectors — JSON, no Python object semantics — rather than something
observed. A TypeScript subject in `agentic-datasets/showcase` now runs the same
suite and reports the same numbers:

| | Python | TypeScript |
|---|---|---|
| vectors loaded | 15 | 15 |
| assertions | 15/15 | 15/15 |
| observations | 77 | 77 |
| AD-015 prohibited attempts | 39 | 39 |
| AD-015 prohibited executions | 0 | 0 |

Seven mutants are each caught by the assertion named for them, in both.

What was checked before recording this, rather than taken from the other
repository's README: the vectors and worlds in the TypeScript project are
**byte-identical** to `agentic_dataset_conformance/data/` (`diff -rq`, clean, 15
files each, CC0 licence file included); its engine has **no non-relative
imports**, so it shares no runtime with the reference; and the Python baseline was
re-run here to confirm 15/77/39/0 rather than trusted as a constant.

**What this establishes.** The vectors execute outside Python, through the public
interface, with no shared runtime. `CONFORMANCE.md` said an implementation "in
Rust, Go, TypeScript or Java can be checked without reproducing Python object
semantics — Python is one runner, not the specification." That was a design
intention; it is now an observation.

**What it does not establish.** The TypeScript subject is a transcription of
`toy.py` by the same author, not a fresh reading of the specification. **Claim 6
is unchanged and claim 6's limitation still stands**: interpretive independence
requires somebody else, and remains the contribution this project most needs. A
second language is not a second reader.

## On claim 13

`capabilities()` is the subject's own report of itself. A subject that
under-reports passes AD-002 while hiding a tool. Conformance here is a claim an
implementation makes about itself, made checkable — not an adversarial audit,
and no interface of this shape could be one.

This line is load-bearing. Without it the conformance vocabulary drifts into
sounding like a security certification, which is the single easiest overclaim
available to this project.

## On claim 6

The toy establishes independence from the reference implementation's code. It
does not establish independence from the author's reading of the
specification, because the same person wrote both. **Interpretive independence
is unclaimed and is the next validation threshold** — it requires somebody
else, and no further implementation written here would supply it.

## On claim 12

The gap's *sign* is proved for every ranking, K and predicate. Its *size*
(0.853 → 0.960 at K=5) is measured on one synthetic corpus with relevance by
construction and a TF-IDF retriever, and belongs to that construction.

## Not measured at all

Latency, cost, concurrency, throughput. Semantic answer quality beyond the
evaluators in `evals/`. Groundedness — reported as N/A rather than as a number,
because this build synthesises no prose and the metric would score its own
formatter.
