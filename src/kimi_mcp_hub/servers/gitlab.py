"""GitLab MCP server configuration."""

from typing import Any


class GitLabServer:
    """GitLab MCP server -- official remote (OAuth) or API-key stdio."""

    name = "gitlab"
    display_name = "GitLab"
    description = "Manage GitLab repos, issues, merge requests, CI/CD pipelines, and wikis."
    icon = "🦊"

    @classmethod
    def get_official_config(cls, instance_url: str = "https://gitlab.com") -> dict[str, Any]:
        """Official GitLab remote MCP server (OAuth 2.1 browser flow).

        Args:
            instance_url: GitLab instance URL (default: https://gitlab.com).
                          Use https://gitlab.example.com for self-managed.
        """
        base = instance_url.rstrip("/")
        return {
            "transport": "http",
            "url": f"{base}/api/v4/mcp",
            "auth": "oauth",
        }

    @classmethod
    def get_official_stdio_config(cls, instance_url: str = "https://gitlab.com") -> dict[str, Any]:
        """Official GitLab remote MCP wrapped with mcp-remote for stdio clients."""
        base = instance_url.rstrip("/")
        url = f"{base}/api/v4/mcp"
        return {
            "command": "npx",
            "args": ["-y", "mcp-remote", url],
            "url": url,
        }

    @classmethod
    def get_stdio_config(cls, token: str, instance_url: str = "https://gitlab.com") -> dict[str, Any]:
        """Community GitLab MCP server using a personal access token."""
        return {
            "command": "npx",
            "args": ["-y", "@yoda.digital/gitlab-mcp-server"],
            "env": {
                "GITLAB_PERSONAL_ACCESS_TOKEN": token,
                "GITLAB_API_URL": f"{instance_url.rstrip('/')}/api/v4",
            }
        }

    @classmethod
    def get_tools(cls) -> list[dict[str, str]]:
        return [
            {"name": "gitlab_list_projects", "desc": "List projects"},
            {"name": "gitlab_create_issue", "desc": "Create issue"},
            {"name": "gitlab_list_issues", "desc": "List issues"},
            {"name": "gitlab_create_merge_request", "desc": "Create merge request"},
            {"name": "gitlab_list_merge_requests", "desc": "List merge requests"},
            {"name": "gitlab_create_branch", "desc": "Create branch"},
            {"name": "gitlab_list_commits", "desc": "List commits"},
            {"name": "gitlab_get_pipeline", "desc": "Get CI/CD pipeline status"},
        ]
