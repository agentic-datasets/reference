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

      **Recommended split — not decided.** Five tiers, because the normative
      JSON behaves more like data than like software and benefits from less
      friction than the runner does:

      | tier | files | recommended | why |
      |---|---|---|---|
      | specification prose | `CONFORMANCE.md`, `src/agentic_dataset/conformance/verbs.md`, `docs/PORTABILITY.md` | CC BY 4.0 | quote, reproduce and extend the spec text |
      | normative data | `conformance/worlds/*.json`, `conformance/vectors/*.json` | CC0-1.0 | copy them into a Rust repo, ship them with a commercial implementation, transform them into another harness — friction here defeats the purpose, and CC0 also removes the attribution requirement from material meant to be vendored unchanged |
      | conformance software | `src/agentic_dataset/conformance/`, `conformance/subjects.py`, `generate.py`, `toy_implementation.py`, `mutations.py` | Apache-2.0 | a third party must be able to build *and test* an independent implementation, commercially or not. `generate.py` is software and belongs here rather than with the data it emits — CC0 can cover code, but Apache-2.0 gives downstream users clearer patent treatment |
      | Authorized Recall | `src/agentic_dataset/authorized_recall/` | Apache-2.0 | imports nothing else here; the piece most likely to be used by people who never adopt the architecture, and there is no strategic gain in making that hard |
      | reference implementation | the rest of `src/agentic_dataset/`, `evals/`, `examples/` | **the one open question** | see below |

      **The only strategic decision left is the last tier**, and the test is:
      if someone clones the reference implementation into a commercial agent
      platform tomorrow, do you want to stop them?

      Arguments for Apache-2.0 throughout:
      - "Agentic Dataset Reference is open source" is a statement you can
        actually make. With BSL on the implementation the accurate sentence is
        "the specification, vectors and conformance tooling are open; the
        reference implementation is source-available", which is correct but
        harder for GitHub users, companies and reviewers to act on.
      - It is the only tier blocking JOSS.
      - Every stated objective — citation, third-party implementations, reuse
        of Authorized Recall, adoption of the contract — is helped by it.
      - The mechanisms here are already defensively published (2026-08-18
        decision, `ok-defensive-disclosures`, Zenodo 10.5281/zenodo.22076330).
        BSL protects this *code*, not the ideas, and the ideas are out.

      Arguments for keeping it restricted:
      - `ok-agentic-datasets`, the adjacent public repo in this programme,
        states the opposite policy in its `NOTICE.md`: commercial rights
        reserved, "the foundation for a commercial software product". Two
        public repos in one programme with contradictory licences is worse
        than either choice made consistently. **Whichever way this goes, that
        repo needs to agree with it.**
      - The awaw.ai venture's locked wedge is governance-aware caching with
        per-tenant scoping — which is what `cache.py` and AD-008 are. The
        product code lives in mosquitodog rather than here, so this is a
        reference expression rather than the asset, but the overlap is real
        and worth deciding deliberately rather than by default.
      - **The asymmetry.** BSL → Apache-2.0 later is easy. Apache-2.0 → BSL is
        not: every published version stays permissive. If the answer is
        genuinely uncertain, the cheap order is restrictive first.

      The middle tiers are now real rather than aspirational: they import no
      implementation, and a test asserts it. Two consequences to settle:
      - CC BY-NC on `CONFORMANCE.md` restricts reuse of the specification
        *text*, which works against treating it as an interoperability
        specification. (It does not restrict implementing the method —
        copyright covers expression, not mechanism.)
      - BSL is source-available, not OSI-approved, which forecloses JOSS for as
        long as it applies to the software. Under the split above that question
        applies only to the last tier.
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
