"""Confluence MCP server configuration."""

from typing import Any


class ConfluenceServer:
    """Atlassian Confluence MCP server."""

    name = "confluence"
    display_name = "Confluence"
    description = "Search, read, and create Confluence pages."
    icon = "📄"

    OAUTH_URL = "https://mcp.atlassian.com/v1/mcp/authv2"

    @classmethod
    def get_oauth_config(cls) -> dict[str, Any]:
        return {
            "transport": "http",
            "url": cls.OAUTH_URL,
            "auth": "oauth"
        }

    @classmethod
    def get_stdio_config(cls, base_url: str, api_token: str, email: str) -> dict[str, Any]:
        return {
            "command": "npx",
            "args": ["-y", "confluence-mcp"],
            "env": {
                "CONFLUENCE_BASE_URL": base_url,
                "CONFLUENCE_API_TOKEN": api_token,
                "CONFLUENCE_USER_EMAIL": email
            }
        }

    @classmethod
    def get_tools(cls) -> list[dict[str, str]]:
        return [
            {"name": "confluence_search", "desc": "Search pages by CQL"},
            {"name": "confluence_get_page", "desc": "Read page content"},
            {"name": "confluence_create_page", "desc": "Create new page"},
            {"name": "confluence_update_page", "desc": "Update existing page"},
            {"name": "confluence_list_spaces", "desc": "List spaces"},
        ]
