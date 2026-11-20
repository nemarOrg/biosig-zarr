# Code Review Standards

## PR Review Toolkit
When the `pr-review-toolkit` plugin is available, use it after creating PRs to catch issues before merge.

### Available Agents
- `code-reviewer` - Review for style, best practices, project guidelines
- `silent-failure-hunter` - Find inadequate error handling, silent failures
- `code-simplifier` - Simplify code while preserving functionality
- `comment-analyzer` - Check comment accuracy and maintainability
- `pr-test-analyzer` - Review test coverage quality
- `type-design-analyzer` - Analyze type design and invariants

### Workflow (at most two rounds, then merge)
**No technical debt carried forward, and no review loops.** Full procedure: the `project:pr-review-toolkit` skill's `references/review-convergence.md`.
1. Create PR with `gh pr create`; start review while CI runs
2. Round 1: one review panel on the whole diff
3. Give every finding one outcome: fix (including suggestions), reject with a one-line reason, or follow-up issue for code the PR did not touch. Fix before merge; never in a follow-up PR or the next release
4. Commit fixes on the PR branch and push once. A large fix (>150 non-test lines, public contract change, or new approach), or any fix when the PR branch blocks direct pushes, goes in one fix PR whose base is the PR branch
5. Round 2 only if round 1 was substantial (accepted Critical, large fix, or auth/crypto/data-integrity/concurrency change): one reviewer, fix diff only
6. Fix round-2 findings directly; no third round. Merge when CI is green, never before the review returns

## Review Checklist for a Specification Change

### Before committing
- [ ] `uvx typos .` and `bun run lint` pass; links resolve
- [ ] Every commit is signed off and atomic
- [ ] No secrets, personal data, or unrelated files

### The text
- [ ] Each requirement uses an RFC 2119 key word, is stated once, and can be tested by a vector
- [ ] Two independent readers of the sentence would implement the same behavior
- [ ] Normative and non-normative text are separate; examples are valid
- [ ] Abbreviations are defined before use; American English; semantic line breaks; no em-dashes

### Classification
- [ ] An editorial change leaves what conforms unchanged; anything else has an accepted RFC and links it
- [ ] The change does not edit an accepted RFC or a published tag's content
- [ ] The change records a decision in an ADR when it settles one

### Never do this
- [ ] No reader or writer library in this repository
- [ ] No vector from a recording that is not under a public-domain dedication
- [ ] No commented-out text (delete it; git has history)
- [ ] No `TODO` without a linked issue
- [ ] No backward-compatibility prose that keeps a withdrawn rule alive; supersede it

## Review Comments
When leaving review comments:
- Be specific about the issue
- Suggest a fix when possible
- Distinguish blocking vs. non-blocking issues
- Reference documentation or examples

---
*No technical debt carried forward. Two review rounds at most, then merge.*
