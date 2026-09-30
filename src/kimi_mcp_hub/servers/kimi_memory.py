"""Kimi memory MCP server configuration.

Unlike the other entries in this package, the server is shipped inside
kimi-mcp-hub itself rather than fetched with npx: it reads the same local
SQLite database the memory hooks write to, so it must run in the interpreter
that owns that database.
"""

import sys
from typing import Any


class KimiMemoryServer:
    """Local persistent memory exposed to the model over MCP.

    The hooks capture observations; this server lets the model retrieve them
    mid-session via a three-step workflow (search -> timeline -> get) instead
    of relying only on the fixed context injected at session start.
    """

    name = "kimi-memory"
    display_name = "Kimi Memory"
    description = (
        "Search your own cross-session memory. Runs locally against the SQLite "
        "database the memory hooks write to -- no API key, no network."
    )
    icon = "🧠"

    @classmethod
    def get_stdio_config(cls, python_executable: str | None = None) -> dict[str, Any]:
        """Return the stdio config for the bundled memory server.

        ``python_executable`` defaults to the interpreter running the CLI, so
        the server is launched from the environment where kimi-mcp-hub (and
        therefore the memory database) actually lives.
        """
        return {
            "command": python_executable or sys.executable,
            "args": ["-m", "kimi_mcp_hub.memory.mcp_server"],
            "env": {},
        }

    @classmethod
    def get_tools(cls) -> list[dict[str, str]]:
        return [
            {
                "name": "memory_search",
                "desc": "Search past sessions, returns a compact index",
            },
            {
                "name": "memory_timeline",
                "desc": "Show observations around a search hit",
            },
            {"name": "memory_get", "desc": "Fetch full text for specific ids"},
            {
                "name": "memory_summarize",
                "desc": "Record a summary of the current conversation",
            },
            {"name": "memory_save", "desc": "Store a durable note for this project"},
        ]
