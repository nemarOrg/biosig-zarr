# Changelog

All notable changes to the specification are recorded here, newest first.
The versioning scheme is in [`GOVERNANCE.md`](GOVERNANCE.md).
A release is a Git tag made by the editor.

## 2.0.2

Editorial: no change to what conforms.
The normative text, the JavaScript Object Notation (JSON) Schemas, and the conformance vectors are those of `2.0.1`.

- The specification is independent of the Neuroelectromagnetic Data Archive and Tools Resource (NEMAR),
  and the copyright holder of its text is the biosig-zarr contributors;
  Architecture Decision Record (ADR) 0005 records the decision and how ADRs 0001 to 0004 read in its light.
- NEMAR is named only as the text's origin (first published on docs.nemar.org), as its first implementer and the profile it defines, as the source of the recording the vectors are cut from,
  and as the host of the repository and of the venue for Requests for Comments (RFCs), nemarOrg/rfcs.
- `GOVERNANCE.md` names the editor, Seyed Yahya Shirazi, in a personal capacity, says that an RFC about this specification is decided by its editor and that hosting gives no say over the text,
  and, with `README.md`, gains a section on hosting and continuity.
- `README.md` states the current status: releases are tags made by the editor, and `schemas/` and `conformance/` hold the format version 2 schemas and vectors since `2.0.1`.
- The editor's ruling: `GOVERNANCE.md` makes a change that alters who decides normative.
  On 2026-11-20 the editor ruled this change editorial, because the same person stays editor, RFCs stay in nemarOrg/rfcs, and nothing that conforms changes.

## 2.0.1

Editorial: no change to what conforms.

- JavaScript Object Notation (JSON) Schemas for format version 2, one per metadata document, in `schemas/v2/`: `root`, `uniform-group`, `level0-array`, `view-array`, and `events-group`.
- The first conformance vectors, in `conformance/`: six format version 2 stores cut from one recording dedicated to the public domain (Creative Commons CC0 1.0),
  dataset `on009081` of the Neuroelectromagnetic Data Archive and Tools Resource (NEMAR), and written by biosigIO 1.2.13,
  with their manifest, goldens, and sources;
  and the checks that run them, `tools/check-schemas.ts` and `tools/vectors/`.
- The editor's ruling: `GOVERNANCE.md` makes any change to a JSON Schema normative and lets the editor decide what is normative.
  On 2026-11-20 the editor ruled that these first version 2 schemas and vectors are editorial, because they transcribe the `2.0.0` text and add no requirement to it.

## 2.0.0

Format version 2, moved from docs.nemar.org with no normative change.
Four parts the text marks Proposed are not yet implemented in NEMAR's stores: the `biosig-zarr` tag inside stores, `.bzx`, `generated_by`, and the conformance classes.

- The repository is initialized: licenses, governance, contribution terms, decision records, and checks on the text.
- A check, `tools/check-moved-text.ts`, compares the word sequence of the specification text with its earlier copy on docs.nemar.org.
- ADR 0004 records the identifier of the biosig-zarr Zarr convention.
