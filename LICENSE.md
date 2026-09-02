# License map

This repository is **not under a single license**, and it is not accurate to
call it open source as a whole. Five tiers, chosen so that everything a third
party needs in order to implement and test the contract independently is
openly licensed, while the reference implementation of the contract is not.

| Tier | What | License |
|---|---|---|
| 1 | Specification and normative prose | **CC BY 4.0** |
| 2 | Normative worlds and vectors | **CC0-1.0** |
| 3 | Conformance software | **Apache-2.0** |
| 4 | Authorized Recall | **Apache-2.0** |
| 5 | Reference implementation | **BUSL-1.1** → Apache-2.0 on 2029-09-02 |

The accurate one-sentence summary, and the one to use publicly:

> The Agentic Dataset specification, normative vectors, conformance tooling and
> Authorized Recall implementation are openly licensed for independent
> implementation and reuse. The reference implementation is source-available
> under the Business Source License 1.1.

---

## Tier 1 — Specification and normative prose · CC BY 4.0

```
CONFORMANCE.md
packages/agentic-dataset-conformance/src/agentic_dataset_conformance/verbs.md
docs/PORTABILITY.md
docs/RESULTS.md
docs/FINDINGS.md
docs/ARCHITECTURE.md, docs/ARCHITECTURE-LLAMAINDEX.md, docs/ARCHITECTURE-ADK.md
README.md, PLAN.md, RELEASE.md, CONTRIBUTING.md
```

<https://creativecommons.org/licenses/by/4.0/>

Quote it, reproduce it, extend it, translate it, build a competing
specification on it. Attribution required. **Commercial use is permitted** —
this is CC BY, not CC BY-NC, because a specification nobody may use
commercially is not an interoperability specification.

## Tier 2 — Normative worlds and vectors · CC0-1.0

```
packages/agentic-dataset-conformance/src/agentic_dataset_conformance/data/worlds/*.json
packages/agentic-dataset-conformance/src/agentic_dataset_conformance/data/vectors/*.json
```

<https://creativecommons.org/publicdomain/zero/1.0/>

Public domain dedication, **including no attribution requirement**. This is
deliberate and it is the point of the tier: these files are meant to be
vendored unchanged into a Rust crate, a Go module, a TypeScript package or a
commercial product's test suite. Every condition attached to them is friction
against the one outcome this repository most wants.

## Tiers 2 and 3 are a published distribution

`agentic-dataset-conformance` on PyPI carries both: the software under
Apache-2.0 and the normative data under CC0-1.0, declared as the SPDX
expression `Apache-2.0 AND CC0-1.0` rather than rounded to whichever is more
convenient. `agentic_dataset_conformance/data/LICENSE` states the CC0
dedication inside the distribution, so it survives being unpacked somewhere
else.

`authorized-recall` is a second published distribution, Apache-2.0.

The reference implementation is **not published to PyPI**. `pip install` reads
as open source to most people, and shipping BUSL code that way would be
misleading whatever the metadata said.

## Tier 3 — Conformance software · Apache-2.0

```
packages/agentic-dataset-conformance/src/**   (interface, runner, CLI, toy, mutants)
conformance/generate.py
conformance/subjects.py
conformance/__init__.py
packages/agentic-dataset-conformance/src/agentic_dataset_conformance/toy.py
packages/agentic-dataset-conformance/src/agentic_dataset_conformance/mutations.py
tests/test_conformance_vectors.py
```

[`LICENSES/Apache-2.0.txt`](LICENSES/Apache-2.0.txt)

A third party must be able to *build and test* an independent implementation,
commercially or not. `generate.py` is here rather than in Tier 2 because it is
software: CC0 can cover code, but Apache-2.0 gives downstream users clearer
patent treatment.

## Tier 4 — Authorized Recall · Apache-2.0

```
packages/authorized-recall/**
```

[`LICENSES/Apache-2.0.txt`](LICENSES/Apache-2.0.txt)

This package imports nothing else in the repository. It is the piece most
likely to be used by people who never adopt the architecture — authorization-
aware search, multi-tenant retrieval, ABAC/RBAC retrieval evaluation — and
there is no strategic gain in making that difficult.

## Tier 5 — Reference implementation · BUSL-1.1

```
src/agentic_dataset/**   EXCEPT conformance/ and authorized_recall/
evals/**
examples/**
```

[`LICENSES/BUSL-1.1.txt`](LICENSES/BUSL-1.1.txt), with parameters filled in:

- **Licensor** — Alexander Chernov
- **Additional Use Grant** — production use permitted where not primarily
  intended for or directed toward commercial advantage or monetary
  compensation. Research, teaching, evaluation, peer review and personal
  projects are covered.
- **Change Date** — 2029-09-02
- **Change License** — Apache-2.0

**BSL is not an open-source license**, and the license itself says so. What it
guarantees is that this tier *becomes* one: on the Change Date, or the fourth
anniversary of first public distribution, whichever comes first, it converts to
Apache-2.0 automatically.

Two notes on the choice.

**Why the restriction exists.** The reference implementation contains a working
expression of authorization-scoped semantic caching, which overlaps a live
commercial interest. The underlying mechanisms are already defensively
published — Zenodo 10.5281/zenodo.22076330, CC BY — so this restricts *this
code*, not the ideas, and anyone is free to implement them from the papers or
from Tier 1.

**Why it is time-limited.** Indefinite source-available licensing would leave
the project permanently unable to describe itself simply. The Change Date fixes
that on a schedule rather than on a decision.

## Commercial licensing

To use Tier 5 commercially before the Change Date:

**Alexander Chernov** — GitHub [@doytsujin](https://github.com/doytsujin) ·
LinkedIn [@thedoytsujin](https://www.linkedin.com/in/thedoytsujin/)

Tiers 1–4 need no such agreement, commercially or otherwise.

## Independent reimplementation is explicitly welcome

`CONFORMANCE.md` (CC BY 4.0) states the fifteen assertions in prose;
the packaged `data/vectors/` (CC0) makes them executable. **Writing an independent
implementation against them, in any language, for any purpose including a
commercial one, and publishing whether it passes, requires no permission from
anybody.** It is the outcome this license map is arranged around.

The assertion identifiers `AD-001` … `AD-015` may be referred to freely.

---

© 2026 Alexander Chernov. Tier 5 rights reserved; Tiers 1–4 licensed as above.
