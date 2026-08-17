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


class MemoryMCPServer:
    """Dispatches MCP requests against the local memory database."""

    def __init__(self, db: MemoryDB | None = None):
        self._db = db
        self._initialized = False

    @property
    def db(self) -> MemoryDB:
        # Opened lazily so a failing database cannot stop the handshake.
        if self._db is None:
            self._db = MemoryDB()
        return self._db

    # ---- tools -------------------------------------------------------

    def tool_memory_search(self, args: dict[str, Any]) -> str:
        query = str(args.get("query") or "").strip()
        if not query:
            raise ValueError("query must not be empty")
        limit = min(max(int(args.get("limit", 20)), 1), MAX_SEARCH_LIMIT)
        project = _project_scope(args)
        rows = self.db.search_index(
            query,
            limit=limit,
            project_path=project,
            obs_type=args.get("type") or None,
        )
        if not rows:
            scope = "this project" if project else "any project"
            return (
                f"No memory matches for {query!r} in {scope}.\n"
                "Try fewer or broader terms, or set all_projects=true."
            )
        return (
            f"{len(rows)} match(es):\n"
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

    # ---- protocol ----------------------------------------------------

    def _tool_handlers(self) -> dict[str, Callable[[dict[str, Any]], str]]:
        return {
            "memory_search": self.tool_memory_search,
            "memory_timeline": self.tool_memory_timeline,
            "memory_get": self.tool_memory_get,
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
