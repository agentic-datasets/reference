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

- [x] **Claims frozen 2026-09-02** — [`docs/CLAIMS.md`](docs/CLAIMS.md).
      Thirteen rows, one of which is "explicitly not claimed". Nothing written
      about this project during the remaining administrative work should assert
      anything not in that table.

- [x] **`ok-agentic-datasets` aligned — DONE 2026-09-02.** Its documentation
      moved from CC BY-NC 4.0 to **CC BY 4.0**, and its Business Source
      provisions were removed: they applied to `prototypes/` and `datasets/`
      directories that have never existed there, so they licensed nothing. Its
      `NOTICE.md` no longer claims a repository-wide commercial restriction and
      instead points at per-repository licensing.

      The programme is now *coherent* rather than uniformly licensed — the
      commercial boundary sits around executable implementation code, not
      around the prose describing it. Forcing BUSL onto a repository because it
      shares a programme name would have been the wrong kind of consistency.

- [x] **Renamed 2026-09-02** to `ok-agentic-dataset-reference`, under the
      naming policy, while still private. Done before publication rather than
      after, so no public name is ever cited or cloned and then redirected.

## Mechanical, once the above are settled

- [x] Repository URLs in `CITATION.cff` (`repository-code`, `license-url`)
      updated to the `ok-` name. GitHub redirects the old one, but a citation
      record should not depend on a redirect.
- [x] ORCID added to `CITATION.cff` — 0009-0007-3198-2712, verified against
      the ORCID public API: the record names Alexander Chernov and lists
      github.com/doytsujin, chernov.ca and the LinkedIn profile as its
      researcher URLs. It must also be duplicated into `.zenodo.json`, which
      does not inherit it from `CITATION.cff`.
- [x] GitHub repository description replaced. It had still read "on the
      LangChain stack. PLANNED — nothing built yet", which contradicted the
      first screen of the README and was wrong in three ways at once.

- [ ] **Zenodo metadata is a mixed-licence problem, not a filled-in field.**
      The release carries four rights regimes — CC-BY-4.0, CC0-1.0,
      Apache-2.0, BUSL-1.1 — so no single licence identifier describes it.
      `"license": "BUSL-1.1"` would wrongly imply BSL covers the vectors and
      the conformance software; `"license": "Apache-2.0"` would wrongly imply
      the reference implementation is permissive, which is worse.

      Do not resolve this by picking one. Declare every applicable licence on
      the Zenodo record and leave `LICENSE.md` as the authoritative
      file-to-licence map.

      **To verify in Zenodo Sandbox before minting anything** — these are
      expectations, not confirmed facts, and the schema may have moved:
      - whether the `.zenodo.json` GitHub-integration schema still exposes a
        single `license` field, and if so whether a record created that way
        can be corrected to multiple licences before publishing;
      - that **Zenodo ignores `CITATION.cff` entirely when `.zenodo.json` is
        present** — they do not merge, so every creator, ORCID, version and
        related-identifier field has to be duplicated correctly into
        `.zenodo.json`;
      - the Rights section of the draft record, read in full, before publish.

      Sequence: RC public → scrutiny → tag `v0.1.0` → create the record →
      verify Rights → publish. **Zenodo publication is irreversible**, and a
      record asserting one licence over a four-regime artifact is not something
      to fix afterwards.
- [x] Re-ran everything and refreshed `docs/runs/` under the final repository
      identity:
      ```
      agentic-dataset-conformance run --subject conformance.subjects:subjects
      python -m authorized_recall
      python evals/evaluate.py
      pytest -q
      ```
- [x] **Public since 2026-09-02**, marked as a release candidate in the README
      rather than as v0.1.0, so the scrutiny window is real.
- [x] **Documentation site live** —
      <https://doytsujin.github.io/ok-agentic-dataset-reference/>. mdBook,
      generated from the repository's own files; CI fails if the two drift.
- [x] **Tagged `v0.1.0-rc.1`** so the candidate itself is citable and the
      changes external scrutiny produces can be diffed against it.
- [ ] **Publish the two permissive distributions to PyPI.** Blocked on
      credentials: there is no `~/.pypirc` or PyPI token on this machine, and
      publication is irreversible — a version number cannot be reused once
      uploaded, and yanking does not remove it. `agentic-dataset-conformance`
      and `authorized-recall` are built and verified as wheel and sdist.
      The reference implementation is **not** published: it is BUSL-1.1.
- [ ] Invite a second implementation rather than writing one. The toy
      establishes independence from the reference *code*; only somebody else's
      reading establishes independence from the author's interpretation of the
      contract. That is the next validation threshold, and writing a third
      implementation here would not cross it.
- [ ] Tag `v0.1.0` and archive that exact tag. **Zenodo publication is
      irreversible** — read the whole draft record, Rights included, in the
      same sitting as pressing publish.
- [ ] The technical report is a separate repository with its own DOI, which
      cites the software DOI. Do not vendor a `paper/` directory here: the
      software artifact and the scholarly artifact should not become
      version-coupled.

- [x] **Git history reviewed and accepted 2026-09-02.** Earlier commits name
      four private repositories, in commit *contents* rather than messages —
      `git log -S` finds them. HEAD is clean and a leak scan over the tree
      (keys, tokens, account ids, home paths, hostnames, credentials) found
      nothing. The decision is to accept: the names leak, the contents do not,
      and all four repositories stay private. **No history rewrite.**

## Deliberately not on this list

**JOSS.** It requires an OSI-approved license and a public development history,
so it cannot be an automatic downstream target of the current licensing. Decide
it as its own question, after the repository has accumulated real public
history — not as a consequence of this release.
