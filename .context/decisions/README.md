# Architecture Decision Records

Architecture Decision Records (ADRs) capture significant decisions about the specification: scope, license, structure, trade-offs accepted, alternatives rejected.
Decisions about NEMAR's profile of the format and its rollout are recorded in nemarOrg/nemar-cli; an ADR here that an RFC produced links that RFC.

## Convention

- One file per decision: `NNNN-short-kebab-title.md`, zero-padded to four digits.
- `0000-template.md` is the template; copy it to start a new ADR. Do not edit `0000-template.md` itself.
- Number sequentially; the next ADR is `0004`.
- Status flows `proposed` -> `accepted` -> (later) `superseded by ADR-NNNN`. Never delete an ADR; supersede it.
- Keep each ADR short. If it grows past two screens, you are probably writing a design doc, not a decision.

## When to write an ADR

Write one when a decision:
- Will be hard or expensive to reverse.
- Cuts off other reasonable paths a future contributor might wonder about.
- Has been argued about more than once.
- Embeds a constraint (legal, performance, schedule) that is not obvious from the code.

Do not write one for routine choices that are obvious from reading the code.

## Index

Add new entries here as you create ADRs:

- ADR 0000 - template (do not edit)
- [ADR 0001](0001-license-and-contribution-terms.md) - License and contribution terms
- [ADR 0002](0002-no-reader-or-writer-library-in-this-repository.md) - No reader or writer library in this repository
- [ADR 0003](0003-rfcs-live-in-nemarorg-rfcs.md) - Requests for Comments live in nemarOrg/rfcs
