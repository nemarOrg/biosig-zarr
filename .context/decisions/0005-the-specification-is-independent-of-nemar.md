# ADR 0005: The specification is independent of NEMAR

**Status:** accepted
**Date:** 2026-11-20
**Owner:** Seyed Yahya Shirazi

## Context

The biosig-zarr text was first written for the Neuroelectromagnetic Data Archive and Tools Resource (NEMAR), its first implementer, and first published on docs.nemar.org;
the first files of this repository, in the nemarOrg GitHub organization, named NEMAR as the party that set the licenses, held the copyright and supplied the editor.
On 2026-11-20 the text's author, who is its editor, made the specification independent of NEMAR, because a format that one archive decides gives other implementers no say.
`GOVERNANCE.md` makes normative a change that alters who decides, which needs an accepted Request for Comments (RFC);
here the editor stays the same person and RFCs stay in nemarOrg/rfcs.
Architecture Decision Records (ADRs) 0001 to 0004 predate this change, and this repository's convention allows no edit to an ADR except its status.

## Decision

1. The specification is independent of NEMAR, and the copyright holder of its text is "the biosig-zarr contributors".
2. NEMAR appears in this repository only as the text's origin (first published on docs.nemar.org), as its first implementer and the profile it defines, as the source of the recordings the conformance vectors are cut from, and as the host of this repository and of the RFC venue, nemarOrg/rfcs.
3. The editor named in `GOVERNANCE.md` decides.
   The editor ruled this change editorial, because the editor and the RFC venue stay as they were and nothing that conforms changes, as was ruled for `2.0.1`.
4. ADRs 0001 to 0004 stand as written.
   Where they say that NEMAR or "the owner" decided, that is the history of where the text came from, and "the owner" there is the text's author, who is the editor.
5. NEMAR hosts the repository and registers its Digital Object Identifiers (DOIs), through nemar-doi, as a service, not as ownership.
   It is ready to hand the specification off once it matures; until then it backstops the specification and guarantees that it continues, while decisions stay with the editor, through RFCs.
6. Nothing is superseded.
   A later move of the RFC venue or of the repository supersedes ADR 0003 in a new ADR.

## Consequences

- Another implementer can adopt the format without depending on the archive that wrote it first: `GOVERNANCE.md` says who decides, and it is not NEMAR.
- The holder line names the people who wrote the text, which fits contributions signed off under the Developer Certificate of Origin with no contributor license agreement: no organization collects the copyright.
- The published tags `2.0.0`, `2.0.1`, `3.0.0-draft.1` and `3.0.0-draft.2` keep their earlier wording, because a published tag is immutable.
  The change reaches a release as `2.0.2`, and `draft/3.0.0` takes it in for its next draft tag.
- The independence is one of decision, not yet of infrastructure: the repository, the RFC venue and the DOIs still rely on NEMAR's services until the hand-off.
- The editor is one person, so continuity rests on NEMAR's backstop until a second institution co-maintains the format and it gets an organization of its own.
- A reader of ADRs 0001 to 0004 reads them through decision 4.

## Alternatives considered

- **Keep NEMAR as the decider:** rejected; it ties a format meant for the whole biosignal community to one archive, and gives other implementers no say.
- **Move to an organization of its own now (Q41, option B):** rejected for now; no second institution co-maintains the format yet, and a move breaks addresses and moves the venue without changing who decides.
- **A separate RFC for the governance change (Q39, option B):** rejected; the editor and the venue stay as they were, so who decides does not change in practice, and with one RFC open for comment at a time it would delay RFC-0001.

## Receipts

- Owner decision on 2026-11-20, recorded on the RFC program board as questions Q37 and Q38 (biosig-zarr is independent of NEMAR, and the copyright holder of its text is the biosig-zarr contributors),
  with the answers to Q39 (the editor, and the ruling that the change is editorial), Q40 (the RFC venue), Q41 (the repository's home) and Q42 (release DOIs through nemar-doi), each option A.
- NEMAR ADR 0131, "biosig-zarr has its own home and packing rules, and its tag rename waits for re-conversion" (nemarOrg/nemar-cli).
