"""GitHub MCP server configuration."""

from typing import Any


class GitHubServer:
    """GitHub MCP server -- official remote (OAuth/PAT) or token-based stdio."""

    name = "github"
    display_name = "GitHub"
    description = "Read repos, create PRs, manage issues, search code."
    icon = "🐙"

    @classmethod
    def get_official_config(cls) -> dict[str, Any]:
        """Official GitHub remote MCP server (OAuth 2.1 browser flow).

        After adding, complete authorization from Kimi CLI with
        ``kimi mcp auth github``.
        """
        return {
            "transport": "http",
            "url": "https://api.githubcopilot.com/mcp/",
            "auth": "oauth",
        }

    @classmethod
    def get_stdio_config(cls, token: str) -> dict[str, Any]:
        """Legacy community stdio server using a personal access token."""
        return {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-github"],
            "env": {
                "GITHUB_PERSONAL_ACCESS_TOKEN": token
            }
        }

    @classmethod
    def get_tools(cls) -> list[dict[str, str]]:
        return [
            {"name": "search_repositories", "desc": "Search repositories"},
            {"name": "create_issue", "desc": "Create issue"},
            {"name": "create_pull_request", "desc": "Create PR"},
            {"name": "list_commits", "desc": "List commits"},
            {"name": "get_file_contents", "desc": "Read file contents"},
            {"name": "search_code", "desc": "Search code across repos"},
        ]
