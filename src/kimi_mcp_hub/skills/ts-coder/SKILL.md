---
name: ts-coder
description: TypeScript specialisttype: prompt
whenToUse: When the user mentions TypeScript, TS, generics, or strict types
disableModelInvocation: false
---

# 📘 TypeScript Coder

When activated, delegate to **coder** sub-agent with TypeScript constraints.

## Principles

### Strict Mode (always)
```json
{
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "strictFunctionTypes": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true
  }
}
```

### Types over Interfaces (for objects)
```typescript
type User = {
  id: number;
  name: string;
};

interface Repository<T> {
  find(id: number): Promise<T | null>;
  save(item: T): Promise<void>;
}
```

### Generics with Constraints
```typescript
function pick<T extends Record<string, any>, K extends keyof T>(
  obj: T,
  keys: K[]
): Pick<T, K> {
  const result = {} as Pick<T, K>;
  for (const key of keys) {
    result[key] = obj[key];
  }
  return result;
}
```

### Discriminated Unions
```typescript
type Result<T> =
  | { status: 'success'; data: T }
  | { status: 'error'; error: string }
  | { status: 'loading' };

function handleResult<T>(result: Result<T>): T | null {
  switch (result.status) {
    case 'success': return result.data;
    case 'error': console.error(result.error); return null;
    case 'loading': return null;
  }
}
```

### Branded Types
```typescript
type UserId = number & { __brand: 'UserId' };
type PostId = number & { __brand: 'PostId' };

function createUserId(id: number): UserId {
  return id as UserId;
}

function getUser(id: UserId) { ... }
getUser(createUserId(1)); // ✅
getUser(1 as PostId);     // ❌ Type error
```

## Patterns

### Template Literal Types
```typescript
type EventName<T extends string> = `on${Capitalize<T>}`;
```

### Conditional Types
```typescript
type NonNullable<T> = T extends null | undefined ? never : T;
```

### Infer
```typescript
type ReturnType<T> = T extends (...args: any[]) => infer R ? R : never;
```

## Tooling
- **tsc** — type checker
- **tsup** — bundler
- **tsx** — runner
- **vitest** — testing
- **eslint** + **typescript-eslint** — linting
