# What the portable contract can and cannot reach

Milestone M7 moved conformance from introspecting this implementation to
observing any implementation. All fifteen assertions survived the move, but
three of them changed shape doing it, and one property was genuinely lost. Both
facts are recorded here rather than absorbed quietly, because a specification
that silently redefines an assertion to fit its harness is worse than one that
admits the assertion was partly white-box.

## Before and after

| | before M7 | after M7 |
|---|---|---|
| assertions checked through a public interface | 2 of 15 | **15 of 15** |
| implementation imports in the conformance package | 8 modules | **none** |
| subjects the suite can test | this codebase | anything satisfying `ConformanceSubject` |
| independent implementations passing | 0 | 1 (`conformance/toy_implementation.py`) |
| broken implementations demonstrably caught | 0 | 13, each by its named assertion |

## The three assertions that changed shape

### AD-003 — from "the raw call raises" to "execution implies a grant"

The white-box check called a capability directly with no authorization and
asserted it raised. There is no portable equivalent: an implementation in
another language need not have a callable object to poke at.

The portable form is a **universally quantified invariant** over every
observation the subject produces: `executed ⟹ granted`. Across the current
vectors that is 77 observations rather than one poke, plus a vector where an
expired token must stop execution.

This is stronger, not weaker. The white-box version proved one call site was
guarded; the invariant proves no observed execution ever lacked authority.

### AD-007 — from "widening is rejected at the call" to "the scope executed
under is never wider than the scope admitted"

Same move. The check used to construct a widened `AuthorizationScope` and pass
it to the registry. Now the subject reports `grant_scope` and `executed_scope`
and the harness checks containment on every observation, plus a delegation
vector that attempts an actual widening.

### AD-008 — from "the cache key contains these dimensions" to "these
distinctions produce a miss"

This one genuinely lost something, and gained something.

**Lost:** the white-box check took the cache key apart and asserted that
altering each of eight dimensions changed the digest. That is unreachable from
outside, and it should be: it constrains *how* an implementation separates
principals, not *whether* it does.

**Gained:** the portable form is behavioural — same question by a different
principal class misses; a new dataset revision misses; a new policy version
misses; a revoked principal does not reach the cache at all. An implementation
that uses per-principal cache partitions instead of a composite key passes the
behavioural form and would have failed the structural one, and it is not doing
anything wrong.

So the portable assertion is **wider** than the white-box assertion, and the
structural check remains in `agentic_dataset.reference_suite` as an
implementation-specific test, where it belongs.

## What is still not expressible, and will not be

**Honesty of the subject.** `capabilities()` is the subject's own report of
what it will execute. A subject that under-reports passes AD-002 while hiding a
tool. Conformance here is a **claim an implementation makes about itself, made
checkable** — it is not an adversarial audit of a binary, and no interface of
this kind can be. Anyone treating a conformance pass as a security guarantee
against a hostile implementation has misread it.

**Anything about latency, cost or concurrency.** Not measured, not asserted,
out of scope.

## What the toy demonstrates

`conformance/toy_implementation.py` is roughly 250 lines and shares nothing
with the reference implementation but the interface module. It has no
framework, no MCP, no descriptor class, no policy engine, no ledger — grants
are integers in a dict and the cache is a dict.

It passes all fifteen.

That is the evidence that the assertions are properties of the **contract**
rather than of the reference architecture. The reference implementation is one
way to satisfy them; the toy is a second, deliberately unlike the first.

It also produced the first finding: its initial version derived `capabilities()`
from the descriptors, which made every advertised capability executable by
construction. AD-002 caught it on the first run. A suite that could not have
caught that would not have been worth building.

## Mutation results

Seventeen deliberately broken variants, each removing exactly one guarantee.
The matrix is what `python -m agentic_dataset.conformance --matrix` prints; the
committed run is in [`runs/mutation-matrix.txt`](runs/mutation-matrix.txt).

```
target detection : 17/17 mutants caught by their intended assertion
cross-detection  : 2.2 assertions per mutant on average
coverage         : 15/15 assertions have a mutant of their own
```

**The coverage line is there because it was not always 15/15.** The first
version of this analysis had thirteen mutants covering eleven assertions, which
meant AD-002, AD-009, AD-013 and AD-014 were exercised only as cross-detectors
— never as the assertion under test. Nothing in the pass/fail output showed
that. Drawing the matrix showed it immediately, and four mutants were added.

**The off-diagonal entries are a result, not noise.** They say the fifteen
assertions are not orthogonal, which is what safety invariants ought to look
like: removing the prohibition check breaks AD-015 *and* AD-004 *and* the
evidence assertions, because a prohibited action that executes also records a
grant where a refusal belonged. An assertion whose row contains nothing but its
own `T` is doing work nothing else does — AD-005, AD-011 and AD-012 are those,
and that is worth knowing about them.

The average of 2.2 is therefore a characterisation of the suite rather than a
score. It should not be driven up or down.

Reproduce: `python -m agentic_dataset.conformance --matrix`
