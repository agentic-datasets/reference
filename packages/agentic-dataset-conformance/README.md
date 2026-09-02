# agentic-dataset-conformance

**Fifteen normative assertions about governed datasets, as language-neutral
executable vectors, checkable against any implementation without access to its
internals.**

```bash
pip install --pre agentic-dataset-conformance   # 0.1.0rc1 is a pre-release
agentic-dataset-conformance run                 # against the built-in subject
```

Not yet on PyPI during the release candidate; install from a clone until it is.

This package contains **no implementation of the contract** — not even the
reference one. That is the property it exists to have: a conformance suite that
imports the thing it tests is testing itself.

## What the assertions rule out

| | |
|---|---|
| **AD-001** `descriptor_valid` | a dataset in admission without a well-formed contract |
| **AD-002** `capability_registered` | an executable action with no capability metadata behind it |
| **AD-003** `grant_required_for_execution` | execution reachable without an authorization artifact |
| **AD-004** `refusal_has_no_grant` | a refusal that still mints authority |
| **AD-005** `indeterminate_has_no_grant` | unknown authority becoming permission |
| **AD-006** `unknown_capability_denied` | default-allow on an unregistered tool |
| **AD-007** `authorization_scope_preserved` | scope widening between admission and execution |
| **AD-008** `cache_is_policy_scoped` | a cached answer crossing an authorization boundary |
| **AD-009** `provenance_complete` | a result that cannot be traced to what produced it |
| **AD-010** `refusal_recorded` | a refusal that leaves no evidence |
| **AD-011** `dataset_revision_recorded` | evidence that cannot identify which data was used |
| **AD-012** `policy_version_recorded` | evidence that cannot identify which rules applied |
| **AD-013** `remote_execution_preserves_scope` | MCP or A2A delegation as an escalation path |
| **AD-014** `agent_handoff_preserves_scope` | sub-agent handoff as an escalation path |
| **AD-015** `prohibited_execution_rate_zero` | any prohibited action executing at all, ever |

Every one is checked structurally. Not *"the answer said no"* but: the decision
is `REFUSED`, no grant exists, and the tool, MCP and A2A call lists are all
empty.

## Testing your implementation

Implement four methods — `load_world`, `capabilities`, `step`, `reset` — and
return an `Observation` from each step. `interface.py` is the whole contract
and `verbs.md` is the control-verb vocabulary.

```bash
agentic-dataset-conformance run --subject mypackage.conformance:make_subject
```

`--subject` takes `module:attribute`, where the attribute is a subject, or a
callable returning one or several. `agentic_dataset_conformance.toy` is a
250-line worked example that implements the contract with no framework, no
vector store and no policy engine — grants are integers in a dict — and passes
all fifteen.

## Checking that the suite would notice

```bash
agentic-dataset-conformance run --matrix
```

Seventeen deliberately broken variants, each removing exactly one guarantee.
Every one is caught by the assertion named for it, every assertion has a mutant
of its own, and the off-diagonal entries show where the assertions overlap. A
suite that cannot fail is decoration.

## The vectors are CC0

```bash
agentic-dataset-conformance vectors --export ./vectors
```

The worlds and vectors under `data/` are dedicated to the public domain:
**no attribution required, no conditions**. Copy them into a Rust crate, a Go
module or a TypeScript package and write your own runner. Python is one runner,
not the specification.

The software around them is Apache-2.0, so the distribution as a whole is
`Apache-2.0 AND CC0-1.0`.

## What conformance does and does not establish

`capabilities()` is the subject's own report of itself. A subject that
under-reports passes AD-002 while hiding a tool. **Conformance here is a claim
an implementation makes about itself, made checkable — not an adversarial
audit**, and no interface of this shape could be one.

## Links

- [The specification](https://github.com/doytsujin/ok-agentic-dataset-reference/blob/main/CONFORMANCE.md)
- [What the portable contract can and cannot reach](https://github.com/doytsujin/ok-agentic-dataset-reference/blob/main/docs/PORTABILITY.md)
- [Results, with the caveats attached to each number](https://github.com/doytsujin/ok-agentic-dataset-reference/blob/main/docs/RESULTS.md)
