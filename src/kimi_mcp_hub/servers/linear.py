"""Linear MCP server configuration."""

from typing import Any


class LinearServer:
    """Linear MCP server -- supports API-key stdio or official remote OAuth server."""

    name = "linear"
    display_name = "Linear"
    description = "Manage Linear issues, projects, and teams."
    icon = "⚡"

    # Official Linear remote MCP endpoint (OAuth 2.1, browser popup)
    OFFICIAL_URL = "https://mcp.linear.app/mcp"

    @classmethod
    def get_stdio_config(cls, api_key: str) -> dict[str, Any]:
        """Local stdio server using a personal API key."""
        return {
            "command": "npx",
            "args": ["-y", "@emmett.deen/linear-mcp-server"],
            "env": {
                "LINEAR_API_KEY": api_key
            }
        }

    @classmethod
    def get_official_config(cls) -> dict[str, Any]:
        """Official remote Linear MCP server (OAuth 2.1).

        The MCP client (e.g. Kimi CLI or Claude) must initiate the OAuth
        browser flow. If the client does not support remote OAuth directly,
        ``mcp-remote`` can proxy the connection.
        """
        return {
            "transport": "http",
            "url": cls.OFFICIAL_URL,
            "auth": "oauth",
        }

    @classmethod
    def get_official_stdio_config(cls) -> dict[str, Any]:
        """Official remote Linear MCP server wrapped with mcp-remote for stdio clients."""
        return {
            "command": "npx",
            "args": ["-y", "mcp-remote", cls.OFFICIAL_URL],
            "url": cls.OFFICIAL_URL,
        }

    @classmethod
    def get_tools(cls) -> list[dict[str, str]]:
        return [
            {"name": "linear_list_issues", "desc": "List issues with filters"},
            {"name": "linear_create_issue", "desc": "Create new issue"},
            {"name": "linear_update_issue", "desc": "Update status/priority"},
            {"name": "linear_add_comment", "desc": "Add comment"},
            {"name": "linear_list_projects", "desc": "List projects"},
            {"name": "linear_list_teams", "desc": "List teams"},
        ]
