"""Supabase MCP server configuration."""

from typing import Any


class SupabaseServer:
    """Supabase MCP server — PostgreSQL + realtime + auth + storage."""

    name = "supabase"
    display_name = "Supabase"
    description = "Query Supabase database, manage auth, storage, realtime subscriptions, edge functions."
    icon = "⚡"

    @classmethod
    def get_stdio_config(cls, url: str, key: str) -> dict[str, Any]:
        return {
            "command": "npx",
            "args": ["-y", "@supabase/mcp-server"],
            "env": {
                "SUPABASE_URL": url,
                "SUPABASE_KEY": key,
            }
        }

    @classmethod
    def get_tools(cls) -> list[dict[str, str]]:
        return [
            {"name": "supabase_query", "desc": "Execute SQL query"},
            {"name": "supabase_schema", "desc": "Read database schema"},
            {"name": "supabase_auth_users", "desc": "List auth users"},
            {"name": "supabase_storage_list", "desc": "List storage buckets"},
            {"name": "supabase_edge_functions", "desc": "List edge functions"},
            {"name": "supabase_realtime_subscribe", "desc": "Subscribe to realtime channel"},
        ]
