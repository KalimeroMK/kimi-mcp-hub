---
name: api-designer
description: API design patterns and best practicestype: prompt
whenToUse: When the user mentions API design, REST, GraphQL, endpoints, or API architecture
disableModelInvocation: false
---

# 🔌 API Designer

## REST Principles

### 1. Resource-Oriented
```
GET    /users          # list
GET    /users/123      # get one
POST   /users          # create
PUT    /users/123      # full update
PATCH  /users/123      # partial update
DELETE /users/123      # remove
```

### 2. Status Codes
- `200` OK
- `201` Created (with Location header)
- `204` No Content (delete success)
- `400` Bad Request (validation error)
- `401` Unauthorized (not authenticated)
- `403` Forbidden (no permission)
- `404` Not Found
- `409` Conflict (duplicate, stale data)
- `422` Unprocessable Entity (semantic error)
- `429` Too Many Requests (rate limit)
- `500` Internal Server Error

### 3. Error Format
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Email is required",
    "field": "email",
    "request_id": "req_abc123"
  }
}
```

### 4. Pagination
```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 145,
    "total_pages": 8,
    "links": {
      "self": "/users?page=1",
      "next": "/users?page=2",
      "last": "/users?page=8"
    }
  }
}
```

## GraphQL Principles
- Single endpoint: `/graphql`
- Types over strings
- N+1 solved with DataLoader
- Mutations named as verbs: `createUser`, `updatePost`
- Subscriptions for real-time

## Versioning
- URL: `/v1/users`, `/v2/users`
- Header: `Accept: application/vnd.api+json;version=2`
- Never break existing consumers

## Documentation
- OpenAPI/Swagger spec
- Examples for every endpoint
- Authentication requirements
- Rate limits
