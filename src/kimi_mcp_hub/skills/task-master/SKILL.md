---
name: task-master
description: >
  Task management system for complex projects. Activate when user says
  "task", "todo", "plan", "milestone", "backlog", "sprint", "organize",
  or when breaking down large features into actionable items.
---

# 📋 Task Master

## Task Format

```markdown
## Task: [ID] Short Title
**Status:** 🔵 Todo | 🟡 In Progress | 🟢 Done | 🔴 Blocked
**Priority:** P0 | P1 | P2 | P3
**Assignee:** @name
**Due:** YYYY-MM-DD
**Estimate:** X hours

### Description
What needs to be done.

### Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

### Dependencies
- Blocks: #task-id
- Blocked by: #task-id

### Notes
- Context, decisions, links
```

## Workflow

1. **Backlog Grooming**
   - All tasks start in 🔵 Todo
   - Estimate before starting
   - Check dependencies

2. **Sprint Planning**
   - Move P0/P1 to 🟡 In Progress
   - Ensure no blockers
   - Set due dates

3. **Daily Standup**
   - What did I finish? (🟢)
   - What am I working on? (🟡)
   - What's blocking me? (🔴)

4. **Review**
   - All acceptance criteria met?
   - Tests passing?
   - Documentation updated?

## Commands
- `/task add "Title"` — create task
- `/task list` — show all tasks
- `/task status [ID]` — show task details
- `/task done [ID]` — mark complete
- `/task block [ID] "reason"` — mark blocked
