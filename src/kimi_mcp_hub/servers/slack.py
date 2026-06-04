"""Slack MCP server configuration."""

from typing import Any


class SlackServer:
    """Slack MCP server — supports OAuth and stealth mode."""

    name = "slack"
    display_name = "Slack"
    description = "Read channels, threads, DMs, post messages, search history."
    icon = "💬"

    @classmethod
    def get_stdio_config(cls, token: str) -> dict[str, Any]:
        return {
            "command": "npx",
            "args": ["-y", "@korotovsky/slack-mcp-server"],
            "env": {
                "SLACK_TOKEN": token
            }
        }

    @classmethod
    def get_oauth_config(cls) -> dict[str, Any]:
        """Official Slack MCP with OAuth (for Claude.ai-style integration)."""
        return {
            "transport": "http",
            "url": "https://mcp.slack.com/mcp",
            "auth": "oauth"
        }

    @classmethod
    def get_tools(cls) -> list[dict[str, str]]:
        return [
            {"name": "slack_list_channels", "desc": "List channels"},
            {"name": "slack_get_channel_history", "desc": "Channel messages"},
            {"name": "slack_get_thread_replies", "desc": "Thread replies"},
            {"name": "slack_post_message", "desc": "Post message (enable env)"},
            {"name": "slack_search_messages", "desc": "Search messages"},
            {"name": "slack_get_unread_messages", "desc": "Unread messages"},
            {"name": "slack_get_dm_history", "desc": "DM history"},
        ]
