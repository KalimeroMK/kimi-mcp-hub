---
name: docker-pro
description: >
  Docker and container best practices. Activate when user says
  "docker", "container", "image", "Dockerfile", "compose", "kubernetes",
  "k8s", "deploy", "containerize", or when working with containerized apps.
---

# 🐳 Docker Pro

## Dockerfile Best Practices

### 1. Multi-stage Builds
```dockerfile
# Build stage
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Runtime stage
FROM node:20-alpine
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
COPY package.json ./
EXPOSE 3000
CMD ["node", "dist/main.js"]
```

### 2. Layer Caching
- Copy package files first (cacheable layer)
- Copy source code last (changes often)
- Use `npm ci` instead of `npm install`

### 3. Security
- Run as non-root: `USER node`
- Use distroless or alpine images
- Scan with `docker scan` or Trivy
- No secrets in ENV (use runtime injection)

### 4. Size Optimization
- Use `node:20-alpine` (not `node:20`)
- Remove dev dependencies: `npm prune --production`
- Clean caches: `rm -rf /var/cache/apk/*`

## Docker Compose
```yaml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
    depends_on:
      - db
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
  db:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_PASSWORD: ${DB_PASSWORD}
volumes:
  postgres_data:
```

## Kubernetes Quick Reference
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
      - name: app
        image: myapp:latest
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 3000
          initialDelaySeconds: 10
          periodSeconds: 30
```
