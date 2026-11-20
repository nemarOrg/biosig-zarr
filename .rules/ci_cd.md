# CI/CD Workflow Standards

Continuous integration (CI) here checks text and JSON.
The Markdown is the product, so a Markdown change must run the checks; the default template that ignores `**.md` is not used.

## Workflow: `text.yml`

- **Triggers:** `pull_request` and `push` to `main` only, never `on: [push, pull_request]`.
- **Paths:** `**/*.md`, `_typos.toml`, `.github/workflows/text.yml`.
- **Concurrency:** cancel superseded pull-request runs, never a run on `main`.
- **Timeouts:** every job sets `timeout-minutes` (10).
- **Permissions:** `contents: read` and nothing more.
- **Jobs:** spelling (`crate-ci/typos`), link checking (`lycheeverse/lychee-action`), and `bun run lint` (Biome over JSON).
- **Pinning:** every action is pinned to a full commit SHA with its released version in a comment.
  The version of each checker is a released version, never a branch.

## Rules

- One integration branch, `main`; releases are tags made by the owner.
- Required checks and path filters: a skipped workflow leaves a required check pending.
  If a ruleset ever requires a check from `text.yml`, move the path filter into a gate job first.
- Add `[skip ci]` to the subject of a commit that touches only files no job reads (`.context/`, `.memory/`, `.rules/`); never on a pull request with required checks.
- No live services in required checks.
  Link checking reads public pages only, and a link that cannot be public stays out of the Markdown.
- Never commit credentials; the checks need none beyond the workflow token.

## Later workflows

Schema and conformance checks, and the tag-driven release workflow, arrive with the schemas and vectors.
Each is its own path-filtered workflow with the same trigger, concurrency, timeout, and pinning rules.
