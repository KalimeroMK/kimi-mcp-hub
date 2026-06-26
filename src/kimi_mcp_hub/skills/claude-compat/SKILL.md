---
name: claude-compat
description: Patch ~/.kimi-code/AGENTS.md so Kimi auto-reads CLAUDE.md and CLAUDE.local.md from the project root at session start.
type: prompt
whenToUse: When the user wants Kimi to automatically load CLAUDE.md or CLAUDE.local.md project instructions, or when setting up a project that already has Claude Code configuration files.
disableModelInvocation: false
tools: Read, Write, Edit, Bash
---

# Claude Compat — Auto-load CLAUDE.md in Kimi

Patch `~/.kimi-code/AGENTS.md` to instruct Kimi to discover and read
`CLAUDE.md` and `CLAUDE.local.md` from the project root at the start of
every session, the same way Claude Code does natively.

## Steps

### 1. Read current AGENTS.md (if it exists)

```bash
cat ~/.kimi-code/AGENTS.md 2>/dev/null || echo "__EMPTY__"
```

### 2. Check if the patch is already applied

Search the output for the marker `<!-- claude-compat -->`.
- If found → report "Already patched, nothing to do." and stop.
- If not found → continue to step 3.

### 3. Append the patch

If `~/.kimi-code/AGENTS.md` is empty or missing, create it with the patch
as the only content. Otherwise append it at the end of the existing file.

The block to append:

```markdown
<!-- claude-compat -->
## Claude Code Compatibility — Auto-load CLAUDE.md

At the start of every session, before doing anything else, check for the
following files in the current working directory (project root):

| Priority | File | Purpose |
|----------|------|---------|
| 1 | `CLAUDE.local.md` | Local overrides — machine-specific, gitignored |
| 2 | `CLAUDE.md` | Project-wide instructions — committed to the repo |

**Discovery logic (in order):**
1. `<cwd>/CLAUDE.local.md` — read if exists
2. `<cwd>/CLAUDE.md` — read if exists
3. If neither exists, skip silently

**How to apply the content:**
- Treat both files as authoritative project instructions — equivalent to
  `AGENTS.md` in the Kimi convention.
- CLAUDE.local.md takes precedence over CLAUDE.md when they conflict.
- Never modify these files unless the user explicitly asks you to.
- If a file is found, print one line: `📋 Loaded <filename> (N lines)`
  so the user knows it was picked up.

**Example bootstrap check you can run:**
```bash
[ -f CLAUDE.local.md ] && echo "found CLAUDE.local.md" || true
[ -f CLAUDE.md ]       && echo "found CLAUDE.md"       || true
```
<!-- /claude-compat -->
```

### 4. Write the file

Use the Write or Edit tool to save the updated content to
`~/.kimi-code/AGENTS.md`.

Make sure the file ends with a single newline.

### 5. Confirm

Print a summary:

```
✅ claude-compat patch applied to ~/.kimi-code/AGENTS.md

Kimi will now auto-read at session start:
  • CLAUDE.local.md  (local overrides, gitignored)
  • CLAUDE.md        (project instructions)

Restart Kimi CLI for the change to take effect.
```

## Uninstall

To remove the patch, delete the lines between
`<!-- claude-compat -->` and `<!-- /claude-compat -->` from
`~/.kimi-code/AGENTS.md`.
