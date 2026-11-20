# ADR 0003: Requests for Comments live in nemarOrg/rfcs

**Status:** accepted
**Date:** 2026-11-20
**Owner:** Seyed Yahya Shirazi

## Context

A change to what a conforming writer or reader must do binds people outside the Neuroelectromagnetic Data Archive and Tools Resource (NEMAR), so it goes through a Request for Comments (RFC) with a fixed comment window and a written decision.
NEMAR recorded in its Architecture Decision Record (ADR) 0130, "Community input goes through a time-boxed RFC" (nemarOrg/nemar-cli), that it adopts one public repository, nemarOrg/rfcs, as the home of every RFC and of one number space.
The first RFC, RFC-0001, covers the whole biosig-zarr format and its single-file form `.bzx`.
An earlier plan kept RFC documents in an `rfc/` directory of this repository.

## Decision

RFC text and its comment threads live in nemarOrg/rfcs, not here.
This repository has no `rfc/` directory; the README links to nemarOrg/rfcs.
A normative change to the specification needs an accepted RFC there (see `GOVERNANCE.md`).
The text an RFC proposes lives on a branch of this repository, tagged `-draft.N`, until the RFC is accepted.
Each ADR here that an RFC produced links that RFC.

## Consequences

- One place to comment and one numbering, whether the RFC concerns the specification or something else NEMAR decides.
- This repository does not duplicate RFC text, so there is no second copy to drift.
- A reader of the specification must follow a link to see the RFC history, and the RFC links back to the tagged text.
- The 21-day window, the extension rule, and the one-open-RFC rule are defined by the process in nemarOrg/rfcs and are not restated here.

## Alternatives considered

- **An `rfc/` directory here:** rejected; it splits the number space and the comment venue across repositories.
- **Discussions in this repository:** rejected; the owner decided one home for all comment threads.

## Receipts

- NEMAR ADR 0130 (content: RFCs live in one public repository, with a time-boxed window) and the ADR that records the biosig-zarr home: ADR 0131, "biosig-zarr has its own home and packing rules, and its tag rename waits for re-conversion" (nemarOrg/nemar-cli).
- <https://github.com/nemarOrg/rfcs>
