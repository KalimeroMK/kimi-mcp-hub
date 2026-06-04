---
name: memory-palace
description: >
  Advanced memory and context management. Activate when user says
  "remember", "don't forget", "context", "memory", "what did we do",
  "previous session", or when resuming work after break.
---

# 🏛️ Memory Palace

## Context Injection

When starting a session, inject:
```
[Context] Last worked on: auth refactor in src/auth/
[Files] middleware.ts, tokens.ts, oauth.ts
[Status] Tests passing, 2 TODOs remaining
[Decisions] Chose JWT over sessions (see ADR-003)
[Blockers] Waiting for OAuth provider credentials
```

## Memory Types

### 1. Session Memory
- What was done this session
- Files modified
- Tools used
- Errors encountered

### 2. Project Memory
- Architecture decisions
- Tech stack
- Conventions (naming, structure)
- Known issues

### 3. User Memory
- Preferences (terse/verbose)
- Common workflows
- Frequently accessed files
- Skill activation patterns

## Retrieval
- **Search**: `memory_search "auth bug"`
- **Timeline**: `memory_timeline --last 5`
- **Get**: `memory_get [observation_id]`

## Maintenance
- Auto-archive observations older than 90 days
- Compress summaries after 30 days
- Flag stale context ("last updated 45 days ago")
- Cleanup on `memory_cleanup --days 30`
