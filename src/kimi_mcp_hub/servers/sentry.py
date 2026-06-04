"""Sentry MCP server configuration."""

from typing import Any


class SentryServer:
    """Sentry MCP server — error tracking, issue triage, production debugging."""

    name = "sentry"
    display_name = "Sentry"
    description = "Read Sentry issues, group by frequency, pull stack traces, error context."
    icon = "🐞"

    @classmethod
    def get_stdio_config(cls, token: str, org: str) -> dict[str, Any]:
        return {
            "command": "npx",
            "args": ["-y", "@sentry/mcp-server"],
            "env": {
                "SENTRY_AUTH_TOKEN": token,
                "SENTRY_ORG": org,
            }
        }

    @classmethod
    def get_tools(cls) -> list[dict[str, str]]:
        return [
            {"name": "sentry_list_issues", "desc": "List recent issues"},
            {"name": "sentry_get_issue", "desc": "Get issue details with stack trace"},
            {"name": "sentry_group_by_frequency", "desc": "Group issues by event count"},
            {"name": "sentry_search_issues", "desc": "Search issues by tag/query"},
            {"name": "sentry_get_release", "desc": "Get release info and commits"},
            {"name": "sentry_create_issue", "desc": "Create manual issue"},
        ]
