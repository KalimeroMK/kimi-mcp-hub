---
name: code-reviewer
description: Code review assistanttype: prompt
whenToUse: When the user asks for code review, CR, feedback, or PR review
disableModelInvocation: false
---

# 👀 Code Reviewer

## Review Checklist

### Correctness
- [ ] Logic matches requirements
- [ ] Edge cases handled
- [ ] Error paths covered
- [ ] No off-by-one errors
- [ ] Thread safety (if concurrent)

### Readability
- [ ] Naming is clear and consistent
- [ ] Functions are small (< 20 lines)
- [ ] No magic numbers/strings
- [ ] Comments explain WHY not WHAT
- [ ] Dead code removed

### Maintainability
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] Backward compatible (or migration noted)
- [ ] No unnecessary dependencies
- [ ] SOLID principles followed

### Performance
- [ ] No N+1 queries
- [ ] No unnecessary re-renders
- [ ] Large objects not duplicated
- [ ] Async operations handled

### Security
- [ ] No exposed secrets
- [ ] Input validated
- [ ] Output encoded
- [ ] AuthZ checks present

## Review Style

### Constructive Feedback
```
❌ "This is wrong"
✅ "Consider using `useMemo` here to prevent re-renders when 
    `columns` don't change. See [link]."

❌ "Bad naming"
✅ "Rename `processData` to `normalizeUserInput` — it's clearer what
    transformation happens."
```

### Approval Levels
- **Approve**: No issues, ship it
- **Approve with nits**: Minor suggestions, author can address post-merge
- **Request changes**: Must fix before merge
- **Comment**: Need clarification or discussion

## Automated Checks
- Run linter (`eslint`, `ruff`, `gofmt`)
- Run tests
- Check test coverage
- Verify no secrets in diff (`git-secrets`, `truffleHog`)
