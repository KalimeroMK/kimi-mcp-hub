"""Gmail MCP server configuration."""

from typing import Any


class GmailServer:
    """Gmail MCP server — multiple implementations available."""

    name = "gmail"
    display_name = "Gmail"
    description = "Read, search, send, draft emails. Multi-account support."
    icon = "📧"

    @classmethod
    def get_npx_config(cls) -> dict[str, Any]:
        """Simple npx install (auto-auth on first run)."""
        return {
            "command": "npx",
            "args": ["-y", "@shinzolabs/gmail-mcp"],
            "env": {}
        }

    @classmethod
    def get_chrome_config(cls) -> dict[str, Any]:
        """Chrome extension bridge — no API keys, uses browser session."""
        return {
            "command": "npx",
            "args": ["-y", "@cafferychen/gmail-mcp"],
            "env": {}
        }

    @classmethod
    def get_python_config(cls, creds_path: str, token_path: str) -> dict[str, Any]:
        """Python SDK version with explicit credentials."""
        return {
            "command": "uv",
            "args": [
                "--directory", "/path/to/gmail-mcp",
                "run", "gmail",
                "--creds-file-path", creds_path,
                "--token-path", token_path
            ],
            "env": {}
        }

    @classmethod
    def get_tools(cls) -> list[dict[str, str]]:
        return [
            {"name": "gmail_search_emails", "desc": "Search emails"},
            {"name": "gmail_get_emails", "desc": "Get email by ID"},
            {"name": "gmail_compose_email", "desc": "Create draft"},
            {"name": "gmail_send_email", "desc": "Send email"},
            {"name": "gmail_list_labels", "desc": "List labels"},
            {"name": "gmail_add_label", "desc": "Add label"},
            {"name": "gmail_mark_read", "desc": "Mark as read"},
            {"name": "gmail_query_emails", "desc": "Raw Gmail query"},
        ]
