# biosig-zarr Development Plan

## Project overview

**Goal:** a specification repository for biosig-zarr, a Zarr version 3 layout for one biosignal recording, and its single-file form `.bzx`: normative text, JSON Schemas, conformance vectors.
It holds no reader or writer library.
**Stack:** Markdown, JSON; Bun and Biome for JSON tooling; Python (uv, Ruff, ty, pytest) only when the conformance runner arrives.

## Tasks

<!-- Status markers: [ ] pending, [~] in progress, [x] complete -->

- [x] Repository initialized: licenses, governance, contribution terms, decision records, checks on the text
- [ ] The specification text moves from docs.nemar.org into `spec/index.md`, with no normative change
- [ ] First release, `2.0.0`, tagged by the editor
- [ ] The version 3 text that RFC-0001 proposes, on `draft/3.0.0`, tagged `3.0.0-draft.1`
- [ ] JSON Schemas for every attribute object, published at a stable address
- [ ] Conformance vectors from real recordings under a public-domain dedication
- [ ] RFC-0001 (in nemarOrg/rfcs) accepted

## Beta criteria

Recorded in neuromechanist/biosigio#179 ("What beta means"); all five must hold:

1. Nothing in the specification is marked "Proposed" without an implementation behind it.
   The `biosig-zarr` name is written by a released biosigIO, and `.bzx` packing and unpacking exist.
2. A JSON Schema for every attribute object is published at a stable address, and validates every test vector and a sample of production stores.
3. Test vectors are published, and two readers that share no code pass them.
   At least one of the two was written or checked against the specification text, not against biosigIO.
4. The license of the text, schemas, and vectors is stated, and a one-page change process exists.
5. Every open question in the text is resolved, deferred past beta with a reason, or rejected.

## Notes

- Specification decisions are recorded in `decisions/`; NEMAR profile and rollout decisions are recorded in nemarOrg/nemar-cli.
- Labels, tags, releases, and repository settings are the editor's acts.
