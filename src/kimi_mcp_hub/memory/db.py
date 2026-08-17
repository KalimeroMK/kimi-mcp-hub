"""SQLite database for persistent memory with FTS5."""

import hashlib
import logging
import re
import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone

import platformdirs

_logger = logging.getLogger(__name__)

# Splits a raw query into bare words and already-quoted phrases.
_FTS_TOKEN_RE = re.compile(r'"[^"]*"|\S+')

# Bare uppercase operators are dropped rather than searched for literally:
# FTS5 already ANDs terms, so "cache AND redis" should mean what the user
# expects instead of hunting for the word "AND". Matched case-sensitively so
# ordinary prose ("this and that") is still searched.
_FTS_OPERATORS = frozenset({"AND", "OR", "NOT", "NEAR"})

# Dropped in match-any mode only. A natural-language prompt ORed word by word
# would match almost every row through its filler words; removing them lets
# bm25 rank on the terms that actually carry meaning.
_STOPWORDS = frozenset(
    """
    the and for are but not you all can had her was one our out day get has him his
    how man new now old see two way who did its let put say she too use with this that
    from they what when where which while your about into over than them then there
    these those been have will would could should does doing done make made just like
    """.split()
)


def _default_memory_db() -> Path:
    """Return the default memory database path."""
    return (
        Path(platformdirs.user_config_dir("kimi-mcp-hub", "MoonshotAI")) / "memory.db"
    )


def content_hash(*parts: str) -> str:
    """Return a short stable hash used to deduplicate observations."""
    digest = hashlib.sha256("\x00".join(parts).encode("utf-8", "replace"))
    return digest.hexdigest()[:16]


