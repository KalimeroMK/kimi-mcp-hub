"""Figma MCP server configuration."""

from typing import Any


class FigmaServer:
    """Figma MCP server -- official remote (OAuth) or console (PAT)."""

    name = "figma"
    display_name = "Figma"
    description = "Read designs, extract tokens, create frames, generate components."
    icon = "🎨"

    # Official Figma remote MCP endpoint (OAuth 2.1)
    OFFICIAL_URL = "https://mcp.figma.com/mcp"

    @classmethod
    def get_official_config(cls) -> dict[str, Any]:
        """Official Figma remote MCP server (OAuth 2.1 browser flow)."""
        return {
            "transport": "http",
            "url": cls.OFFICIAL_URL,
            "auth": "oauth",
        }

    @classmethod
    def get_official_stdio_config(cls) -> dict[str, Any]:
        """Official Figma remote MCP wrapped with mcp-remote for stdio clients."""
        return {
            "command": "npx",
            "args": ["-y", "mcp-remote", cls.OFFICIAL_URL],
            "url": cls.OFFICIAL_URL,
        }

    @classmethod
    def get_console_config(cls, token: str) -> dict[str, Any]:
        """Figma Console MCP -- full read/write with Desktop Bridge (PAT)."""
        return {
            "command": "npx",
            "args": ["-y", "figma-console-mcp@latest"],
            "env": {
                "FIGMA_ACCESS_TOKEN": token,
                "ENABLE_MCP_APPS": "true"
            }
        }

    @classmethod
    def get_tools(cls) -> list[dict[str, str]]:
        return [
            {"name": "figma_get_file", "desc": "Read Figma file"},
            {"name": "figma_get_variables", "desc": "Get design tokens"},
            {"name": "figma_search_components", "desc": "Search components"},
            {"name": "figma_instantiate_component", "desc": "Create component instance"},
            {"name": "figma_create_frame", "desc": "Create frame"},
            {"name": "figma_set_fills", "desc": "Set color variable"},
            {"name": "figma_set_text", "desc": "Set text properties"},
            {"name": "figma_execute", "desc": "Raw Figma Plugin API"},
            {"name": "figma_get_status", "desc": "Check connection status"},
        ]
