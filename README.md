# biosig-zarr

biosig-zarr is a Zarr version 3 layout for one biosignal recording, and `.bzx` is its single-file form.
This repository holds the specification: the normative text, the JavaScript Object Notation (JSON) Schemas, and the conformance vectors.
It holds no reader or writer library, so the text stays the definition and no program becomes it.

The format is developed by the Neuroelectromagnetic Data Archive and Tools Resource (NEMAR), whose archive serves its stores today as `format_version` 2.

## Status

The specification text is not here yet.
It was first published on docs.nemar.org, and it moves into [`spec/`](spec/index.md) in the next change to this repository, with no normative change.
The schemas and conformance vectors follow later.
Until a release exists, nothing in this repository is a published version of the specification.

Two identifiers are planned and neither is live:

- A permanent address, `w3id.org/biosig-zarr`, is being registered; it will redirect to this repository.
- Each specification release is to receive a Digital Object Identifier (DOI) from NEMAR's DOI registry, which is still being built.

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

## License

The specification text is under the World Wide Web Consortium (W3C) Software and Document License.
Schemas, conformance vectors, tools, and any code are under the Apache License 2.0.
The details, and the record of the text's earlier license, are in [`LICENSE.md`](LICENSE.md).

## Citing

[`CITATION.cff`](CITATION.cff) holds the citation.
Cite a release by its tag and, once one is assigned, its DOI.
