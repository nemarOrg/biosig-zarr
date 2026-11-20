# Governance

This document says who decides what in this repository, how a change is made, and how releases are tagged.
It is short on purpose: one organization maintains the specification, and the rules are meant to be easy to check.

## Who decides

The owner of the Neuroelectromagnetic Data Archive and Tools Resource (NEMAR) is the editor of the specification.
The editor merges changes, makes releases, and decides whether a change is normative or editorial.
The format gets an organization of its own only when a second institution co-maintains it; this repository stays under nemarOrg until then.

## Two kinds of change

A **normative** change alters what a conforming writer MUST, SHOULD, or MAY write, or what a conforming reader MUST accept or refuse.
Any change to a JavaScript Object Notation (JSON) Schema is normative.
An **editorial** change does not alter what conforms: spelling, links, formatting, and clarifications that leave the meaning unchanged.
When the editor and a proposer disagree, or when it is unclear, the change is normative.

- A normative change needs an accepted Request for Comments (RFC) in [nemarOrg/rfcs](https://github.com/nemarOrg/rfcs), which has a fixed comment window and ends in a written decision.
- An editorial change goes by pull request review: one approval from the editor, after the checks pass.
- `main` carries only accepted text.
  The text an RFC proposes lives on a branch until the RFC is accepted; then the branch merges.
- An accepted RFC is immutable.
  A later RFC supersedes it; nobody edits it.

## Tags and releases

A release is a Git tag made by the editor.
A published tag is immutable: a mistake in a release is fixed in the next release, never by moving the tag.

The tag is `<major>.<minor>.<patch>`:

| Part | Meaning |
| --- | --- |
| Major | Equals `format_version`, the integer stored in every store |
| Minor | A normative addition that does not break: every store valid under the earlier release in the same major stays valid |
| Patch | An editorial change only |

A suffix `-draft.N` marks the text an RFC proposes, for example `3.0.0-draft.1`.
Draft text lives on a branch named for the release it proposes, for example `draft/3.0.0`, never on `main`.
The tag of a draft points at a commit on that branch and is published as a pre-release.
When the RFC is accepted, the branch merges and the release is tagged without the suffix.

The first release is `2.0.0`: the specification text as moved from docs.nemar.org, for format version 2 as NEMAR's archive serves it, with no normative change.
Its release notes list the parts the text marks as Proposed that are not yet implemented.
The text proposed by RFC-0001 is `3.0.0-draft.1`, on `draft/3.0.0`.

Schemas and conformance vectors are released with the text, under the same tag.

## Identifiers and citation

Each release is intended to receive a Digital Object Identifier (DOI) from NEMAR's DOI registry, which is planned and not yet live.
When a DOI is assigned, it is recorded in `CHANGELOG.md` and in `CITATION.cff`.
A permanent address, `w3id.org/biosig-zarr`, is being registered and will redirect to this repository.

## Where decisions are recorded

- Decisions about the specification itself are Architecture Decision Records (ADRs) in this repository's [`.context/decisions/`](.context/decisions/README.md).
- Decisions about NEMAR's profile of the format and its rollout (conversion, serving, readers) are recorded in nemarOrg/nemar-cli.
- Each ADR that an RFC produced links that RFC, and the ADR wins over the RFC where they disagree.

## Changing this document

A change to this document that alters who decides or how a change becomes normative is itself normative and needs an accepted RFC.
