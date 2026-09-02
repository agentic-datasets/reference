# Release checklist

Nothing here is a decision. It is the list of things that have to change
*together* when the decisions in [`PLAN.md`](PLAN.md) are made, so that none of
them is discovered after a DOI has been minted.

## Blocked on decisions

- [ ] **Disclosure comparison.** Compare what is being released against
      `dk-agentic-datasets-patents` — the fourth and earliest disclosure repo
      (2025-11/12), whose scope under the 2026-08-18 no-filing decision was
      left explicitly open. Establish whether anything here falls outside the
      intended defensive-publication envelope, record the conclusion, and stop.
      This is disclosure accounting, not claim mining.
- [ ] **Licensing boundary.** The current `LICENSE.md` is a two-way split
      (CC BY-NC docs, BSL code). Two consequences to settle first:
      - CC BY-NC on `CONFORMANCE.md` restricts reuse of the specification
        *text*, which works against treating it as an interoperability
        specification. (It does not restrict implementing the method —
        copyright covers expression, not mechanism.)
      - BSL is source-available, not OSI-approved, which forecloses JOSS for as
        long as it applies to the software.
- [ ] **Rename** `dk-agentic-dataset-reference` → `ok-agentic-dataset-reference`
      under the prefix policy, at the moment it goes public and not before.

## Mechanical, once the above are settled

- [ ] Update the repository URL in `CITATION.cff` (`repository-code`,
      `license-url`) — GitHub redirects the old name, the citation record
      should not rely on that.
- [ ] Add an ORCID to `CITATION.cff`.
- [ ] Update the GitHub repository description. It still reads "on the
      LangChain stack. PLANNED — nothing built yet", which contradicts the
      first screen of the README.
- [ ] Write `.zenodo.json` — it needs a license identifier, so it cannot be
      written before the licensing decision.
- [ ] Re-run everything and refresh `docs/runs/`:
      ```
      python -m agentic_dataset.conformance
      python -m agentic_dataset.authorized_recall
      python evals/evaluate.py
      pytest -q
      ```
- [ ] Tag `v0.1.0` and archive that exact tag through the Zenodo GitHub
      integration. **Zenodo publication is irreversible** — confirm the record
      immediately before minting.
- [ ] The technical report is a separate repository with its own DOI, which
      cites the software DOI. Do not vendor a `paper/` directory here: the
      software artifact and the scholarly artifact should not become
      version-coupled.

## Deliberately not on this list

**JOSS.** It requires an OSI-approved license and a public development history,
so it cannot be an automatic downstream target of the current licensing. Decide
it as its own question, after the repository has accumulated real public
history — not as a consequence of this release.
