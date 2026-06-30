# Advanced Memory Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a manual, SQLite-backed long-term memory store with CLI commands and session-start injection.

**Architecture:** A new `memories` table + FTS5 index is added to the existing `MemoryDB`. Public methods provide add/search/list/delete. New `kimi-mcp-hub memory *` subcommands wrap those methods. `MemoryHooks.session_start` queries project memories and includes them in the injected context.

**Tech Stack:** Python 3.11+, `sqlite3`, `click`, `rich`, existing `MemoryDB`/`MemoryHooks`.

---

## Task 1: Extend MemoryDB schema and methods

**Files:**
- Modify: `src/kimi_mcp_hub/memory/db.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Add memories table migration**

Extend `_init_db` with the new table and FTS5 index:

```python
conn.execute("""
    CREATE TABLE IF NOT EXISTS memories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        category TEXT NOT NULL,
        content TEXT NOT NULL,
        tags TEXT,
        project_path TEXT
    )
""")
conn.execute("""
    CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
        content, tags,
        content='memories',
        content_rowid='id'
    )
""")
```

- [ ] **Step 2: Add `add_memory`**

```python
def add_memory(
    self,
    content: str,
    category: str = "general",
    tags: list[str] | None = None,
    project_path: str | None = None,
) -> int:
    tags_str = json.dumps(tags or [])
    timestamp = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(str(self.db_path)) as conn:
        cursor = conn.execute(
            """INSERT INTO memories (timestamp, category, content, tags, project_path)
               VALUES (?, ?, ?, ?, ?)""",
            (timestamp, category, content, tags_str, project_path),
        )
        mem_id = cursor.lastrowid
        conn.execute(
            """INSERT INTO memories_fts (rowid, content, tags)
               VALUES (?, ?, ?)""",
            (mem_id, content, tags_str),
        )
        conn.commit()
    return mem_id
```

- [ ] **Step 3: Add `search_memories`**

```python
def search_memories(
    self,
    query: str,
    limit: int = 10,
    category: str | None = None,
    project_path: str | None = None,
) -> list[dict]:
    sql = """SELECT m.* FROM memories m
             JOIN memories_fts fts ON m.id = fts.rowid
             WHERE memories_fts MATCH ?"""
    params: list[Any] = [query]
    if category:
        sql += " AND m.category = ?"
        params.append(category)
    if project_path:
        sql += " AND m.project_path = ?"
        params.append(project_path)
    sql += " ORDER BY rank LIMIT ?"
    params.append(limit)
    with sqlite3.connect(str(self.db_path)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]
```

- [ ] **Step 4: Add `get_memories`**

```python
def get_memories(
    self,
    limit: int = 20,
    category: str | None = None,
    project_path: str | None = None,
) -> list[dict]:
    sql = "SELECT * FROM memories WHERE 1=1"
    params: list[Any] = []
    if category:
        sql += " AND category = ?"
        params.append(category)
    if project_path:
        sql += " AND project_path = ?"
        params.append(project_path)
    sql += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    with sqlite3.connect(str(self.db_path)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]
```

- [ ] **Step 5: Add `delete_memory`**

```python
def delete_memory(self, memory_id: int) -> bool:
    with sqlite3.connect(str(self.db_path)) as conn:
        cursor = conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        conn.execute("DELETE FROM memories_fts WHERE rowid = ?", (memory_id,))
        conn.commit()
        return cursor.rowcount > 0
```

- [ ] **Step 6: Add `get_memory_stats`**

```python
def get_memory_stats(self) -> dict:
    with sqlite3.connect(str(self.db_path)) as conn:
        total = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        categories = conn.execute(
            "SELECT category, COUNT(*) FROM memories GROUP BY category"
        ).fetchall()
        return {"total_memories": total, "categories": dict(categories)}
```

- [ ] **Step 7: Write MemoryDB tests**

Append to `tests/test_config.py` under `TestMemoryDB`:

```python
def test_add_and_search_memory(self, tmp_path):
    db = MemoryDB(db_path=tmp_path / "memory.db")
    db.add_memory("Use pytest for tests", category="user", tags=["testing"])
    results = db.search_memories("pytest")
    assert len(results) == 1
    assert results[0]["content"] == "Use pytest for tests"

def test_get_memories_by_category(self, tmp_path):
    db = MemoryDB(db_path=tmp_path / "memory.db")
    db.add_memory("project fact", category="project", project_path="/foo")
    db.add_memory("user fact", category="user")
    assert len(db.get_memories(category="project")) == 1

