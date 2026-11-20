# ADR 0002: No reader or writer library in this repository

**Status:** accepted
**Date:** 2026-11-20
**Owner:** Seyed Yahya Shirazi

## Context

The Neuroelectromagnetic Data Archive and Tools Resource (NEMAR) specified, in its Architecture Decision Record (ADR) 0128, "The Zarr serving copy is not an NWB container" (nemarOrg/nemar-cli), the layout as its own format, `biosig-zarr`, with biosigIO as one exemplar implementation and not its definition.
The format's beta criteria (neuromechanist/biosigio#179) require two readers that share no code, at least one written or checked against the specification text and not against biosigIO.
The packing and unpacking functions for the single-file form `.bzx` are planned in biosigIO, and TypeScript reading in nemar-cli.
A specification repository could also host a reference library, which is convenient and which is how a library silently becomes the definition.

## Decision

This repository holds the normative text, the JSON Schemas, the conformance vectors, and only the tools needed to check them.
No reader or writer library lives here.
Reference implementations live in their own repositories and are held to the conformance vectors.

## Consequences

- The text stays implementable on its own; where a program and the text disagree, the text is right.
- Two independent implementations are forced to agree through the vectors, not through shared code.
- Conformance vectors are canonical here, and a repository that holds a reader vendors them by digest.
- Anyone who wants a library must look elsewhere, and the README points them there once one exists.
- A later decision to host library code here needs a new ADR that supersedes this one.

## Alternatives considered

- **A reference reader and writer in this repository:** rejected; it becomes the definition in practice, and the beta criterion of two readers sharing no code becomes harder to show.
- **Make biosigIO the definition:** rejected by ADR 0128; biosigIO is one exemplar, and it is the only writer today.

## Receipts

- NEMAR ADR 0128 (content: biosigIO is one exemplar implementation, not the format's definition) and neuromechanist/biosigio#179: <https://github.com/neuromechanist/biosigio/issues/179>.
