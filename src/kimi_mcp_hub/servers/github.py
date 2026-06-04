"""GitHub MCP server configuration."""

from typing import Any


class GitHubServer:
    """GitHub MCP server — GitHub token based."""

    name = "github"
    display_name = "GitHub"
    description = "Read repos, create PRs, manage issues, search code."
    icon = "🐙"

    @classmethod
    def get_stdio_config(cls, token: str) -> dict[str, Any]:
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
            {"name": "github_search_repos", "desc": "Search repositories"},
            {"name": "github_create_issue", "desc": "Create issue"},
            {"name": "github_create_pull_request", "desc": "Create PR"},
            {"name": "github_list_commits", "desc": "List commits"},
            {"name": "github_read_file", "desc": "Read file contents"},
            {"name": "github_search_code", "desc": "Search code across repos"},
        ]