def test_delete_memory(self, tmp_path):
    db = MemoryDB(db_path=tmp_path / "memory.db")
    mem_id = db.add_memory("to delete")
    assert db.delete_memory(mem_id) is True
    assert db.delete_memory(mem_id) is False
```

- [ ] **Step 8: Run tests and commit**

```bash
source .venv/bin/activate
python -m pytest tests/test_config.py -v
git add src/kimi_mcp_hub/memory/db.py tests/test_config.py
git commit -m "feat(memory): add long-term memories table and methods"
```

---

## Task 2: Add memory CLI subcommands

**Files:**
- Modify: `src/kimi_mcp_hub/cli.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Add helper to resolve project path**

Near the other helpers, add:

```python
def _resolve_memory_project_path(path: str | None) -> str | None:
    if path:
        return str(Path(path).resolve())
    project_root = find_project_root()
    return str(project_root.resolve()) if project_root else None
```

- [ ] **Step 2: Add `memory add` command**

```python
@memory.command(name="add")
@click.argument("content")
@click.option("--category", default="general", show_default=True,
              help="Memory category (user, project, general).")
@click.option("--tags", help="Comma-separated tags.")
@click.option("--project-path", type=click.Path(path_type=Path),
              help="Project path for project-scoped memories.")
def add_memory_cmd(content: str, category: str, tags: str | None,
                   project_path: Path | None):
    """Save a long-term memory."""
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    project = _resolve_memory_project_path(str(project_path) if project_path else None)
    db = MemoryDB()
    mem_id = db.add_memory(
        content=content,
        category=category,
        tags=tag_list,
        project_path=project,
    )
    console.print(f"[green]Saved memory {mem_id}[/green]")
```

- [ ] **Step 3: Add `memory search` command**

```python
@memory.command(name="search")
@click.argument("query")
@click.option("--limit", default=10, show_default=True, help="Max results.")
@click.option("--category", help="Filter by category.")
@click.option("--project-path", type=click.Path(path_type=Path),
              help="Filter by project path.")
def search_memory_cmd(query: str, limit: int, category: str | None,
                      project_path: Path | None):
    """Search saved memories."""
    project = _resolve_memory_project_path(str(project_path) if project_path else None)
    db = MemoryDB()
    results = db.search_memories(
        query=query, limit=limit, category=category, project_path=project
    )
    if not results:
        console.print("[dim]No memories found.[/dim]")
        return
    for mem in results:
        console.print(f"[cyan]{mem['id']}[/cyan] [{mem['category']}] {mem['content']}")
```

- [ ] **Step 4: Add `memory list` command**

```python
@memory.command(name="list")
@click.option("--limit", default=20, show_default=True)
@click.option("--category", help="Filter by category.")
@click.option("--project-path", type=click.Path(path_type=Path),
              help="Filter by project path.")
def list_memory_cmd(limit: int, category: str | None, project_path: Path | None):
    """List recent memories."""
    project = _resolve_memory_project_path(str(project_path) if project_path else None)
    db = MemoryDB()
    results = db.get_memories(limit=limit, category=category, project_path=project)
    if not results:
        console.print("[dim]No memories found.[/dim]")
        return
    for mem in results:
        console.print(f"[cyan]{mem['id']}[/cyan] [{mem['category']}] {mem['content']}")
```

- [ ] **Step 5: Add `memory forget` command**

```python
@memory.command(name="forget")
@click.argument("memory_id", type=int)
def forget_memory_cmd(memory_id: int):
    """Delete a memory by ID."""
    db = MemoryDB()
    if db.delete_memory(memory_id):
        console.print(f"[green]Forgot memory {memory_id}[/green]")
    else:
        console.print(f"[red]Memory {memory_id} not found.[/red]")
        sys.exit(1)
```

- [ ] **Step 6: Write CLI tests**

Append to `tests/test_cli.py`:

```python
class TestMemoryCommands:
    def test_memory_add_and_search(self, tmp_path, monkeypatch):
        from kimi_mcp_hub.memory.db import MemoryDB
        db_path = tmp_path / "memory.db"
        monkeypatch.setattr(MemoryDB, "_default_memory_db", lambda: db_path)
        runner = CliRunner()
        runner.invoke(main, ["memory", "add", "use ruff", "--category", "user"])
        result = runner.invoke(main, ["memory", "search", "ruff"])
        assert result.exit_code == 0
        assert "use ruff" in result.output

    def test_memory_forget(self, tmp_path, monkeypatch):
        from kimi_mcp_hub.memory.db import MemoryDB
        db_path = tmp_path / "memory.db"
        monkeypatch.setattr(MemoryDB, "_default_memory_db", lambda: db_path)
        runner = CliRunner()
        runner.invoke(main, ["memory", "add", "delete me"])
        search = runner.invoke(main, ["memory", "search", "delete"])
        mem_id = int(search.output.strip().split()[0])
        result = runner.invoke(main, ["memory", "forget", str(mem_id)])
        assert result.exit_code == 0
        assert "Forgot" in result.output
```

