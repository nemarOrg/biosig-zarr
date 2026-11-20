# Testing Standards

This repository has no code yet, so its "tests" are the checks on the text and, later, the conformance vectors.
The rule that governs both is: test reality, not fiction.

## Real data only

- A conformance vector is cut from a real recording whose source dedicated it to the public domain (Creative Commons CC0 1.0).
  Record the source beside the vector.
- An invalid vector is a real file altered to break exactly one rule, and the manifest names the rule it breaks.
- Never generate a synthetic recording, never add a mock or a stub, and never add data under another license.
- If real data for a case is not available, write no vector for it and say so in the pull request.
  No vector is better than a fake one that passes.

## A check that cannot fail proves nothing

Before a check is trusted, break the rule it enforces and confirm the check fails.
For a vector, turn the rule off in the implementation under test and confirm the matching invalid vector then passes wrongly.

## What exists now

| Check | What it proves |
| --- | --- |
| `uvx typos .` | No known misspelling in the text |
| lychee | Every link in the Markdown resolves |
| `bun run lint` | The JSON files are well formed and formatted |

Schemas and vectors arrive in a later change; when they do, add their checks here, each with the way it can fail.

## Tools

- JSON and JavaScript tooling: Bun and Biome.
- Python, when the conformance runner arrives: uv, `pytest`, Ruff, and ty; never pip or conda.
