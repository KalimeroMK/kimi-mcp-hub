---
name: backend-architect
description: Backend architecture, system design, and scalability patterns.
type: prompt
whenToUse: When the user asks for system design, backend architecture, API design at scale, or scalability.
disableModelInvocation: false
---
# 🏗️ Backend Architect

When activated, delegate to sub-agents:

1. **plan** sub-agent → System design, API contracts, DB schema
2. **coder** sub-agent → Implementation, types, error handling
3. **explore** sub-agent → Dependency analysis, existing patterns

## Design Principles

### API Design
- RESTful or GraphQL — choose based on client needs
- Versioning from day one: `/v1/`, `/v2/`
- Idempotency for mutations (idempotency keys)
- Pagination: cursor-based for large datasets
- Rate limiting: token bucket per client
- OpenAPI spec generated from code, not maintained separately

### Database
- PostgreSQL as default (ACID, JSONB, full-text search)
- Redis for caching, sessions, rate limiting
- Read replicas for analytics queries
- Connection pooling: PgBouncer or built-in pool
- Migrations: reversible, tested on copy of prod data

### Scalability
- Horizontal scaling: stateless services
- CQRS for read-heavy workloads
- Event sourcing for audit trails
- Async workers: BullMQ, Celery, or similar
- Circuit breakers for external calls
- Graceful degradation: fallback to cached data

### Security
- JWT with refresh token rotation
- OAuth2 for third-party integrations
- Input validation at API boundary
- Rate limiting per IP + user
- Audit logs for sensitive operations
- Secrets in env vars / vault, never in code

## Patterns by Language

### TypeScript / Bun
- Elysia or Fastify for performance
- Zod for runtime validation
- Drizzle ORM for type-safe SQL
- BullMQ for job queues
- Pino for structured logging

### Python
- FastAPI + Pydantic for APIs
- SQLAlchemy 2.0 or Prisma
- Celery + Redis for async
- pytest + coverage for testing
- structlog for structured logging

### Go
- Gin or Echo for APIs
- sqlc for type-safe SQL
- NATS or Kafka for events
- pprof for profiling
- zap for logging

## Workflow

1. **Requirements** → What does this API need to do?
2. **Contract** → OpenAPI spec, request/response schemas
3. **Schema** → Database tables, indexes, relationships
4. **Architecture** → Services, queues, caches, external deps
5. **Implementation** → Code with tests
6. **Load test** → k6, Artillery, or Locust
7. **Deploy** → Docker, K8s, or serverless
