# Specification Style

This repository's product is text.
These rules apply to `spec/`, to every document that quotes or proposes specification text, and to the other Markdown files.
In this repository, a Request for Comments (RFC) is a proposal of the Neuroelectromagnetic Data Archive and Tools Resource (NEMAR), decided in nemarOrg/rfcs.

## Key words

- Requirements use the key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY, in capitals, as defined in RFC 2119 and clarified by RFC 8174.
  Those two are documents of the Internet Engineering Task Force (IETF) and are separate from the NEMAR RFC process.
  The text says so once, in its terminology section.
- Never use the capitalized words for anything but a requirement.
  A sentence that describes without requiring uses plain lowercase verbs.
- A requirement that applies only in some cases says so with the word CONDITIONAL in the text that introduces it, and states the condition.
- State each requirement once, in one place, so that a conformance vector can cite it.
  Other places link to it and do not restate it.

## Prose

- American English: normalization, behavior, analyze, labeled, center, gray, license.
  Quoted external text and identifiers keep their original spelling.
- Avoid em-dashes; commas and semicolons are usually enough.
- Use semantic line breaks: one sentence per line, and a break after clause punctuation (`,` `;` `:`) in a long sentence.
  Blank lines separate paragraphs only.
  Do not hard-wrap for width, and do not fragment into bare phrases.
- Define an abbreviation before using it: spell out the full form on first use in a document, once, then use the short form.
  Never use an abbreviation before its definition.
- Examples beat explanation.
  Each example is a real object from a real recording, or is labeled as illustrative and shown valid by a check.

## Structure

- Normative text and non-normative text are separate, and each non-normative block is labeled (Note, Example, Rationale).
- Every JSON block in the text is valid JSON, and a block that claims to be an instance is valid against its schema.
- Link to the tagged copy of the text from other documents; never copy it.
- A heading is a stable anchor: do not rename one without a reason, because links and conformance vectors cite it.

## Text posted to GitHub

Pull-request bodies, comments, and reviews render every newline as a line break.
Keep each paragraph and list item on one line there, with blank lines between paragraphs only.

## Checks

`uvx typos .` checks spelling, lychee checks links, and `bun run lint` checks the JSON files (see `ci_cd.md`).
A word the spell checker does not know goes in `_typos.toml` only when it is a real term of the format, never to silence a mistake.
