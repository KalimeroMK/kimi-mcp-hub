"""Supabase MCP server configuration."""

from typing import Any


class SupabaseServer:
    """Supabase MCP server — official remote OAuth or local stdio with access token."""

    name = "supabase"
    display_name = "Supabase"
    description = "Query Supabase database, manage auth, storage, realtime subscriptions, edge functions."
    icon = "⚡"

    OFFICIAL_URL = "https://mcp.supabase.com/mcp"

    @classmethod
    def get_official_config(
        cls,
        project_ref: str | None = None,
        read_only: bool = True,
    ) -> dict[str, Any]:
        """Official Supabase remote MCP server (OAuth 2.1).

        Recommended — no npm package needed, Kimi CLI handles login.
        """
        params = {}
        if project_ref:
            params["project_ref"] = project_ref
        if read_only:
            params["read_only"] = "true"

        url = cls.OFFICIAL_URL
        if params:
            from urllib.parse import urlencode
            url = f"{url}?{urlencode(params)}"

        return {
            "transport": "http",
            "url": url,
            "auth": "oauth",
        }

    @classmethod
    def get_stdio_config(
        cls,
        access_token: str,
        project_ref: str | None = None,
        read_only: bool = True,
    ) -> dict[str, Any]:
        """Local stdio Supabase MCP server using a personal access token.

        Uses the official @supabase/mcp-server-supabase package. The extra
        -p @modelcontextprotocol/sdk works around a bundling issue in some
        versions of the package.
        """
        args = [
            "-y",
            "-p", "@modelcontextprotocol/sdk",
            "-p", "@supabase/mcp-server-supabase@latest",
            "mcp-server-supabase",
        ]
        if project_ref:
            args.extend(["--project-ref", project_ref])
        if read_only:
            args.append("--read-only")

        return {
            "command": "npx",
            "args": args,
            "env": {
                "SUPABASE_ACCESS_TOKEN": access_token,
            },
        }

    @classmethod
    def get_tools(cls) -> list[dict[str, str]]:
        """List of available tools (for display)."""
        return [
            {"name": "supabase_query", "desc": "Execute SQL query"},
            {"name": "supabase_schema", "desc": "Read database schema"},
            {"name": "supabase_auth_users", "desc": "List auth users"},
            {"name": "supabase_storage_list", "desc": "List storage buckets"},
            {"name": "supabase_edge_functions", "desc": "List edge functions"},
            {"name": "supabase_realtime_subscribe", "desc": "Subscribe to realtime channel"},
        ]
