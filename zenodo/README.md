# Zenodo record preparation

The metadata for the `v0.1.0` archive, and the reason it is not built the
obvious way.

## Do not use the GitHub integration for this record

Zenodo's GitHub integration reads `.zenodo.json`, whose schema carries a
**single** `license` field. This release has **four** rights regimes, so any
record created that way is wrong before anybody looks at it:

- `"BUSL-1.1"` would wrongly imply BSL covers the vectors and the conformance
  software, both of which are freely reusable;
- `"Apache-2.0"` would wrongly imply the reference implementation is permissive,
  which is the worse error of the two — it invites exactly the commercial use
  the licence withholds until 2029-09-02.

**There is deliberately no `.zenodo.json` in this repository.** Adding one would
not merely be unused; if the GitHub integration is ever switched on it would
silently override a correct record with a single-licence one. Its absence is the
control.

## Use the REST API, where `rights` is a list

Verified against the live Zenodo API on 2026-09-06: **all four licence
identifiers exist in Zenodo's vocabulary**, which was the open question.

| Tier | Licence | `rights` id | In vocabulary |
|---|---|---|---|
| Specification and normative prose | CC-BY-4.0 | `cc-by-4.0` | yes |
| Normative worlds and vectors | CC0-1.0 | `cc0-1.0` | yes |
| Conformance software · `authorized_recall` | Apache-2.0 | `apache-2.0` | yes |
| Reference implementation | BUSL-1.1 → Apache-2.0 on 2029-09-02 | `busl-1.1` | yes |

`busl-1.1` was the one genuinely in doubt, since BSL is not an OSI licence.
It is present, so no custom free-text right is needed and the record can state
all four in the machine-readable field rather than only in prose.

[`metadata.json`](metadata.json) holds the record body. `LICENSE.md` in the
archived tree stays authoritative for the file-to-licence map; the four
identifiers say *which* licences apply, not *to what*, and no metadata field can
carry that mapping.

## Sequence

`RELEASE.md` fixes the order, and it is not negotiable at the last step:

    RC public → scrutiny → tag v0.1.0 → create the record → verify Rights → publish

**Zenodo publication is irreversible.** Read the whole draft record — Rights
included, rendered rather than as JSON — in the same sitting as pressing
publish. A record asserting one licence over a four-regime artifact is not
something to fix afterwards.

Two things to confirm on the draft before publishing, because neither is
guaranteed by the payload being correct:

1. all four licences appear in the rendered Rights section, not just the first;
2. `version` matches the tag exactly — `metadata.json` pins `0.1.0`, and it
   must be bumped in step with any retag rather than left behind.

## What is not archived here

The technical report is a separate repository with its own DOI, which cites the
software DOI. Do not vendor a `paper/` directory into this repo: the software
artifact and the scholarly artifact should not become version-coupled.
