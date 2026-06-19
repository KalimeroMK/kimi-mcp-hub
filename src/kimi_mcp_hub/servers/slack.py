"""Slack MCP server configuration."""

from typing import Any


class SlackServer:
    """Slack MCP server — official Anthropic stdio server or remote OAuth."""

    name = "slack"
    display_name = "Slack"
    description = "Read channels, threads, DMs, post messages, search history."
    icon = "💬"

    OFFICIAL_REMOTE_URL = "https://mcp.slack.com/mcp"

    @classmethod
    def get_stdio_config(cls, bot_token: str, team_id: str) -> dict[str, Any]:
        """Official Anthropic Slack MCP server using a bot token.

        This is the most reliable option for Kimi CLI / Cursor / Windsurf.
        """
        return {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-slack"],
            "env": {
                "SLACK_BOT_TOKEN": bot_token,
                "SLACK_TEAM_ID": team_id,
            }
        }

    @classmethod
    def get_official_config(cls) -> dict[str, Any]:
        """Official Slack remote MCP server (OAuth 2.1).

        Note: this can fail in some clients because Slack's OAuth server does
        not support Dynamic Client Registration (DCR). Prefer the stdio bot
        token option unless your client explicitly supports Slack remote MCP.
        """
        return {
            "transport": "http",
            "url": cls.OFFICIAL_REMOTE_URL,
            "auth": "oauth",
        }

    @classmethod
    def get_tools(cls) -> list[dict[str, str]]:
        """List of available tools (for display)."""
        return [
            {"name": "slack_list_channels", "desc": "List channels"},
            {"name": "slack_get_channel_history", "desc": "Channel messages"},
            {"name": "slack_get_thread_replies", "desc": "Thread replies"},
            {"name": "slack_post_message", "desc": "Post message"},
            {"name": "slack_search_messages", "desc": "Search messages"},
            {"name": "slack_get_unread_messages", "desc": "Unread messages"},
            {"name": "slack_get_dm_history", "desc": "DM history"},
        ]
