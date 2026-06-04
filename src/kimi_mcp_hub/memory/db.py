"""SQLite database for persistent memory with FTS5."""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Optional


class MemoryDB:
    """Local SQLite database for cross-session memory."""

    def __init__(self, db_path: Path | None = None):
        if db_path is None:
            db_path = Path.home() / ".kimi" / "mcp-hub" / "memory.db"
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize tables and FTS5 index."""
        with sqlite3.connect(str(self.db_path)) as conn:
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
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    project_path TEXT,
                    summary TEXT
                )
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
        timestamp = datetime.utcnow().isoformat()

        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute(
                """INSERT INTO observations (session_id, timestamp, type, content, summary, tags, project_path)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (session_id, timestamp, obs_type, content, summary, tags_str, project_path),
            )
            obs_id = cursor.lastrowid
            conn.execute(
                """INSERT INTO observations_fts (rowid, content, summary, tags)
                   VALUES (?, ?, ?, ?)""",
                (obs_id, content, summary or "", tags_str),
            )
            conn.commit()
        return obs_id

    def search(
        self,
        query: str,
        limit: int = 10,
        project_path: str | None = None,
    ) -> list[dict]:
        """Full-text search across observations."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
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
            return [dict(row) for row in rows]

    def get_recent(
        self,
        session_id: str | None = None,
        limit: int = 20,
    ) -> list[dict]:
        """Get recent observations."""
        with sqlite3.connect(str(self.db_path)) as conn:
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
        with sqlite3.connect(str(self.db_path)) as conn:
            total = conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0]
            sessions = conn.execute("SELECT COUNT(DISTINCT session_id) FROM observations").fetchone()[0]
            return {"total_observations": total, "total_sessions": sessions}
