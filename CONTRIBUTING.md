# Contributing

Thank you for helping with the biosig-zarr specification.
The organization's code of conduct and security policy apply here; they are inherited from the nemarOrg organization, which hosts this repository.

## What to send, and where

| You want to | Do this |
| --- | --- |
| Fix a typo, a broken link, or an unclear sentence that does not change what conforms | Open a pull request, or an issue if you prefer; this is an editorial change |
| Report an error in the text, or a place where two readers could disagree | Open an issue with the defect template |
| Ask how something is meant to work | Open an issue with the question template |
| Change what a conforming writer or reader must do, add a feature, or change a schema | Propose a Request for Comments (RFC) in [nemarOrg/rfcs](https://github.com/nemarOrg/rfcs); a normative change needs an accepted RFC |
| Comment on an RFC that is open | Post in its Discussion thread in nemarOrg/rfcs |

If you are unsure whether a change is normative, ask in an issue first.
When in doubt, it is normative.
[`GOVERNANCE.md`](GOVERNANCE.md) defines the two kinds and who decides.

## Contribution terms: sign off your commits

This repository uses the Developer Certificate of Origin (DCO), version 1.1, published at <https://developercertificate.org/>.
By signing off a commit you certify that you wrote the contribution, or otherwise have the right to submit it under the license of the part it touches.
Contributions are licensed under that same license, so inbound equals outbound: text under the World Wide Web Consortium (W3C) Software and Document License, and schemas, vectors, tools, and code under the Apache License 2.0.
[`LICENSE.md`](LICENSE.md) lists which files fall under which license.
There is no contributor license agreement.

Sign off with `git commit -s`, which adds this line to the commit message, using your real name and an email address you control:

```text
Signed-off-by: Your Name <you@example.org>
```

A reviewer checks the line on every commit of a pull request; a commit without it is amended before merge.

## Writing the text

- Use the key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY as defined in RFC 2119 and RFC 8174, in capitals, and only for requirements.
- Write American English, and avoid em-dashes.
- Spell out an abbreviation the first time it appears in a document, once, and use the short form afterward.
- Put one sentence on each line, and break longer sentences at clause punctuation (semantic line breaks).
- Do not copy the normative text into another document; link to the tagged copy.

## Checks

A pull request runs three checks, defined in `.github/workflows/text.yml`.
Run them locally first:

```bash
uvx typos .        # spelling
bun install
bun run lint       # Biome over the JavaScript Object Notation (JSON) files
```

The third check is link checking with lychee, which runs in continuous integration.

## Commits and pull requests

- Make atomic commits: one logical change each, with a subject under 50 characters and no emojis.
- Open a pull request against `main`, the only integration branch.
- A pull request gets at most two review rounds.
  Every finding is fixed, or declined with a one-line reason.
- Releases are tags made by the editor; do not tag.
