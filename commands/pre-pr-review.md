---
description: Review the current branch before opening a PR -- diff, bugs, lint, verdict
---

Review the code on the current branch the way a reviewer would, *before* the PR is opened.
This command is read-only: **never** edit files, stage, commit, push, or open a PR while running it.

## 1. Read the arguments

`$ARGUMENTS` may be empty or contain one of:

- `quick` -- skip the sub-agents, review the diff yourself in one pass
- `deep` -- dispatch every sub-agent in step 3 (the default is all three)
- `focus <path>` -- restrict the review to that file or directory
- anything else -- treat it as the base ref (e.g. `develop`, `origin/release/2.0`)

## 2. Collect the diff context

Run `kimi-mcp-hub review-context` (add `--base <ref>` if the arguments named one). That prints the
base branch, the changed files with line counts, uncommitted files, warnings, and the diff.

**Read its Warnings section before reviewing.** A wrong base branch, a shallow clone, or a truncated
diff body all mean your review is looking at the wrong thing — say so instead of reviewing anyway.

If the command is not found, this is a plugin-only install without the Python package. Fall back to:

```bash
BASE=$(git symbolic-ref -q --short refs/remotes/origin/HEAD || echo origin/main)
MB=$(git merge-base "$BASE" HEAD)
git diff --name-status -M "$MB..HEAD"
git diff --no-color -M "$MB..HEAD"
git status --porcelain -uall
```

## 3. Dispatch review sub-agents in parallel

Follow the `code-review` skill's methodology. Give each sub-agent the changed-file list and the diff:

- **explore** -- blast radius: who calls the changed code, which callers were *not* updated, whether
  tests exist for the changed paths, whether a public API or config contract changed
- **coder** -- defects: logic errors, unhandled edge cases, missing error paths, off-by-one, null and
  empty-collection handling, concurrency, resource leaks, N+1 queries, injection and secret leaks
- **plan** -- fit: does the change belong where it was put, does it duplicate something that already
  exists in the repo, does it break an existing pattern, is the abstraction earning its keep

For `quick`, do this yourself in one pass and skip the sub-agents.

## 4. Run the fast linter only

Detect the project's linter from its config and run it **on the changed files only**:

| Signal | Command |
|--------|---------|
| `[tool.ruff]` in `pyproject.toml` | `ruff check <files>` |
| eslint config or devDependency | `npx eslint <files>` |
| `laravel/pint` in `composer.json` | `vendor/bin/pint --test <files>` |
| `.golangci.yml` | `golangci-lint run` |
| none of the above | skip, and say so |

**Do not run the test suite.** Find the test command instead (`pytest`, `npm test`, `composer test`,
`go test ./...`) and report it as the next step, so the review stays fast.

## 5. Aggregate

Merge the sub-agent reports. Drop duplicates. Drop anything that is not about the changed lines —
pre-existing problems in untouched code are not this PR's business. Rank by severity:

- 🔴 **blocking** -- will break behavior, lose data, or leak a secret
- 🟡 **should fix** -- works but fragile, missing test, unclear contract
- 🔵 **nit** -- naming, style, micro-optimization; the author may ignore it
- ❓ **question** -- you genuinely cannot tell from the diff whether it is correct

Every finding needs `file:line`, what is wrong, and the concrete fix. No hedging, no restating what
the line does.

## 6. Report

```
👀 Pre-PR Review — <branch> vs <base>
Scope: <n> files, <n> lines

🔴 Blocking (n)
  path/file.py:45 — <problem>. Fix: <fix>.

🟡 Should fix (n)
🔵 Nits (n)
❓ Questions (n)

Lint:  <linter> — clean | <n> problems
Tests: not run — `<test command>`

Verdict: 🟢 ready to open | 🟡 open with follow-ups | 🔴 fix before opening
```

Verdict rules: any 🔴 or a failing linter means 🔴. Only 🟡/🔵 means 🟡. Nothing but nits and a clean
linter means 🟢.

If the diff is empty, say so and stop — do not invent findings. End by offering the next step
(`gh pr create`, or the test command), but do not run it.
