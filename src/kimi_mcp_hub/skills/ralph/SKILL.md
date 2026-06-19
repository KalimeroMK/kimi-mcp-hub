---
name: ralph
description: Autonomous loop with stop-hooks for long-running tasks.
type: prompt
whenToUse: When the user asks to keep going, continue working, or run in autonomous mode with checkpoints.
disableModelInvocation: false
---
# 🔄 Ralph — Autonomous Loop

## Pattern

```
while (has_tasks):
    1. Plan next action
    2. Execute with tools
    3. Verify result
    4. If success → next task
    5. If failure → retry with fix (max 3x)
    6. If blocked → STOP and ask human
```

## Stop Conditions (MUST stop and ask)
- Error after 3 retries
- Test failure without clear fix
- Security-related change (auth, permissions)
- Database schema change
- API contract change
- Deleting > 5 files
- Cost > $0.50 in API calls
- User explicitly says "stop"

## Progress Reporting
Every 5 minutes or 10 tasks:
```
[Progress] 7/23 tasks complete
[Current] Refactoring auth middleware
[Next] Update tests for new auth flow
[Blockers] None
```

## Safety
- Always show diff before applying
- Never commit without review
- Keep backup branch: `ralph-backup-[timestamp]`
- Log all actions to `RALPH_LOG.md`
