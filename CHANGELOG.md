# Changelog

All notable changes to the specification are recorded here, newest first.
The versioning scheme is in [`GOVERNANCE.md`](GOVERNANCE.md).
A release is a Git tag made by the editor.

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
