# ADR 0004: The Zarr convention identifier is minted now

**Status:** accepted
**Date:** 2026-11-20
**Owner:** Seyed Yahya Shirazi

## Context

The Zarr conventions mechanism lets a node declare a convention in a `zarr_conventions` attribute array, where each entry is identified by a `uuid`, a `schema_url`, or a `spec_url`.
No central approval is needed, and the `uuid` is the one identifier that does not depend on any address being final.
The permanent address `w3id.org/biosig-zarr` is not yet registered, and the schemas do not exist yet.
The Neuroelectromagnetic Data Archive and Tools Resource (NEMAR) rewrites the root `zarr.json` of every store once, in the migration that renames the format tag.
An identifier that is ready by then can be written in that single pass, and one that is not forces a second pass over every store.

## Decision

The identifier of the biosig-zarr convention is the version 4 UUID `3d7d2fe9-20a5-46d9-a92b-9170cddf6633`, minted on 2026-11-20 with `uuidgen`.
This ADR is its only record in this repository; the moved text of release 2.0.0 does not mention it, because version 2 stores do not carry it.
The writer of format version 3 writes it from its first store.
How a store carries it, and what a reader does with it, is a normative question for RFC-0001 and is not decided here.
The identifier never changes: later releases, a new address, or a new schema location leave it as it is.

## Consequences

- The migration that renames the format tag can write the identifier in the same pass, with no second rewrite of the stores.
- Anyone can cite the convention by `uuid` before `w3id.org/biosig-zarr` exists.
- The identifier is fixed whether or not RFC-0001 is accepted; if the RFC does not use it, it stays reserved and unused.
- This ADR must be kept: it is the only place that ties the `uuid` to biosig-zarr.

## Alternatives considered

- **Mint it with the schemas, later:** rejected; the stores would be rewritten twice, once for the name and once for the identifier.
- **Identify the convention by `spec_url` only:** rejected; the address is not final, and a `uuid` outlives any address.

## Receipts

- Owner decision on 2026-11-20, recorded on the Request for Comments program board as question Q11 (mint now, record in an ADR here).
- The Zarr conventions specification: <https://github.com/zarr-conventions/zarr-conventions-spec>
