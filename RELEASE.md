# Release checklist

**M7 is done** — the conformance suite is portable, and an independent
implementation passes it. That was the precondition for releasing under the
"implement this contract independently" positioning; see `docs/PORTABILITY.md`.

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
      (CC BY-NC docs, BSL code). M7 has now drawn the file boundaries a
      three-way split would follow, so this is decidable rather than
      hypothetical:

      | tier | files | what it has to allow |
      |---|---|---|
      | specification | `CONFORMANCE.md`, `src/agentic_dataset/conformance/verbs.md`, `docs/PORTABILITY.md` | quoting, reproducing and extending the spec text |
      | conformance assets | `conformance/` (world, vectors, `subjects.py`, `generate.py`, `toy_implementation.py`, `mutations.py`) and `src/agentic_dataset/conformance/` (interface + runner) | a third party building and testing an independent implementation, commercially or not |
      | reference implementation | the rest of `src/agentic_dataset/`, `evals/`, `examples/` | whatever commercial boundary is wanted |

      The middle tier is now real: it imports no implementation, and a test
      asserts it. Two consequences to settle:
      - CC BY-NC on `CONFORMANCE.md` restricts reuse of the specification
        *text*, which works against treating it as an interoperability
        specification. (It does not restrict implementing the method —
        copyright covers expression, not mechanism.)
      - BSL is source-available, not OSI-approved, which forecloses JOSS for as
        long as it applies to the software. If the middle tier is permissively
        licensed and the reference implementation stays BSL, that question
        applies only to the third tier.
      - `src/agentic_dataset/authorized_recall/` is a fourth candidate: it
        imports nothing else in the repository and is the piece most likely to
        be used by people who never adopt the architecture.
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
- [ ] Make the repository public **before** tagging, so there is a window for
      external scrutiny before an immutable snapshot exists.
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
