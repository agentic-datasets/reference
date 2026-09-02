# Citation

The software carries a `CITATION.cff`, which GitHub renders as *Cite this
repository*.

```
Chernov, A. (2026). Agentic Dataset Reference Implementation and
Conformance Suite (Version 0.1.0) [Computer software].
https://github.com/doytsujin/ok-agentic-dataset-reference
```

ORCID: [0009-0007-3198-2712](https://orcid.org/0009-0007-3198-2712)

**There is no DOI yet.** One will be minted from the `v0.1.0` tag once the
release-candidate window closes; until then cite the repository and a commit.

## Citing an assertion

The identifiers `AD-001` … `AD-015` are stable and may be referred to freely.
Cite the assertion, not a line number:

> …refuses on an unregistered capability (AD-006) and records the refusal
> (AD-010).

## Citing the metric

Authorized Recall@K is defined in
[its own package](https://github.com/doytsujin/ok-agentic-dataset-reference/blob/main/authorized-recall.md), which has no dependency on this
architecture. If you use the metric without adopting the control plane, cite
the package rather than the reference implementation.

## Papers

Three conference papers argue the model. All were accepted for 2026 and none is
in published proceedings yet, so there are no DOIs to cite.

| Venue | Title |
|---|---|
| IEEE CCECE 2026 | *Agentic Datasets as an Engineering Control Plane* |
| IEEE EMBC 2026 | *Dataset Descriptors for Autonomous and Observable Biomedical Data Pipelines* |
| IEEE BigDataService 2026 | *Agentic Data Services: A Control-Plane Architecture for Adaptive Data Workflows* |

Nothing in this repository depends on them: the assertions, the vectors and the
measurements are reproducible from a clone.