- [ ] **Step 7: Run tests and commit**

```bash
source .venv/bin/activate
python -m pytest tests/test_cli.py::TestMemoryCommands -v
ruff check src/kimi_mcp_hub/cli.py tests/test_cli.py
git add src/kimi_mcp_hub/cli.py tests/test_cli.py
git commit -m "feat(cli): add memory add/search/list/forget commands"
```

---

## Task 3: Inject project memories on session start

**Files:**
- Modify: `src/kimi_mcp_hub/memory/hooks.py`
- Test: `tests/test_obsidian.py` or `tests/test_memory_hooks.py`

- [ ] **Step 1: Update `session_start` to include project memories**

Replace the method body with:

```python
def session_start(self, payload: dict) -> str:
    session_id = payload.get("session_id", "unknown")
    project_path = payload.get("project_path", "")
    parts: list[str] = []

    recent = self.db.get_recent(limit=5)
    if recent:
        parts.append("\n[Memory] Recent context:")
        for obs in recent:
            parts.append(
                f"- [{obs['type']}] {obs['summary'] or obs['content'][:100]}"
            )

    if project_path:
        memories = self.db.get_memories(
            limit=10, category="project", project_path=project_path
        )
        if memories:
            parts.append("\n[Memory] Project notes:")
            for mem in memories:
                parts.append(f"- {mem['content']}")

    return "\n".join(parts)
```

- [ ] **Step 2: Add hook test**

Append to `tests/test_obsidian.py` (or create `tests/test_memory_hooks.py`):

```python
class TestMemoryHooksProjectMemory:
    def test_session_start_includes_project_memories(self, tmp_path):
        db = MemoryDB(db_path=tmp_path / "memory.db")
        hooks = MemoryHooks(db=db)
        db.add_memory(
            "Always run tests before push",
            category="project",
            project_path=str(tmp_path),
        )
        result = hooks.session_start({
            "session_id": "s1",
            "project_path": str(tmp_path),
        })
        assert "Always run tests before push" in result
```

- [ ] **Step 3: Run tests and commit**

```bash
source .venv/bin/activate
python -m pytest tests/test_obsidian.py::TestMemoryHooksProjectMemory -v
git add src/kimi_mcp_hub/memory/hooks.py tests/test_obsidian.py
git commit -m "feat(memory): inject project memories on session start"
```

---

## Task 4: Documentation

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add memory commands to the All Commands table**

Add rows:

```markdown
| `kimi-mcp-hub memory add "<content>" [--category ...] [--tags ...]` | Save a long-term memory |
| `kimi-mcp-hub memory search "<query>"` | Search saved memories |
| `kimi-mcp-hub memory list` | List recent memories |
| `kimi-mcp-hub memory forget <id>` | Delete a memory by ID |
```

- [ ] **Step 2: Add a short Memory section after Obsidian Local Memory**

Include examples:

```bash
kimi-mcp-hub memory add "Use ruff for linting" --category user --tags linting
kimi-mcp-hub memory add "API base URL is https://api.example.com" --category project
kimi-mcp-hub memory search "ruff"
kimi-mcp-hub memory list
kimi-mcp-hub memory forget 3
```

- [ ] **Step 3: Update Table of Contents**

- [ ] **Step 4: Run full verification and commit**

```bash
source .venv/bin/activate
python -m pytest -v
ruff check src/kimi_mcp_hub/memory/db.py src/kimi_mcp_hub/memory/hooks.py src/kimi_mcp_hub/cli.py tests
git add README.md
git commit -m "docs: document advanced memory commands"
```

---

## Self-review

- **Spec coverage:** memories table (Task 1), CLI commands (Task 2), hook integration (Task 3), docs (Task 4) — all covered.
- **Placeholder scan:** no TBD/TODO; code and commands are concrete.
- **Type consistency:** method names (`add_memory`, `search_memories`, etc.) match across DB, CLI, and tests.
