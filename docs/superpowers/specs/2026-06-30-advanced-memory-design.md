# Advanced Memory Layer Design

## Overview

Add a long-term memory store to `kimi-mcp-hub` that feels like a lightweight, local `mem0` / `claude-mem`. Users can manually save facts, preferences, and project context, then search them later from the CLI or have relevant memories injected at session start.

This version is **manual-only** and requires **no API key**. Automatic LLM extraction can be added later without changing the schema.

## Goals

- Store long-term memories outside the per-session `observations` stream.
- Make memories searchable from the CLI.
- Surface relevant project memories at the start of a session.
- Keep everything local (SQLite + FTS5) and dependency-free.

## Non-goals

- Vector embeddings / semantic similarity.
- Automatic extraction from conversations (future iteration).
- Multi-user or cloud sync.

## Data model

A new `memories` table is added to the existing SQLite memory database:

```sql
CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    category TEXT NOT NULL,
    content TEXT NOT NULL,
    tags TEXT,
    project_path TEXT
);
```

And a matching FTS5 virtual table:

```sql
CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
    content, tags,
    content='memories',
    content_rowid='id'
);
```

- `category` — e.g. `user`, `project`, `general`.
- `tags` — JSON list.
- `project_path` — absolute path to the project this memory belongs to (optional).

Existing databases are migrated automatically: the new tables are created on the next `MemoryDB` initialization if they do not exist.

## API

`MemoryDB` grows the following methods:

- `add_memory(content, category="general", tags=None, project_path=None) -> int`
- `search_memories(query, limit=10, category=None, project_path=None) -> list[dict]`
- `get_memories(limit=20, category=None, project_path=None) -> list[dict]`
- `delete_memory(memory_id) -> bool`
- `get_memory_stats() -> dict`

`MemoryHooks.session_start` is updated to query project-specific memories and append them to the injected context.

## CLI

New subcommands under the existing `memory` group:

| Command | Description |
|---|---|
| `kimi-mcp-hub memory add "<content>" [--category user\|project\|general] [--tags tag1,tag2]` | Save a memory. |
| `kimi-mcp-hub memory search "<query>" [--limit N] [--category ...]` | Full-text search. |
| `kimi-mcp-hub memory list [--limit N] [--category ...]` | List recent memories. |
| `kimi-mcp-hub memory forget <id>` | Delete a memory by ID. |

When `--category project` is used without an explicit project path, the current working directory is used.

## Hook integration

`MemoryHooks.session_start` will:

1. Load recent observations (existing behavior).
2. Also load memories whose `project_path` matches the session's `project_path`.
3. Return a combined context block.

No new hooks are registered; the change is internal to `MemoryHooks`.

## Testing

- Unit tests for `MemoryDB` memory methods.
- CLI tests for `memory add`, `search`, `list`, `forget`.
- Hook test verifying project memories appear in `session_start` output.

## Dependencies

None beyond what is already used (`sqlite3`, `platformdirs`).
