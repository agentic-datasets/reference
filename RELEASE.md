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

- [x] **Moved to the `agentic-datasets` organization 2026-09-02**, as
      `agentic-datasets/reference`; the programme description moved with it as
      `agentic-datasets/programme`. Done while the release candidate was hours
      old and before PyPI, `v0.1.0` and any DOI — those are what make a
      namespace expensive to change, and none of them existed yet.

      The `ok-` prefix was dropped with the move. It encodes public-versus-
      private *within the personal account* and carries no information inside a
      single-purpose organization.

      GitHub redirects the old repository URLs, and the old names cannot be
      taken by anybody else, since only their former owner can create
      repositories in that account. **Pages URLs do not redirect.** The
      documentation address is now
      <https://agentic-datasets.github.io/reference/>; the previous one, live
      for a few hours, is dead and was never cited.

      `CITATION.cff`, both package `pyproject.toml` files, `docs-site/book.toml`
      (including `site-url`), `docs-site/build.py` (its two constants *and* the
      absolute-link regex) and the hand-authored pages were swept together, the
      chapters regenerated, and the two publishable wheels rebuilt so their
      `Homepage` metadata does not immortalise the old URL on PyPI.

      This entry is the record; the entries above it are left as they were
      written and describe the identity at the time.

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

      **Prepared 2026-09-06 in [`zenodo/`](zenodo/README.md), and the open
      question is answered.** Verified against the live Zenodo API: all four
      licence identifiers — `cc-by-4.0`, `cc0-1.0`, `apache-2.0` and
      `busl-1.1` — exist in Zenodo's vocabulary. `busl-1.1` was the one in
      doubt, since BSL is not an OSI licence; it is present, so the record can
      state all four in the machine-readable `rights` field and needs no custom
      free-text entry.

      **The instrument changes as a result.** `rights` is a list on the REST
      API and a single `license` string in the `.zenodo.json` GitHub
      integration, so the record is created through the API and **there is
      deliberately no `.zenodo.json` in this repository** — if the integration
      were ever switched on, one would silently override a correct record with
      a single-licence one. Its absence is the control, which is worth saying
      because an absent file looks like an oversight.

      Still to verify **on the rendered draft**, not in the payload:
      - that all four licences appear in the Rights section as displayed, not
        merely that the JSON was accepted;
      - that **Zenodo ignores `CITATION.cff` entirely when `.zenodo.json` is
        present** — they do not merge, so every creator, ORCID, version and
        related-identifier field has to be duplicated correctly into
        `.zenodo.json`;
      - the Rights section of the draft record, read in full, before publish.
      - that Zenodo can see the repository at all: its GitHub integration is
        an OAuth app, and an organization may restrict third-party access.

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
- [x] **Tagged `v0.1.0-rc.2` 2026-09-02.** `rc.1` names a tree whose
      `CITATION.cff` points at the personal namespace, which is no longer where
      the repository is. A candidate exists to be cited, so the citable tag
      should not require a redirect to resolve.

      It also carries the first green `conformance` run. Every run of that
      workflow since it was added had failed at its first step -- a guard using
      `importlib.util.find_spec("google.adk")`, which raises rather than
      returning `None` when `google` is absent, so it broke exactly when its
      condition held. The two steps below it, which run the suite from an
      unrelated directory with no implementation installed and export the
      vectors, had therefore never executed. They are the clean-room evidence
      for claim 3, and CI now reproduces 17/17 target detection and 15/15
      coverage from an environment holding nothing but the harness.

      The two package versions stay at `0.1.0rc1`: they are separate
      distributions with their own numbering, and neither has been published.
- [x] **Paper publication status re-checked 2026-09-06 — it had gone stale, as
      predicted.** Two of the three are now in published proceedings, verified
      against Crossref:

      | Venue | DOI | Pages |
      |---|---|---|
      | IEEE CCECE 2026 | `10.1109/CCECE68150.2026.11610344` | 326–332 |
      | IEEE BigDataService 2026 | `10.1109/BigDataService70481.2026.00025` | 125–129 |

      `docs-site/pages/citation.md` carried "none is in published proceedings
      yet, so there are no DOIs to cite" for both of them. Corrected, and the
      two DOIs are now `issupplementto` related identifiers on the Zenodo
      record. IEEE EMBC 2026 has not appeared and is marked as awaiting
      proceedings.

      **Re-check once more immediately before `v0.1.0`.** This is the same
      failure a second time, not a one-off: nothing in the repository fails
      when a paper appears, so the claim decays silently and the only defence
      is to look. EMBC is the entry that will go next.

- [x] **Published the two permissive distributions to PyPI — 2026-09-06.**
      <https://pypi.org/project/agentic-dataset-conformance/0.1.0rc1/> and
      <https://pypi.org/project/authorized-recall/0.1.0rc1/>, each as wheel and
      sdist. Both names were free and are now held. The reference
      implementation is **not** published: it is BUSL-1.1.

      Verified before upload rather than after, because a version number cannot
      be reused once taken and yanking does not remove it: 186 tests pass,
      `twine check` passes on all four artifacts, and both console scripts run
      from a clean-room venv holding nothing but the two wheels.

      **One metadata fix went in first.** The packages carried `Homepage` and
      `Source` but no `Documentation` URL, and the last packaging sweep predates
      the domain by a day — `agenticdatasets.org` went live 2026-09-03, the
      wheels were last built 2026-09-02. Package metadata is immortal per
      version, so a `Documentation` entry pointing at
      <https://agenticdatasets.org/reference/> was added to both before the
      build. This is the same failure the 2026-09-02 entry above guarded
      against, one address later.

      Installing needs `--pre`, or a specifier that names a pre-release:
      `pip install --pre agentic-dataset-conformance`. That is the same trap the
      root `pyproject.toml` already documents for its own dependency pins.

