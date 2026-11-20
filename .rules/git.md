# Git & Version Control Standards

## Commit Messages
- **Format:** `<type>: <description>`
- **Length:** <50 characters
- **No emojis** in commits or PR titles
- **No AI attribution** (no "Co-Authored-By: Claude" or similar)
- **Sign-off:** every commit carries a `Signed-off-by:` line (`git commit -s`), per the Developer Certificate of Origin in `CONTRIBUTING.md`
- **Types:**
  - `feat:` New normative text or a new file of the specification
  - `fix:` Correct an error
  - `docs:` Editorial change
  - `refactor:` Restructure without changing meaning
  - `test:` Add a check or a vector (real data only)
  - `chore:` Maintenance tasks
- **`[skip ci]`:** append to the subject when the commit touches only files no CI job reads (notes, `.context/`, `.memory/`, docs CI does not build): `docs: clarify setup [skip ci]`
  - GitHub reads only the head commit of a push; never push it on top of untested code commits
  - The token matches anywhere in the message, body included; never quote it in a commit you want tested
  - On a PR with required checks (`gh pr checks N --required`), do not use it; a skipped required check blocks merge
  - Exception: post-merge bot bump and sync commits on the integration branch always carry it (see `.rules/ci_cd.md`)

## Branch Strategy
- **One integration branch:** `main`. Releases are tags made by the owner; never tag.
- **Work branches:** `feature/short-description` or `fix/short-description`, branched from `main`
- **Draft branches:** the text an RFC proposes lives on `draft/<major>.<minor>.<patch>` until the RFC is accepted (see `GOVERNANCE.md`); `main` carries only accepted text
- **No spaces** in branch names, use hyphens
- **Delete after merge**

## Commit Practice
- **Atomic commits** - One logical change per commit
- **Test before commit** - Ensure code works
- **No broken commits** - Each commit should work independently

## Pull Request Process
1. Create an issue first for a significant change; a normative change starts as an RFC in nemarOrg/rfcs, not here
2. Branch from `main`
3. Make atomic commits
4. Push branch
5. Create PR with `gh pr create`:
   - Clear title (<70 chars, no emojis)
   - Description that references the issue or the RFC, one paragraph per line
   - Results of the checks
6. Review per `.rules/code_review.md`: at most one full review and one delta review
7. Fix review findings with commits on the same branch (one push per round). If that branch blocks direct pushes (release PRs), use one fix PR per round into it
8. Squash merge to keep history clean

## Merge Strategy
- **Squash merge** for feature branches (clean history)
- **Merge `main` into** a pushed feature branch to update it; never rebase or force-push a pushed branch
- **Never force-push** to `main`
- **Delete branch** after merge

## Git Commands
```bash
# Start a branch
git switch -c feature/short-description origin/main

# Atomic, signed-off commits
git add -p  # Stage selectively
git commit -s -m "docs: clarify the chunk shape"

# Push and create PR
git push -u origin feature/short-description
gh pr create
```

## .gitignore Essentials
```
node_modules/    # JavaScript tooling
.env             # Secrets
.DS_Store
```

---
*Atomic commits, signed off, clear messages, clean history. No emojis, no AI attribution.*
