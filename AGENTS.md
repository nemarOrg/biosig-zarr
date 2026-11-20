# biosig-zarr: Development Instructions

> Project instructions for any coding agent and for people.
> Claude Code reads this through `@AGENTS.md` in `CLAUDE.md`.

This is the specification repository for biosig-zarr, a Zarr version 3 layout for one biosignal recording, and its single-file form `.bzx`: normative text, JSON Schemas, conformance vectors.
It holds no reader or writer library.
Requests for Comments (RFCs) live in nemarOrg/rfcs, not here.
**This file is the hard rules**: what can go wrong here and is not obvious from the files.
Who decides and how releases are tagged are in [`GOVERNANCE.md`](GOVERNANCE.md); the licenses are in [`LICENSE.md`](LICENSE.md).

## Hard rules

### Published tags and accepted RFCs are immutable

Never move, delete, or re-create a published tag, and never edit an accepted RFC.
A mistake is fixed in the next release or by a superseding RFC.
Only the owner tags and releases; no agent creates a tag, a release, a label, or a repository setting.

### A normative change needs an accepted RFC

A change to what a conforming writer or reader must do, and any change to a schema, is normative and needs an accepted RFC in nemarOrg/rfcs.
Only editorial changes (spelling, links, formatting, clarifications that leave the meaning unchanged) go by pull request alone.
When it is unclear which, it is normative.
`main` carries only accepted text; the text an RFC proposes lives on a branch (for example `draft/3.0.0`) and is tagged `-draft.N` (see `GOVERNANCE.md`).

### No reader or writer library lives here

The text is the definition.
A library in this repository would become the definition in practice.
Reference implementations live in their own repositories and are held to the conformance vectors.
Tools here are limited to what checks the text, the schemas, and the vectors.

### Vectors come from real recordings, dedicated to the public domain

A conformance vector is cut from a real recording whose source dedicated it to the public domain (Creative Commons CC0 1.0), and its source is recorded.
An invalid vector is an altered real file.
Never generate a fake recording, and never add data under any other license.

### One canonical copy of the text

The specification text has one editable copy, `spec/index.md` here.
docs.nemar.org links to it and never copies it; two copies drift.
Never paste normative text into another document: link the tagged copy.

### Decisions are recorded where they belong

Specification decisions are Architecture Decision Records (ADRs) in [`.context/decisions/`](.context/decisions/README.md); copy `0000-template.md`, number sequentially, add it to the index, and never edit or delete an accepted one (supersede it).
NEMAR profile and rollout decisions belong in nemarOrg/nemar-cli.
Each ADR that an RFC produced links that RFC.

## Tooling is fixed

**Bun** for JavaScript and JSON tooling, never npm or npx. **Biome** for JSON lint and format, never ESLint or Prettier. **uv** for anything Python, never pip or conda (no Python lives here yet).
Gates: `uvx typos . && bun install && bun run lint`.
Link checking (lychee) runs in continuous integration (`.github/workflows/text.yml`).

## Writing

The text follows [`.rules/documentation.md`](.rules/documentation.md): RFC 2119 key words, semantic line breaks, abbreviations defined once, American English, no em-dashes.
Commit subjects are under 50 characters, with no emojis and no AI or co-author attribution; commits are signed off (`git commit -s`, see `CONTRIBUTING.md`).
Text posted to GitHub (pull-request bodies and comments) keeps each paragraph on one line.

## Where everything else lives

- **Standards:** [`.rules/`](.rules/) (`git`, `code_review`, `testing`, `documentation`, `ci_cd`, `self_improve`).
- **Plans and research:** `.context/plan.md`, `.context/ideas.md`, `.context/research.md`, `.context/scratch_history.md`.
- **Observations:** [`.memory/`](.memory/README.md), one per file, binding nobody (an ADR is a ruling, a `.context/` document an argument, a memory an observation).