- [x] **`0.1.0rc2` published — 2026-09-06, the same day, to correct a frozen
      description.** <https://pypi.org/project/agentic-dataset-conformance/0.1.0rc2/>
      and <https://pypi.org/project/authorized-recall/0.1.0rc2/>.

      `rc1` shipped with `packages/agentic-dataset-conformance/README.md` still
      reading *"Not yet on PyPI during the release candidate; install from a
      clone until it is"* — directly beneath a working `pip install` command,
      on the page a stranger arriving through pip sees first. Seven files in
      the repository carried that claim; this one was the package long
      description, and a description is frozen with its version, so the repo
      and the site could be corrected in place and the package page could not.

      **The lesson is narrow and worth stating.** Pre-upload verification
      covered the metadata *fields* — name, version, licence, URLs, entry
      points, a clean-room install — and not the prose inside the README that
      becomes the page body. Those are the same artifact to PyPI and were two
      different checks here. For `v0.1.0`, read the rendered description, not
      only the header.

      `rc1` remains on PyPI as a superseded pre-release, which is what
      release-candidate numbering is for. Both package versions moved together
      even though only one carried the stale line: they are released as a pair,
      and a version skew between them would cost more than the bump saved.
- [ ] Invite a second implementation rather than writing one. The toy
      establishes independence from the reference *code*; only somebody else's
      reading establishes independence from the author's interpretation of the
      contract. That is the next validation threshold, and writing a third
      implementation here would not cross it.
- [x] **Own domain, 2026-09-03 — <https://agenticdatasets.org/>.** The
      documentation address above is superseded. `agenticdatasets.org` was
      registered that morning and its A records already pointed at the Toronto
      edge, so the domain is served by Caddy there rather than by GitHub Pages —
      one tree, with the org site at the apex, `/showcase/` and `/reference/`
      beneath it. No path rewriting was needed because the three builds already
      agree on their base paths.

      GitHub Pages still serves the same content at the old address and is not
      disabled. It cannot serve the domain, because DNS points elsewhere, so
      there is no redirect between them: the two are independent copies.

      **DECIDED 2026-09-06 — both stay up, and each now names the other.**
      Pages is a standby rather than a leftover: the mirror exists so the
      documentation stays reachable if the domain does not. The README and the
      documentation home both carry a two-row table marking
      `agenticdatasets.org` **canonical** and the Pages address a **mirror**,
      with the instruction to prefer the domain in anything durable — a
      citation, a DOI, a paper — because it survives a change of hosting. The
      text reads correctly from either address, which it has to: one build is
      deployed to both, so there is no per-address copy to diverge.

      **A claim in this entry was wrong and is corrected.** It said "the
      canonical tags name `agenticdatasets.org`". There are no canonical tags:
      neither address emits `<link rel="canonical">`, verified against both
      live sites on 2026-09-06. Emitting real per-page ones is not free —
      mdbook's `head.hbs` exposes `{{ path }}` as `citation.md` and has no
      string-replace, so a correct tag needs a post-build pass wired into both
      the Makefile and the Pages workflow, which is two places to keep in step
      in a repository whose CI exists to catch exactly that drift. **Left
      undone deliberately, and recorded rather than asserted.** The visible
      cross-link is what a reader needs; the tag is what a crawler needs, and
      only the first is claimed.

      `make deploy` publishes the book to the edge. Pages rebuilds on push; the
      edge does not, so a docs change is live in one place before the other
      until someone runs it.

- [x] **A second language, 2026-09-03 — and it does not close the item above.**
      `agentic-datasets/showcase` runs the same CC0 vectors against a TypeScript
      subject and reports 15/15 assertions, 77 observations and 0/39 prohibited
      executions: identical to Python, with byte-identical vectors and no shared
      runtime. `docs/CLAIMS.md` claim 4 is extended accordingly.

      It is a transcription of `toy.py` by the same author, so it is evidence of
      **language** neutrality and not of **interpretive** independence. Do not let
      it be read as satisfying the invitation above; claim 6 is untouched.

- [x] **`0.1.0` published to PyPI and tagged `v0.1.0` — 2026-09-06.**
      <https://pypi.org/project/agentic-dataset-conformance/0.1.0/> and
      <https://pypi.org/project/authorized-recall/0.1.0/>. `--pre` is no longer
      needed anywhere and has been removed from every install instruction; the
      root distribution's dependency pins are plain lower bounds again, and the
      comment explaining the pre-release trap now records it as past rather
      than current.

      **The rc1 lesson was applied.** Before uploading, the rendered
      description *body* was scanned for stale phrasing — "not on PyPI",
      "--pre", "release candidate", "install from a clone", any `0.1.0rc` — and
      not merely the metadata header. Zero hits on both packages. That is the
      check whose absence cost an `rc2`.

      Note for whoever publishes next: PyPI's JSON API and `/simple/` index lag
      the upload by minutes. `pip install` resolved the previous version twice
      while the project page for the new one already returned 200. The upload
      is not broken; the CDN is cold.

- [ ] Archive that exact tag on Zenodo. **Zenodo publication is
      irreversible** — read the whole draft record, Rights included, in the
      same sitting as pressing publish. Metadata is prepared in
      [`zenodo/`](zenodo/README.md).
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
