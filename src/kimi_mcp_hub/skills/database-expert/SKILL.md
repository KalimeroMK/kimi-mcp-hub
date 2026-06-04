---
name: database-expert
description: >
  Database design and optimization. Activate when user says "database",
  "DB", "SQL", "schema", "migration", "index", "query", "PostgreSQL",
  "MySQL", "MongoDB", "Redis", "ORM", or when working with data storage.
---

# 🗄️ Database Expert

## Schema Design

### Normalization
- 1NF: Atomic values, no repeating groups
- 2NF: No partial dependencies
- 3NF: No transitive dependencies
- Denormalize only for read performance (document)

### Types
```sql
-- Use appropriate types
VARCHAR(255)  -- strings with max length
TEXT          -- unlimited/long text
INTEGER       -- whole numbers
BIGINT        -- large numbers (IDs, timestamps)
DECIMAL(10,2) -- money (never FLOAT)
BOOLEAN       -- true/false
TIMESTAMP     -- dates with timezone
UUID          -- distributed IDs
JSONB         -- PostgreSQL flexible schema
```

### Indexes
```sql
-- B-tree (default) — equality and range
CREATE INDEX idx_users_email ON users(email);

-- Partial — filter common queries
CREATE INDEX idx_active_users ON users(created_at) WHERE active = true;

-- Composite — multi-column
CREATE INDEX idx_orders_user_date ON orders(user_id, created_at);

-- GIN — JSONB, arrays, full-text
CREATE INDEX idx_docs_search ON documents USING GIN(search_vector);
```

## Query Optimization

### EXPLAIN ANALYZE
```sql
EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
SELECT * FROM users WHERE email = 'test@example.com';
```

Look for:
- Seq Scan → needs index
- High buffers → too much data read
- High execution time → optimize or cache

### Anti-patterns
```sql
-- N+1 query (BAD)
SELECT * FROM orders;
-- For each order:
SELECT * FROM users WHERE id = ?;

-- JOIN (GOOD)
SELECT o.*, u.name
FROM orders o
JOIN users u ON o.user_id = u.id;

-- SELECT * (BAD)
SELECT * FROM large_table;

-- Explicit columns (GOOD)
SELECT id, name, email FROM large_table;
```

## Migrations
- Always reversible (up + down)
- Test on copy of production data
- Run in transaction when possible
- Never delete column without deprecation period
- Add index concurrently (PostgreSQL): `CREATE INDEX CONCURRENTLY`

## Connection Pooling
- Max connections: CPU cores × 2
- Use PgBouncer or similar
- Close connections properly
- Handle connection errors gracefully
