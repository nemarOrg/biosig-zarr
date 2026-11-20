# Changelog

All notable changes to the specification are recorded here, newest first.
The versioning scheme is in [`GOVERNANCE.md`](GOVERNANCE.md).
A release is a Git tag made by the owner.

## Unreleased

- The repository is initialized: licenses, governance, contribution terms, decision records, and checks on the text.
- A check, `tools/check-moved-text.ts`, compares the word sequence of the specification text with its earlier copy on docs.nemar.org.
- ADR 0004 records the identifier of the biosig-zarr Zarr convention.

## 2.0.0

Format version 2, moved from docs.nemar.org with no normative change.
Four parts the text marks Proposed are not yet implemented in NEMAR's stores: the `biosig-zarr` tag inside stores, `.bzx`, `generated_by`, and the conformance classes.
