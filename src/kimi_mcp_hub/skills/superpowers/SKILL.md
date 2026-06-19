---
name: superpowers
description: 14 agentic development workflows for plan, debug, test, refactor, deploy.
type: prompt
whenToUse: When the user asks to plan, debug, test, refactor, deploy, audit, or architect a complex feature end-to-end.
disableModelInvocation: false
---
# 🦸 Superpowers — Agentic Skills Framework

## Available Skills

### `/plan` — Task Decomposition
Before writing code:
1. Identify all files that need changes
2. List dependencies and edge cases
3. Define verification steps
4. Estimate token budget
5. Present plan for approval

### `/architect` — System Design
For new features:
1. Choose patterns (not over-engineer)
2. Define component interactions
3. Plan extensibility points
4. Document trade-offs

### `/debug` — Root Cause Analysis
For bugs:
1. Isolate reproduction steps
2. Check recent changes (git log)
3. Reproduce in isolation
4. Form hypothesis
5. Validate fix
6. Add regression test

### `/test` — Test-Driven Validation
1. Write failing test first
2. Implement minimal code to pass
3. Refactor
4. Verify coverage

### `/refactor` — Code Improvement
1. Identify code smells
2. Ensure tests pass before
3. Make incremental changes
4. Verify tests pass after
5. Document changes

### `/deploy` — Safe Deployment
1. Pre-flight checks (lint, test, build)
2. Environment validation
3. Staging verification
4. Production rollout with rollback plan
5. Post-deploy monitoring

### `/audit` — Security Review
1. Check for exposed credentials
2. Injection risks (SQL, XSS, command)
3. Dependency vulnerabilities
4. Misconfigured permissions
5. Input validation gaps

### `/migrate` — Safe Migration
1. Backward compatibility check
2. Data migration plan
3. Rollback strategy
4. Verification steps

### `/optimize` — Performance
1. Profile before optimizing
2. Target bottlenecks (DB queries, algorithms, renders)
3. Measure after
4. Document trade-offs

### `/document` — Meaningful Docs
1. Explain WHY not just WHAT
2. Include context and decisions
3. Add examples
4. Keep in sync with code

## Workflow

Brainstorm → Git Worktree → Plan → Execute → Test → Review → Deploy

### Phase 1: Brainstorm
- Ask clarifying questions
- Explore alternatives
- Present design in chunks for validation

### Phase 2: Git Worktree
```bash
git worktree add -b feature/name ../feature-name
cd ../feature-name
# Verify clean test baseline
```

### Phase 3: Write Plan
- Break into 2-5 minute tasks
- Include exact file paths
- Define expected code + verification steps

### Phase 4: Execute
- Subagent-driven: fresh agent per task, two-stage review
- Or batch execution with human checkpoints

### Phase 5: Test-Driven
- Write tests before implementation
- Red → Green → Refactor

### Phase 6: Review
- Self-review against plan
- Check for deviations
- Verify all acceptance criteria

### Phase 7: Deploy
- Run pre-flight checks
- Deploy to staging
- Verify
- Production rollout
