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

Thirteen deliberately broken variants, each removing exactly one guarantee.
Every one is caught by the assertion named for it:

```
mutant:descriptor-not-validated          AD-001   caught by AD-001
mutant:executes-without-a-grant          AD-003   caught by AD-002, AD-003, AD-013, AD-014
mutant:expired-tokens-accepted           AD-003   caught by AD-003, AD-013, AD-014
mutant:refusal-still-mints-authority     AD-004   caught by AD-001, AD-004, AD-006, AD-015
mutant:indeterminate-becomes-refusal     AD-005   caught by AD-005
mutant:default-allow                     AD-006   caught by AD-006
mutant:delegation-widens-scope           AD-007   caught by AD-007, AD-013, AD-014
mutant:cache-ignores-principal           AD-008   caught by AD-008
mutant:cache-ignores-revision            AD-008   caught by AD-008
mutant:refusal-leaves-no-evidence        AD-010   caught by AD-009, AD-010
mutant:evidence-omits-revision           AD-011   caught by AD-009, AD-010, AD-011
mutant:evidence-omits-policy-version     AD-012   caught by AD-009, AD-010, AD-012
mutant:prohibitions-ignored              AD-015   caught by AD-004, AD-009, AD-010, AD-015
```

The over-catching is informative rather than noise. Removing the prohibition
check breaks AD-015 *and* AD-004 *and* the evidence assertions, because a
prohibited action that executes also produces a granted decision where a
refusal was recorded — the assertions are not independent, and the overlap map
is a fact about the contract worth having written down.

Reproduce: `python -m agentic_dataset.conformance --mutants`
