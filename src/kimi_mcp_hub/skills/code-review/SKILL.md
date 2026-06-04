---
name: code-review
description: >
  Multi-agent code review using Kimi CLI sub-agents. Activate when user says
  "review", "CR", "code review", "PR review", "check this code", or when
  examining diffs, PRs, or new code. Uses explore, coder, and plan sub-agents
  for parallel analysis.
---

# 👀 Code Review — Multi-Agent

## Sub-Agent Dispatch

When reviewing code, dispatch parallel sub-agents:

### explore agent → Codebase Analysis
- Read surrounding files for context
- Check imports, dependencies, patterns
- Identify blast radius of changes
- Return: context summary, related files

### coder agent → Bug Detection
- Analyze diff line by line
- Check for logic errors, edge cases
- Verify error handling
- Return: bug list, severity, suggested fixes

### plan agent → Architectural Review
- Check if change fits architecture
- Identify coupling, cohesion issues
- Verify design patterns
- Return: architectural concerns, refactor suggestions

### Main agent → Aggregation
- Combine all sub-agent reports
- Deduplicate findings
- Prioritize by severity
- Present unified review

## Review Checklist (per sub-agent)

### explore findings
- [ ] All affected files identified
- [ ] Dependencies checked
- [ ] No breaking changes to public API
- [ ] Tests exist for modified code

### coder findings
- [ ] No logic errors
- [ ] Edge cases handled
- [ ] Error paths covered
- [ ] No off-by-one errors
- [ ] Thread safety (if concurrent)

### plan findings
- [ ] Fits existing architecture
- [ ] No unnecessary coupling
- [ ] SOLID principles followed
- [ ] Extensibility preserved

## Response format

```
👀 Code Review Report
━━━━━━━━━━━━━━━━━━━━

🔍 Context (explore agent)
  Files changed: 3
  Blast radius: src/auth/, src/api/
  Related: tests/auth.test.ts

🐛 Bugs (coder agent)
  🟠 auth.ts:45 — Missing null check on token
      Fix: Add `if (!token) return 401`
  🟡 utils.ts:12 — Potential race condition
      Fix: Use atomic operation

🏗️ Architecture (plan agent)
  🟡 New util in auth.ts should be in utils/
  🟢 No breaking API changes

✅ Overall: 2 issues, 1 suggestion
   Action: Fix null check before merge
```

## Commands
- `/review` — start full multi-agent review
- `/review quick` — fast check (main agent only)
- `/review deep` — full with all sub-agents
- `/review focus <file>` — review specific file
