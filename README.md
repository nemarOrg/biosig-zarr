# biosig-zarr

biosig-zarr is a Zarr version 3 layout for one biosignal recording, and `.bzx` is its single-file form.
This repository holds the specification: the normative text, the JavaScript Object Notation (JSON) Schemas, and the conformance vectors.
It holds no reader or writer library, so the text stays the definition and no program becomes it.

The format was first written for the Neuroelectromagnetic Data Archive and Tools Resource (NEMAR), its first implementer, whose archive serves stores written by biosigIO as `format_version` 2.
The specification is independent of NEMAR; [`GOVERNANCE.md`](GOVERNANCE.md) says who decides.

## Status

The specification text is in [`spec/index.md`](spec/index.md).
It was first published on docs.nemar.org and was moved here with no normative change; it is still pre-beta.
The first release, `2.0.0`, is a Git tag made by the owner; until it exists, nothing in this repository is a published version of the specification.
The schemas and conformance vectors follow later.

Two identifiers are planned and neither is live:

- A permanent address, `w3id.org/biosig-zarr`, is being registered; it will redirect to this repository.
- Each specification release is to receive a Digital Object Identifier (DOI) issued through nemar-doi, the planned DOI service of the NEMAR archive, which registers it and does not own it; the DOI names the authors in `CITATION.cff`.

## What is here

| Path | What it holds |
| --- | --- |
| [`spec/`](spec/index.md) | The normative text of the format and of the `.bzx` form |
| `schemas/` | JSON Schemas for the metadata objects (arrives after the text) |
| `conformance/` | Conformance vectors cut from real recordings (arrives after the schemas) |
| [`GOVERNANCE.md`](GOVERNANCE.md) | Who decides, how a change is made, and how releases are tagged |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | How to report a defect, propose a change, and sign off a contribution |
| [`LICENSE.md`](LICENSE.md) | The three license parts: text, software and schemas, contributions |
| [`CHANGELOG.md`](CHANGELOG.md) | What each release changed |
| [`.context/decisions/`](.context/decisions/README.md) | Architecture Decision Records for the specification |

## How to take part

A change to what a conforming writer or reader must do is a Request for Comments (RFC).
RFCs live in [nemarOrg/rfcs](https://github.com/nemarOrg/rfcs), where each one is open for comment for a fixed, short window.
The first, RFC-0001, covers the whole format and its single-file form.
Comment on an open RFC in its Discussion thread there.

A typo, an unclear sentence, or an error in the text is an issue here; see [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Hosting and continuity

NEMAR hosts this repository and offers its hosting and its DOI registration, nemar-doi, as a service, not as ownership.
The specification is meant to be as independent as possible, and NEMAR is ready to hand it off once it matures.
Until then, NEMAR backstops the specification and guarantees that it continues; decisions stay with the editor, through RFCs, as [Who decides](GOVERNANCE.md#who-decides) says.

## License

The specification text is under the World Wide Web Consortium (W3C) Software and Document License.
Schemas, conformance vectors, tools, and any code are under the Apache License 2.0.
The details, and the record of the text's earlier license, are in [`LICENSE.md`](LICENSE.md).

## Citing

[`CITATION.cff`](CITATION.cff) holds the citation.
Cite a release by its tag and, once one is assigned, its DOI.
