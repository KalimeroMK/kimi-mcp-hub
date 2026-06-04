---
name: python-engineer
description: >
  Python backend specialist. Activate for Python code, FastAPI, Django,
  data processing, async Python, or when user says "Python", "FastAPI",
  "Django", "asyncio", "uv", "Pydantic", "SQLAlchemy", "Celery",
  "data pipeline", "ETL", "pandas", "NumPy", "machine learning".
---

# 🐍 Python Engineer

When activated, delegate to **coder** sub-agent with Python constraints.

## Code Style

### Type Hints (always)
```python
from typing import Optional, TypedDict, NotRequired

def get_user(user_id: int) -> Optional[User]:
    ...

class UserResponse(TypedDict):
    id: int
    name: str
    email: NotRequired[str]
```

### Async First
```python
import asyncio

async def fetch_data(url: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        return resp.json()
```

### Error Handling
```python
class AppError(Exception):
    pass

class NotFoundError(AppError):
    pass

# Never bare except
try:
    ...
except NotFoundError:
    raise
except Exception as e:
    logger.exception("unexpected error")
    raise AppError("failed") from e
```

## Dependencies

### Web Framework
- **FastAPI** — APIs, async, auto-docs
- **Django** — full-stack, admin, ORM
- **Flask** — micro, simple APIs

### ORM / Database
- **SQLAlchemy 2.0** — type-safe, async
- **Prisma** — schema-first, type-safe
- **Django ORM** — if using Django

### Validation
- **Pydantic v2** — models, config, validation
- **msgspec** — faster alternative

### Async
- **asyncio** — built-in
- **httpx** — async HTTP client
- **aiofiles** — async file I/O
- **aioredis** — async Redis

### Task Queues
- **Celery** — mature, Redis/RabbitMQ
- **arq** — async, Redis
- **Dramatiq** — simple, Redis

### Testing
- **pytest** — testing framework
- **pytest-asyncio** — async tests
- **factory-boy** — test data
- **pytest-cov** — coverage

### Data
- **pandas** — data manipulation
- **Polars** — faster alternative
- **pydantic-settings** — env config

## Performance
- Use `uvloop` for event loop
- Connection pooling for DB
- Batch operations (bulk inserts)
- Avoid GIL: multiprocessing for CPU-bound
- Profile with `py-spy` or `scalene`

## Tooling
- **uv** — package manager (fast, modern)
- **ruff** — linter + formatter
- **mypy** — type checking
- **pre-commit** — git hooks
- **docker** — containerization
