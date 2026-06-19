---
name: perf-optimization
description: Performance profiling and optimizationtype: prompt
whenToUse: When the user mentions slow performance, profiling, benchmark, or optimization
disableModelInvocation: false
---

# ⚡ Performance Optimization

## Golden Rule
**Never optimize without profiling.**

## Profiling Tools

### Frontend
- Chrome DevTools: Performance tab, Lighthouse
- React DevTools: Profiler, why-did-you-render
- Web Vitals: LCP, FID, CLS, TTFB, INP

### Backend
- Node.js: `clinic.js`, `0x`, `node --prof`
- Python: `cProfile`, `py-spy`, `scalene`
- Go: `pprof`
- Database: `EXPLAIN ANALYZE`, slow query log

### Database
```sql
EXPLAIN ANALYZE SELECT * FROM users WHERE email = 'test@example.com';
-- Check: Seq Scan vs Index Scan
-- Check: Execution time, rows, buffers
```

## Optimization Strategies

### Algorithmic
- O(n²) → O(n log n) or O(n)
- Use hash maps for lookups
- Avoid nested loops

### Caching
- Memoization: `useMemo`, `lru_cache`
- HTTP caching: ETag, Cache-Control
- CDN: static assets, images
- Database: query cache, connection pooling

### Lazy Loading
- Code splitting: `React.lazy()`, dynamic imports
- Image lazy loading: `loading="lazy"`
- Virtual scrolling: `react-window`, `react-virtualized`

### Database
- Add indexes (but not too many)
- Denormalize read-heavy data
- Batch inserts/updates
- Connection pooling

### Network
- Bundle size: tree shaking, minification
- Compression: Brotli, Gzip
- HTTP/2 or HTTP/3
- Reduce requests: bundling, inlining critical CSS

## Measurement
- Before: baseline metric
- After: new metric
- Compare: percentage improvement
- Document: what worked, what didn't
