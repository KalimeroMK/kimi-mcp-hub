"""SQLite database for persistent memory with FTS5."""

import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone

import platformdirs


def _default_memory_db() -> Path:
    """Return the default memory database path."""
    return (
        Path(platformdirs.user_config_dir("kimi-mcp-hub", "MoonshotAI")) / "memory.db"
    )


class MemoryDB:
    """Local SQLite database for cross-session memory."""

    @staticmethod
    def _default_memory_db() -> Path:
        """Return the default memory database path."""
        return _default_memory_db()

    def __init__(self, db_path: Path | None = None):
        if db_path is None:
            db_path = MemoryDB._default_memory_db()
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        """Open a connection with a busy timeout for concurrent hook writers."""
        conn = sqlite3.connect(str(self.db_path), timeout=10)
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def _init_db(self) -> None:
        """Initialize tables and FTS5 index."""
        with self._connect() as conn:
            # WAL allows concurrent readers while a hook is writing, which
            # matters when several Kimi sessions share one database.
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS observations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    summary TEXT,
                    tags TEXT,
                    project_path TEXT
                )
            """)
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS observations_fts USING fts5(
                    content, summary, tags,
                    content='observations',
                    content_rowid='id'
                )
            """)
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
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memories_project_path ON memories(project_path)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_observations_project_path ON observations(project_path)
            """)
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS memories_fts_insert
                AFTER INSERT ON memories
                BEGIN
                    INSERT INTO memories_fts (rowid, content, tags)
                    VALUES (NEW.id, NEW.content, NEW.tags);
                END
            """)
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS memories_fts_delete
                AFTER DELETE ON memories
                BEGIN
                    DELETE FROM memories_fts WHERE rowid = OLD.id;
                END
            """)
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS observations_fts_insert
                AFTER INSERT ON observations
                BEGIN
                    INSERT INTO observations_fts (rowid, content, summary, tags)
                    VALUES (NEW.id, NEW.content, NEW.summary, NEW.tags);
                END
            """)
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS observations_fts_delete
                AFTER DELETE ON observations
                BEGIN
                    DELETE FROM observations_fts WHERE rowid = OLD.id;
                END
            """)
            conn.commit()

    def add_observation(
        self,
        session_id: str,
        obs_type: str,
        content: str,
        summary: str | None = None,
        tags: list[str] | None = None,
        project_path: str | None = None,
    ) -> int:
        """Add an observation and index it."""
        tags_str = json.dumps(tags or [])
        timestamp = datetime.now(timezone.utc).isoformat()

        with self._connect() as conn:
            cursor = conn.execute(
                """INSERT INTO observations (session_id, timestamp, type, content, summary, tags, project_path)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    session_id,
                    timestamp,
                    obs_type,
                    content,
                    summary,
                    tags_str,
                    project_path,
                ),
            )
            conn.commit()
        return cursor.lastrowid

    def search(
        self,
        query: str,
        limit: int = 10,
        project_path: str | None = None,
    ) -> list[dict]:
        """Full-text search across observations."""
        if limit < 0:
            raise ValueError("limit must be non-negative")
        if limit == 0 or not query.strip():
            return []
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            try:
                if project_path:
                    rows = conn.execute(
                        """SELECT o.* FROM observations o
                           JOIN observations_fts fts ON o.id = fts.rowid
                           WHERE observations_fts MATCH ? AND o.project_path = ?
                           ORDER BY rank LIMIT ?""",
                        (query, project_path, limit),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        """SELECT o.* FROM observations o
                           JOIN observations_fts fts ON o.id = fts.rowid
                           WHERE observations_fts MATCH ?
                           ORDER BY rank LIMIT ?""",
                        (query, limit),
                    ).fetchall()
            except sqlite3.OperationalError:
                return []
            return [dict(row) for row in rows]

    def get_recent(
        self,
        session_id: str | None = None,
        limit: int = 20,
    ) -> list[dict]:
        """Get recent observations."""
        if limit < 0:
            raise ValueError("limit must be non-negative")
        if limit == 0:
            return []
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            if session_id:
                rows = conn.execute(
                    "SELECT * FROM observations WHERE session_id = ? ORDER BY timestamp DESC LIMIT ?",
                    (session_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM observations ORDER BY timestamp DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            return [dict(row) for row in rows]

    def get_stats(self) -> dict:
        """Return database statistics."""
        with self._connect() as conn:
            total = conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0]
            sessions = conn.execute(
                "SELECT COUNT(DISTINCT session_id) FROM observations"
            ).fetchone()[0]
            return {"total_observations": total, "total_sessions": sessions}

    def add_memory(
        self,
        content: str,
        category: str = "general",
        tags: list[str] | None = None,
        project_path: str | None = None,
    ) -> int:
        """Add a long-term memory and index it."""
        if project_path:
            project_path = str(Path(project_path).resolve())
        tags_str = json.dumps(tags or [])
        timestamp = datetime.now(timezone.utc).isoformat()

        with self._connect() as conn:
            cursor = conn.execute(
                """INSERT INTO memories (timestamp, category, content, tags, project_path)
                   VALUES (?, ?, ?, ?, ?)""",
                (timestamp, category, content, tags_str, project_path),
            )
            conn.commit()
        return cursor.lastrowid

    def search_memories(
        self,
        query: str,
        limit: int = 10,
        category: str | None = None,
        project_path: str | None = None,
    ) -> list[dict]:
        """Full-text search across memories."""
        if project_path:
            project_path = str(Path(project_path).resolve())
        if limit < 0:
            raise ValueError("limit must be non-negative")
        if limit == 0 or not query.strip():
            return []
        sql = """SELECT m.* FROM memories m
                 JOIN memories_fts fts ON m.id = fts.rowid
                 WHERE memories_fts MATCH ?"""
        params: list[str | int | None] = [query]
        if category:
            sql += " AND m.category = ?"
            params.append(category)
        if project_path:
            sql += " AND m.project_path = ?"
            params.append(project_path)
        sql += " ORDER BY rank LIMIT ?"
        params.append(limit)

        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            try:
                rows = conn.execute(sql, params).fetchall()
            except sqlite3.OperationalError:
                return []
            return [dict(row) for row in rows]

    def get_memories(
        self,
        limit: int = 20,
        category: str | None = None,
        project_path: str | None = None,
    ) -> list[dict]:
        """Get recent memories, optionally filtered."""
        if project_path:
            project_path = str(Path(project_path).resolve())
        if limit < 0:
            raise ValueError("limit must be non-negative")
        if limit == 0:
            return []
        sql = "SELECT * FROM memories WHERE 1=1"
        params: list[str | int | None] = []
        if category:
            sql += " AND category = ?"
            params.append(category)
        if project_path:
            sql += " AND project_path = ?"
            params.append(project_path)
        sql += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(sql, params).fetchall()
            return [dict(row) for row in rows]

    def delete_memory(self, memory_id: int) -> bool:
        """Delete a memory; the FTS index is cleaned up by a trigger."""
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            conn.commit()
            return cursor.rowcount > 0

    def get_memory_stats(self) -> dict:
        """Return memory statistics."""
        with self._connect() as conn:
            total = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
            categories = conn.execute(
                "SELECT category, COUNT(*) FROM memories GROUP BY category"
            ).fetchall()
            return {"total_memories": total, "categories": dict(categories)}
