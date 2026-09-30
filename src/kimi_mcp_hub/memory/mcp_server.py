"""Stdio MCP server exposing Kimi's persistent memory to the model.

Hooks already capture observations into SQLite, but until now only a human
could query them from the CLI. This server closes that gap: the model can
search its own history mid-session.

Retrieval follows a three-layer workflow that keeps token cost proportional to
what is actually needed:

1. ``memory_search`` returns a compact index (id, time, type, title).
2. ``memory_timeline`` expands the neighbourhood around one interesting id.
3. ``memory_get`` fetches full bodies for a filtered set of ids.

Skipping straight to full bodies is what makes naive memory tools expensive,
so the index deliberately omits ``content``.

The MCP wire format is newline-delimited JSON-RPC 2.0 over stdin/stdout,
implemented directly so the package keeps its zero-dependency install.
Nothing except protocol frames may be written to stdout.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Callable

from .db import MemoryDB
from .embeddings import EmbeddingClient

SERVER_NAME = "kimi-memory"
DEFAULT_PROTOCOL_VERSION = "2024-11-05"
SUPPORTED_PROTOCOL_VERSIONS = frozenset({"2024-11-05", "2025-03-26", "2025-06-18"})

# JSON-RPC error codes (subset of the spec that this server can emit).
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603

_PROJECT_PARAMS = {
    "project": {
        "type": "string",
        "description": (
            "Absolute project path to scope results to. "
            "Defaults to the current working directory."
        ),
    },
    "all_projects": {
        "type": "boolean",
        "description": "Search across every project instead of just this one.",
        "default": False,
    },
}

TOOLS: list[dict[str, Any]] = [
    {
        "name": "memory_search",
        "description": (
            "Step 1 of 3. Full-text search across past sessions. Returns a compact "
            "index (id, time, type, title) without bodies, so it is cheap to call. "
            "Use memory_timeline to see context around a hit and memory_get to read "
            "the full text of the ids you care about."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search terms. Punctuation and quotes are safe.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum results (default 20, max 100).",
                    "default": 20,
                },
                "type": {
                    "type": "string",
                    "description": "Filter by observation type, e.g. 'session' or 'tool'.",
                },
                "mode": {
                    "type": "string",
                    "enum": ["keyword", "semantic", "hybrid"],
                    "description": (
                        "Search mode. 'keyword' (default) is full-text matching; "
                        "'semantic' matches by meaning via embeddings; 'hybrid' "
                        "merges both. Semantic modes fall back to keyword when "
                        "embeddings are unavailable."
                    ),
                    "default": "keyword",
                },
                **_PROJECT_PARAMS,
            },
            "required": ["query"],
        },
    },
    {
        "name": "memory_timeline",
        "description": (
            "Step 2 of 3. Show the observations immediately before and after an id "
            "returned by memory_search, to recover what was happening around it."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "anchor_id": {
                    "type": "integer",
                    "description": "Observation id to centre the timeline on.",
                },
                "before": {
                    "type": "integer",
                    "description": "How many observations before the anchor (default 3).",
                    "default": 3,
                },
                "after": {
                    "type": "integer",
                    "description": "How many observations after the anchor (default 3).",
                    "default": 3,
                },
                **_PROJECT_PARAMS,
            },
            "required": ["anchor_id"],
        },
    },
    {
        "name": "memory_get",
        "description": (
            "Step 3 of 3. Fetch the full content of specific observation ids. "
            "Only call this for ids you already filtered down to."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "ids": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Observation ids to fetch (max 20).",
                },
            },
            "required": ["ids"],
        },
    },
    {
        "name": "memory_summarize",
        "description": (
            "Record a summary of the current conversation so future sessions can "
            "resume from it. Call this when a [Memory] hook asks for it, passing "
            "the session_id it gives you. Include what was asked, what was done "
            "(file paths, and the key content of anything that exists only in "
            "chat), decisions with reasons, and what is still open."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Session id supplied by the [Memory] hook.",
                },
                "title": {
                    "type": "string",
                    "description": "One specific line, at most 90 characters.",
                },
                "summary": {
                    "type": "string",
                    "description": "Markdown summary, under 200 words.",
                },
                "project": {
                    "type": "string",
                    "description": "Project path (defaults to the session's project).",
                },
            },
            "required": ["session_id", "summary"],
        },
    },
    {
        "name": "memory_save",
        "description": (
            "Store a durable note for this project: a decision, a convention, a "
            "gotcha worth surviving the session. Unlike captured tool observations, "
            "saved notes are injected at the start of future sessions."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "The note to remember."},
                "category": {
                    "type": "string",
                    "description": (
                        "Note category. Use 'project' (the default) for notes that "
                        "should be injected at session start."
                    ),
                    "default": "project",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional tags for later filtering.",
                },
                "project": {
                    "type": "string",
                    "description": "Project path (defaults to the working directory).",
                },
            },
            "required": ["content"],
        },
    },
]

MAX_SEARCH_LIMIT = 100
MAX_GET_IDS = 20


def _project_scope(args: dict[str, Any]) -> str | None:
    """Return the project path to filter on, or None for all projects."""
    if args.get("all_projects"):
        return None
    explicit = args.get("project")
    raw = explicit if isinstance(explicit, str) and explicit.strip() else os.getcwd()
    try:
        return str(Path(raw).resolve())
    except OSError:
        return raw


def _short_time(timestamp: str) -> str:
    """Trim an ISO timestamp to 'YYYY-MM-DD HH:MM'."""
    return timestamp.replace("T", " ")[:16] if timestamp else ""


def _title(row: dict[str, Any], limit: int = 90) -> str:
    """Return a one-line label for an observation."""
    text = (row.get("summary") or row.get("content") or "").strip()
    text = " ".join(text.split())
    return text[:limit] if text else "(no summary)"


def _format_index(rows: list[dict[str, Any]]) -> str:
    lines = [
        f"#{row['id']}  {_short_time(row['timestamp'])}  {row['type']:<8} {_title(row)}"
        for row in rows
    ]
    return "\n".join(lines)


def _format_full(rows: list[dict[str, Any]]) -> str:
    blocks = []
    for row in rows:
        header = f"#{row['id']}  {_short_time(row['timestamp'])}  [{row['type']}]"
        if row.get("project_path"):
            header += f"  {row['project_path']}"
        body = row.get("content") or ""
        summary = row.get("summary") or ""
        parts = [header]
        if summary and summary not in body:
            parts.append(summary)
        if body:
            parts.append(body)
        blocks.append("\n".join(parts))
    return "\n\n---\n\n".join(blocks)


def _reciprocal_rank_fusion(*rankings: list[int], k: int = 60) -> list[int]:
    """Merge ranked id lists by Reciprocal Rank Fusion, best first."""
    scores: dict[int, float] = {}
    for ranking in rankings:
        for rank, row_id in enumerate(ranking):
            scores[row_id] = scores.get(row_id, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores, key=lambda row_id: scores[row_id], reverse=True)


class MemoryMCPServer:
    """Dispatches MCP requests against the local memory database."""

    def __init__(
        self, db: MemoryDB | None = None, embedding_client: EmbeddingClient | None = None
    ):
        self._db = db
        self._embedding_client = embedding_client
        self._initialized = False

    @property
    def db(self) -> MemoryDB:
        # Opened lazily so a failing database cannot stop the handshake.
        if self._db is None:
            self._db = MemoryDB()
        return self._db

    @property
    def embedding_client(self) -> EmbeddingClient:
        # Lazy: only semantic/hybrid searches ever need it.
        if self._embedding_client is None:
            self._embedding_client = EmbeddingClient.from_config()
        return self._embedding_client

    # ---- tools -------------------------------------------------------

    def tool_memory_search(self, args: dict[str, Any]) -> str:
        query = str(args.get("query") or "").strip()
        if not query:
            raise ValueError("query must not be empty")
        limit = min(max(int(args.get("limit", 20)), 1), MAX_SEARCH_LIMIT)
        project = _project_scope(args)
        obs_type = args.get("type") or None
        mode = str(args.get("mode") or "keyword").lower()
        if mode not in ("keyword", "semantic", "hybrid"):
            raise ValueError("mode must be 'keyword', 'semantic' or 'hybrid'")

        def keyword_rows() -> list[dict[str, Any]]:
            return self.db.search_index(
                query, limit=limit, project_path=project, obs_type=obs_type
            )

        note = ""
        if mode == "keyword":
            rows = keyword_rows()
        else:
            vec_rows: list[dict[str, Any]] = []
            semantic_ran = False
            client = self.embedding_client
            if self.db.vec_available and client.available:
                embeddings = client.embed([query])
                if embeddings:
                    vec_rows = self.db.vector_search(
                        embeddings[0],
                        limit=limit,
                        project_path=project,
                        obs_type=obs_type,
                    )
                    semantic_ran = True
            if mode == "semantic" and semantic_ran:
                rows = vec_rows
            elif mode == "hybrid" and semantic_ran:
                fts_rows = keyword_rows()
                merged = _reciprocal_rank_fusion(
                    [r["id"] for r in vec_rows], [r["id"] for r in fts_rows]
                )[:limit]
                by_id = {r["id"]: r for r in self.db.get_observations_by_ids(merged)}
                rows = [by_id[row_id] for row_id in merged if row_id in by_id]
            else:
                rows = keyword_rows()
                note = "[semantic search unavailable; showing keyword results]"

        if not rows:
            scope = "this project" if project else "any project"
            return (
                f"No memory matches for {query!r} in {scope}.\n"
                "Try fewer or broader terms, or set all_projects=true."
            )
        header = f"{len(rows)} match(es)"
        if note:
            header += f" {note}"
        return (
            f"{header}:\n"
            f"{_format_index(rows)}\n\n"
            "Next: memory_timeline(anchor_id) for context, memory_get([ids]) for full text."
        )

    def tool_memory_timeline(self, args: dict[str, Any]) -> str:
        anchor_id = int(args["anchor_id"])
        before = min(max(int(args.get("before", 3)), 0), 25)
        after = min(max(int(args.get("after", 3)), 0), 25)
        rows = self.db.timeline(
            anchor_id, before=before, after=after, project_path=_project_scope(args)
        )
        if not rows:
            return f"No observation with id {anchor_id}."
        lines = []
        for row in rows:
            marker = ">" if row["id"] == anchor_id else " "
            lines.append(
                f"{marker} #{row['id']}  {_short_time(row['timestamp'])}  "
                f"{row['type']:<8} {_title(row)}"
            )
        return "\n".join(lines)

    def tool_memory_get(self, args: dict[str, Any]) -> str:
        raw_ids = args.get("ids") or []
        if not isinstance(raw_ids, list) or not raw_ids:
            raise ValueError("ids must be a non-empty array of integers")
        ids = [int(value) for value in raw_ids[:MAX_GET_IDS]]
        rows = self.db.get_observations_by_ids(ids)
        if not rows:
            return f"No observations found for ids {ids}."
        text = _format_full(rows)
        if len(raw_ids) > MAX_GET_IDS:
            text += (
                f"\n\n[{len(raw_ids) - MAX_GET_IDS} more id(s) omitted; call again.]"
            )
        return text

    def tool_memory_save(self, args: dict[str, Any]) -> str:
        content = str(args.get("content") or "").strip()
        if not content:
            raise ValueError("content must not be empty")
        tags = args.get("tags") or []
        if not isinstance(tags, list):
            raise ValueError("tags must be an array of strings")
        project = _project_scope({"project": args.get("project")})
        memory_id = self.db.add_memory(
            content=content,
            category=str(args.get("category") or "project"),
            tags=[str(tag) for tag in tags],
            project_path=project,
        )
        return f"Saved memory #{memory_id} for {project}."

    def tool_memory_summarize(self, args: dict[str, Any]) -> str:
        from .hooks import strip_private

        session_id = str(args.get("session_id") or "").strip()
        summary = strip_private(str(args.get("summary") or "")).strip()
        if not session_id or not summary:
            raise ValueError("session_id and summary must not be empty")
        title = " ".join(strip_private(str(args.get("title") or "")).split())
        if not title:
            title = " ".join(summary.lstrip("#- *").split("\n", 1)[0].split())
        title = title[:160]

        explicit = args.get("project")
        if isinstance(explicit, str) and explicit.strip():
            project = _project_scope({"project": explicit})
        else:
            known = self.db.get_recent(session_id=session_id, limit=1)
            project = (known[0]["project_path"] if known else None) or _project_scope(
                {}
            )

        self.db.delete_observations(session_id, "session")
        row_id = self.db.add_observation(
            session_id=session_id,
            obs_type="session",
            content=f"Title: {title}\n\n{summary}",
            summary=title,
            tags=["session", "model"],
            project_path=project,
        )
        return f"Saved session summary #{row_id} for {project}."

    # ---- protocol ----------------------------------------------------

    def _tool_handlers(self) -> dict[str, Callable[[dict[str, Any]], str]]:
        return {
            "memory_search": self.tool_memory_search,
            "memory_timeline": self.tool_memory_timeline,
            "memory_get": self.tool_memory_get,
            "memory_summarize": self.tool_memory_summarize,
            "memory_save": self.tool_memory_save,
        }

    def handle(self, message: dict[str, Any]) -> dict[str, Any] | None:
        """Handle one JSON-RPC message; returns None for notifications."""
        method = message.get("method")
        msg_id = message.get("id")
        params = message.get("params") or {}
        is_notification = msg_id is None

        if not isinstance(method, str):
            if is_notification:
                return None
            return _error(msg_id, INVALID_REQUEST, "missing method")

        if method == "initialize":
            self._initialized = True
            requested = params.get("protocolVersion")
            version = (
                requested
                if requested in SUPPORTED_PROTOCOL_VERSIONS
                else DEFAULT_PROTOCOL_VERSION
            )
            return _result(
                msg_id,
                {
                    "protocolVersion": version,
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {
                        "name": SERVER_NAME,
                        "version": _package_version(),
                    },
                },
            )

        if method in ("notifications/initialized", "initialized"):
            return None

        if method == "ping":
            return None if is_notification else _result(msg_id, {})

        if method == "tools/list":
            return _result(msg_id, {"tools": TOOLS})

        if method == "tools/call":
            name = params.get("name")
            handler = self._tool_handlers().get(name)
            if handler is None:
                return _error(msg_id, METHOD_NOT_FOUND, f"unknown tool: {name}")
            arguments = params.get("arguments") or {}
            if not isinstance(arguments, dict):
                return _error(msg_id, INVALID_PARAMS, "arguments must be an object")
            try:
                text = handler(arguments)
            except (KeyError, TypeError, ValueError) as exc:
                return _result(msg_id, _tool_error(f"Invalid arguments: {exc}"))
            except Exception as exc:  # pragma: no cover - defensive
                return _result(msg_id, _tool_error(f"Memory lookup failed: {exc}"))
            return _result(
                msg_id,
                {"content": [{"type": "text", "text": text}], "isError": False},
            )

        if is_notification:
            return None
        return _error(msg_id, METHOD_NOT_FOUND, f"unknown method: {method}")


def _package_version() -> str:
    try:
        from .. import __version__

        return __version__
    except Exception:  # pragma: no cover - defensive
        return "0"


def _result(msg_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def _error(msg_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}


def _tool_error(message: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": message}], "isError": True}


def serve(stdin=None, stdout=None, db: MemoryDB | None = None) -> int:
    """Run the stdio loop until stdin closes."""
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    server = MemoryMCPServer(db=db)

    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            _write(stdout, _error(None, PARSE_ERROR, "invalid JSON"))
            continue
        if not isinstance(message, dict):
            _write(stdout, _error(None, INVALID_REQUEST, "expected an object"))
            continue
        response = server.handle(message)
        if response is not None:
            _write(stdout, response)
    return 0


def _write(stream, payload: dict[str, Any]) -> None:
    stream.write(json.dumps(payload, ensure_ascii=False) + "\n")
    stream.flush()


def main() -> int:
    return serve()


if __name__ == "__main__":
    raise SystemExit(main())
