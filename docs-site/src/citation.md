# Citation

The software carries a `CITATION.cff`, which GitHub renders as *Cite this
repository*.

**`v0.1.0` is released and archived.** Cite the DOI:

```
Chernov, A. (2026). Agentic Dataset Reference Implementation and
Conformance Suite (v0.1.0) [Computer software]. Zenodo.
https://doi.org/10.5281/zenodo.22536342
```

| | DOI |
|---|---|
| **Concept** — always resolves to the newest version. **Cite this.** | [10.5281/zenodo.22536342](https://doi.org/10.5281/zenodo.22536342) |
| Version — `v0.1.0` specifically, for reproducibility | [10.5281/zenodo.22536343](https://doi.org/10.5281/zenodo.22536343) |

ORCID: [0009-0007-3198-2712](https://orcid.org/0009-0007-3198-2712)

**The archive carries four licences and the DOI record names all four.** No
single identifier describes this release, so `LICENSE.md` inside the archive
stays authoritative for which licence covers which file. The record says *which*
licences apply; only that file says *to what*.

## Citing an assertion

The identifiers `AD-001` … `AD-015` are stable and may be referred to freely.
Cite the assertion, not a line number:

> …refuses on an unregistered capability (AD-006) and records the refusal
> (AD-010).

## Citing the metric

Authorized Recall@K is defined in
[its own package](authorized-recall.md), which has no dependency on this
architecture. If you use the metric without adopting the control plane, cite
the package rather than the reference implementation.

## Papers

Three conference papers argue the model. **Two are now in published
proceedings and carry DOIs; cite those rather than this repository when citing
the argument.** The third is accepted and awaiting its proceedings.

| Venue | Title | DOI |
|---|---|---|
| IEEE CCECE 2026 | *Agentic Datasets as an Engineering Control Plane* | [10.1109/CCECE68150.2026.11610344](https://doi.org/10.1109/CCECE68150.2026.11610344) · pp. 326–332 |
| IEEE BigDataService 2026 | *Agentic Data Services: A Control-Plane Architecture for Adaptive Data Workflows* | [10.1109/BigDataService70481.2026.00025](https://doi.org/10.1109/BigDataService70481.2026.00025) · pp. 125–129 |
| IEEE EMBC 2026 | *Dataset Descriptors for Autonomous and Observable Biomedical Data Pipelines* | accepted; not yet in proceedings |

*Verified against Crossref on 2026-09-06. The EMBC entry is the one that will
go stale next, and it will do so silently — nothing here fails when a paper
appears.*

Nothing in this repository depends on them: the assertions, the vectors and the
measurements are reproducible from a clone.
