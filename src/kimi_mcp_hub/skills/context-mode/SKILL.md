---
name: context-mode
description: Context window optimization and token budget management.
type: prompt
whenToUse: When the user mentions context window, token budget, context limits, or context optimization.
disableModelInvocation: false
---
# 🎯 Context Mode

## Token Budget Management

### 1. Progressive Disclosure
- Level 1: File names + 1-line descriptions
- Level 2: Function signatures + docstrings
- Level 3: Full implementation (only when needed)

### 2. Smart Truncation
```python
# Show signature + first 5 lines + last 3 lines
def complex_function(a, b, c, d=None, e=None):
    """Process data with multiple options."""
    # ... (45 lines) ...
    return result
```

### 3. Exclude irrelevant files
- `node_modules/` — always exclude
- `.git/` — always exclude
- `dist/`, `build/` — exclude unless debugging build
- Test files — exclude unless testing
- Lock files — exclude unless dependency issue

### 4. Use references
Instead of full content, use:
- "See `src/utils/helpers.ts:45` for implementation"
- "Refer to `docs/architecture.md` for design"

### 5. Summarize history
Instead of full chat history:
- "Previously: Fixed auth bug in `middleware.ts`. Now implementing refresh token."

## Context Preservation
- Always keep: current task, relevant files, error messages
- Compress: old tool outputs, unrelated code, verbose logs
- Evict: oldest non-relevant context when limit reached