def build_fts_query(raw: str, match_any: bool = False) -> str:
    """Escape a user query so FTS5 cannot raise a syntax error.

    Every bare term becomes a quoted phrase. This means input like
    ``what's this?`` or ``C++`` is searched literally instead of blowing up the
    MATCH parser and silently returning no rows. A trailing ``*`` is preserved
    as a prefix search, and quoted phrases the caller wrote are passed through.
    Bare boolean operators are dropped, so ``foo AND bar`` behaves the way a
    user expects.

    With ``match_any`` the terms are ORed and filler words are dropped. That is
    the right mode for retrieving against a whole sentence -- requiring every
    word of "what changed in the billing importer?" to appear would match
    nothing -- whereas the default AND keeps deliberate searches precise.
    """
    parts: list[str] = []
    for token in _FTS_TOKEN_RE.findall(raw):
        if token in _FTS_OPERATORS:
            continue
        if token.startswith('"') and token.endswith('"') and len(token) > 1:
            inner = token[1:-1].strip()
            if inner:
                parts.append('"' + inner.replace('"', '""') + '"')
            continue
        prefix = token.endswith("*")
        core = token[:-1] if prefix else token
        core = core.replace('"', "").strip()
        if not core:
            continue
        if match_any:
            word = core.strip(".,;:!?()[]{}'\"").lower()
            if len(word) < 3 or word in _STOPWORDS:
                continue
            core = word
        parts.append(f'"{core}"*' if prefix else f'"{core}"')
    return (" OR " if match_any else " ").join(parts)


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
                    project_path TEXT,
                    content_hash TEXT
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
            self._migrate(conn)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_observations_content_hash
                ON observations(session_id, content_hash)
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

    @staticmethod
    def _migrate(conn: sqlite3.Connection) -> None:
        """Apply additive schema migrations to databases created by older versions."""
        columns = {
            row[1] for row in conn.execute("PRAGMA table_info(observations)").fetchall()
        }
        if "content_hash" not in columns:
            conn.execute("ALTER TABLE observations ADD COLUMN content_hash TEXT")

    def add_observation(
        self,
        session_id: str,
        obs_type: str,
        content: str,
        summary: str | None = None,
        tags: list[str] | None = None,
        project_path: str | None = None,
        content_hash_value: str | None = None,
    ) -> int:
        """Add an observation and index it."""
        if project_path:
            project_path = str(Path(project_path).resolve())
        tags_str = json.dumps(tags or [])
        timestamp = datetime.now(timezone.utc).isoformat()

        with self._connect() as conn:
            cursor = conn.execute(
                """INSERT INTO observations
                   (session_id, timestamp, type, content, summary, tags, project_path, content_hash)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    session_id,
                    timestamp,
                    obs_type,
                    content,
                    summary,
                    tags_str,
                    project_path,
                    content_hash_value,
                ),
            )
            conn.commit()
        return cursor.lastrowid

    def has_observation(self, session_id: str, hash_value: str) -> bool:
        """Return True if this session already stored an identical observation."""
        if not hash_value:
            return False
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM observations WHERE session_id = ? AND content_hash = ? LIMIT 1",
                (session_id, hash_value),
            ).fetchone()
        return row is not None

    def search(
        self,
        query: str,
        limit: int = 10,
        project_path: str | None = None,
        obs_type: str | None = None,
        columns: str = "o.*",
        match_any: bool = False,
    ) -> list[dict]:
        """Full-text search across observations.

        The query is escaped before it reaches FTS5, so punctuation and stray
        boolean keywords are searched literally instead of raising a syntax
        error that used to surface as an empty result set. Pass ``match_any``
        to retrieve against a whole sentence rather than requiring every word.
        """
        if limit < 0:
            raise ValueError("limit must be non-negative")
        match_query = build_fts_query(query, match_any=match_any)
        if limit == 0 or not match_query:
            return []
        if project_path:
            project_path = str(Path(project_path).resolve())

        sql = f"""SELECT {columns} FROM observations o
                  JOIN observations_fts fts ON o.id = fts.rowid
                  WHERE observations_fts MATCH ?"""
        params: list[str | int] = [match_query]
        if project_path:
            sql += " AND o.project_path = ?"
            params.append(project_path)
        if obs_type:
            sql += " AND o.type = ?"
            params.append(obs_type)
        sql += " ORDER BY rank LIMIT ?"
        params.append(limit)

        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            try:
                rows = conn.execute(sql, params).fetchall()
            except sqlite3.OperationalError:
                _logger.warning(
                    "FTS search failed for query %r (escaped as %r)",
                    query,
                    match_query,
                    exc_info=True,
                )
                return []
            return [dict(row) for row in rows]

    def search_index(
        self,
        query: str,
        limit: int = 20,
        project_path: str | None = None,
        obs_type: str | None = None,
        match_any: bool = False,
    ) -> list[dict]:
        """Search returning only index fields, without the bulky ``content``."""
        return self.search(
            query,
            limit=limit,
            project_path=project_path,
            obs_type=obs_type,
            match_any=match_any,
            columns="o.id, o.timestamp, o.type, o.summary, o.tags, o.project_path, o.session_id",
        )

    def get_recent(
        self,
        session_id: str | None = None,
        limit: int = 20,
        project_path: str | None = None,
        obs_type: str | None = None,
    ) -> list[dict]:
        """Get recent observations, optionally scoped to a session or project."""
        if limit < 0:
            raise ValueError("limit must be non-negative")
        if limit == 0:
            return []
        if project_path:
            project_path = str(Path(project_path).resolve())

        sql = "SELECT * FROM observations WHERE 1=1"
        params: list[str | int] = []
        if session_id:
            sql += " AND session_id = ?"
            params.append(session_id)
        if project_path:
            sql += " AND project_path = ?"
            params.append(project_path)
        if obs_type:
            sql += " AND type = ?"
            params.append(obs_type)
        sql += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(sql, params).fetchall()
            return [dict(row) for row in rows]

    def browse_observations(
        self,
        limit: int = 50,
        offset: int = 0,
        project_path: str | None = None,
        obs_type: str | None = None,
        session_id: str | None = None,
    ) -> tuple[list[dict], int]:
        """Return a page of observations plus the total row count.

        Used by the web viewer, which needs stable offset pagination rather
        than the relevance ordering the search paths use.
        """
        if limit < 0 or offset < 0:
            raise ValueError("limit and offset must be non-negative")
        if project_path:
            project_path = str(Path(project_path).resolve())

        where = " WHERE 1=1"
        params: list[str | int] = []
        if project_path:
            where += " AND project_path = ?"
            params.append(project_path)
        if obs_type:
            where += " AND type = ?"
            params.append(obs_type)
        if session_id:
            where += " AND session_id = ?"
            params.append(session_id)

        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            total = conn.execute(
                f"SELECT COUNT(*) FROM observations{where}", params
            ).fetchone()[0]
            rows = conn.execute(
                f"SELECT * FROM observations{where} ORDER BY id DESC LIMIT ? OFFSET ?",
                [*params, limit, offset],
            ).fetchall()
            return [dict(row) for row in rows], total

    def list_projects(self) -> list[dict]:
        """Return distinct project paths with their observation counts."""
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT project_path, COUNT(*) AS count FROM observations
                   WHERE project_path IS NOT NULL AND project_path != ''
                   GROUP BY project_path ORDER BY count DESC"""
            ).fetchall()
            return [{"project_path": row[0], "count": row[1]} for row in rows]

    def list_types(self) -> list[str]:
        """Return the distinct observation types present in the database."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT DISTINCT type FROM observations ORDER BY type"
            ).fetchall()
            return [row[0] for row in rows]

    def get_observations_by_ids(self, ids: list[int]) -> list[dict]:
        """Fetch full observations for the given ids, in ascending id order."""
        if not ids:
            return []
        placeholders = ",".join("?" for _ in ids)
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                f"SELECT * FROM observations WHERE id IN ({placeholders}) ORDER BY id",
                list(ids),
            ).fetchall()
            return [dict(row) for row in rows]

    def timeline(
        self,
        anchor_id: int,
        before: int = 3,
        after: int = 3,
        project_path: str | None = None,
    ) -> list[dict]:
        """Return observations surrounding ``anchor_id`` in chronological order.

        Ordering uses the autoincrement id, which tracks insertion order and is
        stable even when several observations share a timestamp.
        """
        if before < 0 or after < 0:
            raise ValueError("before/after must be non-negative")
        if project_path:
            project_path = str(Path(project_path).resolve())

        scope = ""
        scope_params: list[str] = []
        if project_path:
            scope = " AND project_path = ?"
            scope_params.append(project_path)

        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            anchor = conn.execute(
                "SELECT * FROM observations WHERE id = ?", (anchor_id,)
            ).fetchone()
            if anchor is None:
                return []
            preceding = (
                conn.execute(
                    f"SELECT * FROM observations WHERE id < ?{scope} ORDER BY id DESC LIMIT ?",
                    [anchor_id, *scope_params, before],
                ).fetchall()
                if before
                else []
            )
            following = (
                conn.execute(
                    f"SELECT * FROM observations WHERE id > ?{scope} ORDER BY id ASC LIMIT ?",
                    [anchor_id, *scope_params, after],
                ).fetchall()
                if after
                else []
            )

        rows = [*reversed(preceding), anchor, *following]
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
        match_any: bool = False,
    ) -> list[dict]:
        """Full-text search across memories."""
        if project_path:
            project_path = str(Path(project_path).resolve())
        if limit < 0:
            raise ValueError("limit must be non-negative")
        match_query = build_fts_query(query, match_any=match_any)
        if limit == 0 or not match_query:
            return []
        sql = """SELECT m.* FROM memories m
                 JOIN memories_fts fts ON m.id = fts.rowid
                 WHERE memories_fts MATCH ?"""
        params: list[str | int | None] = [match_query]
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
                _logger.warning(
                    "FTS memory search failed for query %r (escaped as %r)",
                    query,
                    match_query,
                    exc_info=True,
                )
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
