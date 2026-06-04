"""Linear MCP server configuration."""

from typing import Any


class LinearServer:
    """Linear MCP server — API key based."""

    name = "linear"
    display_name = "Linear"
    description = "Manage Linear issues, projects, and teams."
    icon = "⚡"

    @classmethod
    def get_stdio_config(cls, api_key: str) -> dict[str, Any]:
        return {
            "command": "npx",
            "args": ["-y", "@emmett.deen/linear-mcp-server"],
            "env": {
                "LINEAR_API_KEY": api_key
            }
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
