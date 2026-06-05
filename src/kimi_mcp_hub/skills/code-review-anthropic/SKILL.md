---
name: code-review-anthropic
description: Multi-agent code review system inspired by Anthropic's official plugin. Uses Kimi CLI sub-agents (coder, explore, plan) for parallel review. Activate when user says "review", "CR", "PR review", "code 
type: prompt
whenToUse: When the user asks for deep PR review, multi-agent review, or thorough code inspection
disableModelInvocation: false
---

# 👥 Code Review Anthropic — Multi-Agent Review

## Architecture

Uses Kimi CLI built-in sub-agents for parallel analysis:

| Agent | Role | What it checks |
|-------|------|----------------|
| **explore** | Codebase analyzer | Context, dependencies, blast radius |
| **coder** | Bug detector | Logic errors, edge cases, anti-patterns |
| **plan** | Architect reviewer | Design patterns, extensibility, tech debt |
| **main** | Aggregator | Confidence scoring, final verdict |

## Review Pipeline

### Phase 1: Parallel Analysis (auto-dispatch)
```
main: "Review this PR"
  → explore: "Analyze changed files and their dependencies"
  → coder: "Find bugs, edge cases, and logic errors"
  → plan: "Check architecture and design decisions"
```

### Phase 2: Confidence Scoring
Each agent returns score 0-100:
- **90-100**: LGTM, no issues
- **70-89**: Minor issues, address if time
- **50-69**: Moderate issues, must fix
- **0-49**: Critical issues, block merge

**Threshold for approval: 80+ from ALL agents**

### Phase 3: Aggregated Report
```markdown
## Code Review Report

### explore (confidence: 85)
- ✅ No breaking changes to public API
- ⚠️ New dependency `lodash-es` adds 15KB, consider native alternative
- ✅ Tests cover new paths

### coder (confidence: 72)
- ❌ Edge case: `userId` can be null, throws unhandled exception
- ⚠️ Race condition in `fetchUser` if called twice rapidly
- ✅ Error handling present for network failures

### plan (confidence: 91)
- ✅ Clean separation of concerns
- ✅ Follows existing module pattern
- ✅ Extensible for future user types

### Verdict: REQUEST CHANGES (coder < 80)
**Required fixes:**
1. Add null check for `userId` (line 45)
2. Debounce or cache `fetchUser` to prevent race condition
```

## Review Checklist (per agent)

### explore Agent
- [ ] Changed files and their dependencies identified
- [ ] Blast radius calculated (who else uses this code?)
- [ ] No breaking changes to public API (or documented)
- [ ] Tests exist for modified paths
- [ ] Documentation updated if needed

### coder Agent
- [ ] Logic errors and edge cases
- [ ] Null/undefined handling
- [ ] Race conditions and async issues
- [ ] Error handling completeness
- [ ] Performance implications (N+1, loops, allocations)
- [ ] Type safety (if typed language)

### plan Agent
- [ ] Architecture consistency
- [ ] Design pattern appropriateness
- [ ] Extensibility for future requirements
- [ ] Tech debt introduced or resolved
- [ ] SOLID principles followed
- [ ] YAGNI — no over-engineering

## Commands
- `/review` — start full multi-agent review
- `/review quick` — single-agent fast review (explore only)
- `/review deep` — all agents + security-guidance scan
- `/review focus [agent]` — only specific agent (explore/coder/plan)
- `/review confidence` — show confidence scores
- `/review approve` — mark as approved (if all > 80)
- `/review block` — mark as blocked with required fixes

## Integration with security-guidance
When `/review deep` is used, automatically run security-guidance Layer 2 scan on the diff.
