---
name: karpathy
description: Andrej Karpathy-style coding discipline. Activate for any code generation, review, or refactoring. Use when writing functions, classes, algorithms, or when user says "write code", "implement", "functi
type: prompt
whenToUse: When the user asks to write, review, or refactor code, or mentions functions, classes, or implementation
disableModelInvocation: false
---

# 🧠 Karpathy Skills — Code Discipline

## Principles

1. **Start simple, then complexify**
   - Solve the 80% case first
   - Add edge cases only when needed
   - Avoid premature abstraction

2. **One function, one job**
   - Max 20 lines per function
   - Max 3 parameters (use config object if more)
   - Pure functions when possible

3. **Names are documentation**
   - `process_data()` → `normalize_image_tensor()`
   - Boolean: `is_valid`, `has_feature`
   - Avoid abbreviations: `num` → `count`, `tmp` → `temp_buffer`

4. **Fail fast, fail loud**
   - Assert preconditions
   - Raise specific exceptions
   - Never silently swallow errors

5. **No magic numbers**
   - `TIMEOUT_SECONDS = 30`
   - `MAX_RETRIES = 3`
   - `BATCH_SIZE = 64`

6. **Comments explain WHY, not WHAT**
   - Bad: `// Increment counter`
   - Good: `// Retry with exponential backoff for rate limits`

7. **Test the boundaries**
   - Empty input
   - Single element
   - Maximum size
   - Invalid types

## Code Review Checklist
- [ ] Can I understand this in 30 seconds?
- [ ] Are there side effects?
- [ ] Is error handling complete?
- [ ] Would this confuse me in 6 months?
- [ ] Is there a simpler way?
