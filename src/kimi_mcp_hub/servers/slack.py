"""Slack MCP server configuration."""

from typing import Any


class SlackServer:
    """Slack MCP server — community slack-mcp-server package."""

    name = "slack"
    display_name = "Slack"
    description = "Read channels, threads, DMs, post messages, search history."
    icon = "💬"

    @classmethod
    def get_stdio_config(cls, token: str, token_type: str = "bot") -> dict[str, Any]:
        """Community slack-mcp-server using a bot or user token.

        npm package: slack-mcp-server (from korotovsky/slack-mcp-server)
        """
        env_var = "SLACK_MCP_XOXB_TOKEN" if token_type == "bot" else "SLACK_MCP_XOXP_TOKEN"
        return {
            "command": "npx",
            "args": ["-y", "slack-mcp-server@latest"],
            "env": {
                env_var: token,
            },
        }

    @classmethod
    def get_tools(cls) -> list[dict[str, str]]:
        """List of available tools (for display)."""
        return [
            {"name": "conversations_history", "desc": "Get messages from a channel/DM"},
            {"name": "conversations_replies", "desc": "Thread replies"},
            {"name": "conversations_search_messages", "desc": "Search messages"},
            {"name": "channels_list", "desc": "List channels"},
            {"name": "users_search", "desc": "Search users"},
        ]
