---
name: hindsight
description: Memory that learns from mistakes and past decisions.
type: prompt
whenToUse: When the user asks to learn from mistakes, review past errors, or improve based on history.
disableModelInvocation: false
---
# 🔮 Hindsight — Learning Memory

## Capture Patterns

### 1. Error Patterns
When a bug recurs:
```
[LEARNED] Auth middleware fails when token is expired + refresh is missing.
Fix: Check refresh token before validating access token.
File: src/auth/middleware.ts
```

### 2. Decision Log
When making architectural choices:
```
[DECISION] Chose PostgreSQL over MongoDB for user data.
Reason: ACID requirements, complex relationships.
Date: 2024-01-15
Reversible: Yes (migration script exists)
```

### 3. Workarounds
When applying temporary fixes:
```
[WORKAROUND] Disabled ESLint rule @typescript-eslint/no-explicit-any
in tests/ folder. Re-enable after migrating test types.
Ticket: #234
```

### 4. Performance Notes
When discovering optimizations:
```
[PERF] useMemo prevents re-render in DataTable when columns don't change.
Measured: 45% faster on 1000+ rows.
```

## Query Patterns
- "What did we learn about auth?" → Search [LEARNED] tags
- "Why did we choose X?" → Search [DECISION] tags
- "What workarounds exist?" → Search [WORKAROUND] tags
- "What optimizations worked?" → Search [PERF] tags

## Auto-capture triggers
- Same error 3+ times
- Failed attempt followed by success
- "Let's remember this for next time"
- Explicit: "Remember that..."
