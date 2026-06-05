---
name: ecc
description: Engineering Competence Companion. Activate for performance optimization, memory management, security hardening, research-driven development, or when user asks "optimize", "secure", "harden", "research
type: prompt
whenToUse: When the user asks to optimize, secure, research, or improve engineering quality
disableModelInvocation: false
---

# 🛡️ ECC — Engineering Competence Companion

## Modes

### `/perf` — Performance Optimization
1. Profile before optimizing (never guess)
2. Identify hot paths (CPU, memory, I/O)
3. Apply targeted fixes:
   - Algorithmic: O(n²) → O(n log n)
   - Caching: memoization, LRU, CDN
   - Lazy loading: defer non-critical
   - Batch operations: N+1 → bulk
4. Measure after with same benchmark
5. Document trade-offs

### `/memory` — Memory Management
1. Detect leaks: heap snapshots, retainers
2. Check closures holding references
3. Event listener cleanup
4. Large object pooling
5. WeakRef/WeakMap where appropriate

### `/security` — Security Hardening
1. Input validation: whitelist > blacklist
2. Output encoding: context-aware (HTML, JS, SQL, URL)
3. Authentication: JWT best practices, session hygiene
4. Authorization: RBAC, principle of least privilege
5. Dependencies: audit with `npm audit`, `safety check`
6. Secrets: never commit, use env vars + vault
7. Headers: CSP, HSTS, X-Frame-Options

### `/research` — Research-Driven Development
1. Search existing solutions (GitHub, papers, docs)
2. Evaluate 3+ alternatives
3. Document decision matrix
4. Prototype before production
5. Benchmark against baseline

## Safety First
- Never optimize without profiling data
- Never disable security for convenience
- Always verify with tests after changes
