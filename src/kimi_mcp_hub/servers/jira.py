"""Jira MCP server configuration."""

from typing import Any


class JiraServer:
    """Atlassian Jira MCP server — supports both Cloud (OAuth) and Data Center (API token)."""

    name = "jira"
    display_name = "Jira"
    description = "Create, search, and transition Jira issues. Supports JQL, sprints, and worklogs."
    icon = "🎯"

    # OAuth endpoint for Atlassian Cloud (simplest 2-click auth)
    OAUTH_URL = "https://mcp.atlassian.com/v1/mcp/authv2"

    @classmethod
    def get_oauth_config(cls) -> dict[str, Any]:
        """Return HTTP-based OAuth config for Atlassian Cloud."""
        return {
            "transport": "http",
            "url": cls.OAUTH_URL,
            "auth": "oauth"
        }

    @classmethod
    def get_stdio_config(cls, base_url: str, api_token: str, email: str) -> dict[str, Any]:
        """Return STDIO config for Jira Data Center or Cloud with API token."""
        return {
            "command": "npx",
            "args": ["-y", "jira-mcp"],
            "env": {
                "JIRA_BASE_URL": base_url,
                "JIRA_API_TOKEN": api_token,
                "JIRA_USER_EMAIL": email,
                "JIRA_TYPE": "cloud"
            }
        }

    @classmethod
    def get_tools(cls) -> list[dict[str, str]]:
        """List of available tools (for display)."""
        return [
            {"name": "jira_get_issue", "desc": "Get issue details by key"},
            {"name": "jira_create_issue", "desc": "Create bug, task, story"},
            {"name": "jira_search_issue", "desc": "JQL search"},
            {"name": "jira_transition_issue", "desc": "Move to Done/In Progress"},
            {"name": "jira_add_comment", "desc": "Add comment to issue"},
            {"name": "jira_list_sprints", "desc": "List active sprints"},
            {"name": "jira_add_worklog", "desc": "Log time spent"},
            {"name": "jira_get_development_information", "desc": "See linked PRs/commits"},
        ]
