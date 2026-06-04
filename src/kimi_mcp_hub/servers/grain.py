"""Grain MCP server configuration."""

from typing import Any


class GrainServer:
    """Grain MCP server — meeting recordings and transcripts."""

    name = "grain"
    display_name = "Grain"
    description = "Access meeting recordings, transcripts, summaries."
    icon = "🎙️"

    @classmethod
    def get_uv_config(cls, user_data_dir: str) -> dict[str, Any]:
        """Uses Playwright browser automation — login via browser on first use."""
        return {
            "command": "uvx",
            "args": [
                "--from", "git+https://github.com/eadm/grain-mcp-server",
                "grain-mcp-server",
                "--user-data-dir", user_data_dir
            ],
            "env": {}
        }

    @classmethod
    def get_tools(cls) -> list[dict[str, str]]:
        return [
            {"name": "grain_get_all_meetings", "desc": "List all meetings"},
            {"name": "grain_download_transcript", "desc": "Download transcript (VTT/SRT)"},
        ]
