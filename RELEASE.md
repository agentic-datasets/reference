# Release checklist

**M7 is done** — the conformance suite is portable, and an independent
implementation passes it. That was the precondition for releasing under the
"implement this contract independently" positioning; see `docs/PORTABILITY.md`.

Nothing here is a decision. It is the list of things that have to change
*together* when the decisions in [`PLAN.md`](PLAN.md) are made, so that none of
them is discovered after a DOI has been minted.

## Blocked on decisions

- [x] **Disclosure comparison — DONE 2026-09-02. No blocker.** Nothing being
      released falls outside the intended defensive-publication envelope. The
      conclusion is recorded in the disclosure workspace rather than here,
      since that is where the search record lives.
- [x] **Licensing boundary — DECIDED 2026-09-02.** Five tiers, implemented in
      `LICENSE.md` with full license texts in `LICENSES/` and per-directory
      markers:

      | tier | license |
      |---|---|
      | specification and normative prose | CC BY 4.0 |
      | normative worlds and vectors | CC0-1.0 |
      | conformance software (incl. `generate.py`, toy, mutants) | Apache-2.0 |
      | `authorized_recall/` | Apache-2.0 |
      | reference implementation | BUSL-1.1 → Apache-2.0 on 2029-09-02 |

      Tier 5 stays restricted because the reference implementation contains a
      working expression of authorization-scoped semantic caching, which
      overlaps a live commercial interest; because `ok-agentic-datasets` states
      the same principle publicly; and because the direction is one-way —
      BSL → Apache later is easy, the reverse is not. It is time-limited rather
      than indefinite so the project is not permanently unable to describe
      itself simply.

      BSL parameters are filled in, as BSL 1.1 requires: Licensor, Licensed
      Work, Additional Use Grant (non-commercial production use permitted),
      Change Date 2029-09-02, Change License Apache-2.0. The BSL covenant
      requires a Change License compatible with "GPL Version 2.0 or a later
      version"; Apache-2.0 is GPLv3-compatible and therefore qualifies.

      **Revisit after public release**, on two pieces of evidence that do not
      exist yet: whether the contract gets external adoption, and whether the
      commercial implementation becomes a real product asset. If the Tier 5
      restriction turns out to suppress adoption while protecting little,
      moving it to Apache-2.0 is an easy later decision.

- [ ] **Align `ok-agentic-datasets`** with the same *principle* — open
      specification and interoperability artifacts, restricted commercial
      implementation. It currently applies CC BY-**NC** to all documentation
      and BSL to all code, with no tier boundary. That is not necessarily
      wrong for that repository's contents, but two public repositories in one
      programme should not state the principle differently. This does not mean
      making its code Apache.

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
- [ ] Make the repository public **before** tagging, marked clearly as a
      release candidate rather than as v0.1.0, so there is a real window for
      external scrutiny before an immutable snapshot exists.
- [ ] Invite a second implementation rather than writing one. The toy
      establishes independence from the reference *code*; only somebody else's
      reading establishes independence from the author's interpretation of the
      contract. That is the next validation threshold, and writing a third
      implementation here would not cross it.
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
