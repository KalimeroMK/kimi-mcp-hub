---
name: headroom
description: Compress large tool outputs to save tokenstype: prompt
whenToUse: When the user mentions large outputs, token limits, context compression, or saving tokens
disableModelInvocation: false
---

# 📉 Headroom — Output Compression

## When to compress
- Tool output > 1000 tokens
- Large file listings (> 50 files)
- Full directory trees
- Long logs or stack traces
- Bulk search results

## Compression strategies

### 1. Summarize listings
```
# Instead of listing 200 files:
src/
  components/ (42 files)
  utils/ (15 files)
  hooks/ (8 files)
  tests/ (67 files)
```

### 2. Truncate with ellipsis
```
# Show first 5 and last 3
file1.ts
file2.ts
file3.ts
file4.ts
file5.ts
... (47 more files) ...
file95.ts
file96.ts
file97.ts
```

### 3. Group by pattern
```
# Instead of individual files
*.test.tsx: 23 files
*.stories.tsx: 12 files
*.types.ts: 8 files
```

### 4. Extract key lines from logs
```
# Error log: show ERROR/FATAL only, with 2 lines context
[12:34:56] ERROR: Connection refused at db.ts:45
[12:34:57] ERROR: Retry failed, max attempts reached
[12:34:58] FATAL: Service shutdown initiated
```

## Rules
- Never compress code that needs editing
- Never compress error messages (summarize instead)
- Always preserve line numbers for errors
- State compression ratio: "Compressed 5000 → 200 tokens (96%)"
