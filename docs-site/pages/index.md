<div align="center" style="color: var(--fg)">
<!-- MARK -->

# Agentic Dataset Reference

**A framework-independent behavioural contract for governed, agent-facing
datasets.**
</div>

---

```
15 normative assertions, 85 language-neutral vector steps

reference architecture      4 runtimes x 2 dataset boundaries   15/15 each
independent implementation  shares no code with the above       15/15
mutation analysis           17 / 17 targeted violations detected
                            15 / 15 assertions independently exercised
                             2.2 detecting assertions per mutant (mean)
execution safety            0 / 576 prohibited executions
                            0 /  24 in the evaluation set
tests                       405 passed

Authorized Recall@5         filter after truncation     0.853
                            filter before truncation    0.960
                                                       +0.107
```

---

## Start here

An **agentic dataset** describes itself, advertises bounded capabilities,
accepts a semantic intent, decides whether an action is admissible, executes
only what was admitted, refuses the rest, and leaves evidence.

The [**specification**](specification.md) is fifteen assertions, each naming a
failure it rules out. Everything else exists to check them.

```
GRANTED        -> approval token -> execution reachable
REFUSED        -> no token       -> execution unreachable
INDETERMINATE  -> no token       -> execution unreachable
```

`INDETERMINATE` is not a refusal. An evaluator that is unreachable or out of
budget has not decided anything, and recording that as a refusal invents an
authority nobody exercised.

## Check an implementation

```bash
pip install agentic-dataset-conformance
agentic-dataset-conformance run --subject yourmodule:your_factory
```

The harness imports no implementation — not even the reference one — and a test
asserts it. The worlds and vectors are CC0; export them and write a runner in
another language if you prefer.

## What this is not

No deployment, no real data, no model in the loop by default, no latency or
cost claim, and **no security guarantee**. `capabilities()` is the subject's own
report of itself, so a subject that under-reports passes AD-002 while hiding a
tool. Conformance is a claim an implementation makes about itself, made
checkable — not an adversarial audit.

[`Claims`](claims.md) is frozen and lists everything asserted, and the one thing
explicitly not.

## Status

**Release candidate.** Public before `v0.1.0` is tagged, deliberately, so a
finding can still change the artifact rather than becoming errata against a
DOI. The independent implementation is a 250-line toy written by the same
person who wrote the specification: that establishes independence from the
reference *code*, not from its author's reading of the contract.

**Interpretive independence is the next threshold, and it needs somebody else.**
[How to do it](contributing.md).
