---
name: gitnexus
description: Code knowledge graph and blast radius analysistype: prompt
whenToUse: When the user asks who wrote code, git blame, code impact, or repository analysis
disableModelInvocation: false
---

# 🕸️ GitNexus — Code Knowledge Graph

## Queries

### 1. Authorship
```bash
git log --format="%h %an %ae %ad %s" -- path/to/file
git blame -L 10,30 path/to/file
```

### 2. Change History
```bash
git log --all --full-history -- path/to/file
git log --grep="keyword" --oneline
```

### 3. Blast Radius
When changing a file, find all affected:
```bash
# Files that import this module
grep -r "from './module'" src/

# Tests for this component
find . -name "*.test.*" | xargs grep -l "ComponentName"

# References in docs
grep -r "moduleName" docs/
```

### 4. Dependency Graph
```bash
# JS/TS: find imports
find src -name "*.ts" | xargs grep "^import"

# Python: find imports
find . -name "*.py" | xargs grep "^import\|^from"

# Show circular dependencies
madge --circular src/
```

## Analysis Patterns

### Before Refactoring
1. `git log --stat` on target file → see change frequency
2. `git blame` → identify owner for review
3. `grep -r` → find all references
4. Check tests → ensure coverage

### Before Deleting
1. `git log --all -- path` → full history
2. Cross-reference with issues/PRs
3. Check if exported/public API
4. Verify no external consumers

## Safety
- Never delete without checking `git log`
- Never rename without updating all imports
- Always run tests after structural changes
