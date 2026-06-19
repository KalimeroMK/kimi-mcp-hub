---
name: research-mode
description: Research-driven development for technology evaluation.
type: prompt
whenToUse: When the user asks to research, compare, benchmark, or evaluate technologies or approaches.
disableModelInvocation: false
---
# 🔬 Research Mode

## Process

### 1. Define Question
```
"What is the best state management library for React in 2024?"
→ Must be: specific, measurable, time-bound
```

### 2. Gather Sources
- GitHub stars, issues, PR velocity
- npm trends / PyPI downloads
- Documentation quality
- Community size (Discord, Reddit, StackOverflow)
- Corporate backing (if relevant)

### 3. Evaluate Criteria
| Criteria | Weight | Option A | Option B | Option C |
|----------|--------|----------|----------|----------|
| Performance | 30% | 9/10 | 7/10 | 8/10 |
| Learning curve | 20% | 6/10 | 9/10 | 7/10 |
| Ecosystem | 20% | 10/10 | 5/10 | 7/10 |
| Maintenance | 20% | 9/10 | 8/10 | 6/10 |
| Bundle size | 10% | 7/10 | 9/10 | 8/10 |
| **Weighted** | | **8.5** | **7.4** | **7.2** |

### 4. Prototype
- Build minimal proof-of-concept
- Measure actual metrics (not just docs)
- Test edge cases

### 5. Decision Record
```markdown
## ADR-001: Chose Zustand over Redux Toolkit
- Date: 2024-01-15
- Decision: Use Zustand for global state
- Rationale: 90% smaller bundle, simpler API, sufficient for our use case
- Consequences: Less middleware ecosystem, need custom devtools integration
- Reversible: Yes (migration ~2 days)
```

## Rules
- Never choose based on popularity alone
- Always prototype before production
- Document decision with rationale
- Set review date (re-evaluate in 6 months)
