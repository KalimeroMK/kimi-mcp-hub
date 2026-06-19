"""Figma Context MCP server configuration (Cursor-style design-to-code)."""

from typing import Any


class FigmaContextServer:
    """Figma Context MCP -- optimized for implementing Figma designs in code."""

    name = "figma-context"
    display_name = "Figma Context"
    description = "Translate Figma designs into code with structured layout/styling context."
    icon = "🎨"

    @classmethod
    def get_stdio_config(cls, api_key: str) -> dict[str, Any]:
        """Local stdio server using a Figma API access token."""
        return {
            "command": "npx",
            "args": ["-y", "figma-developer-mcp", f"--figma-api-key={api_key}", "--stdio"],
            "env": {"FIGMA_API_KEY": api_key},
        }

    @classmethod
    def get_tools(cls) -> list[dict[str, str]]:
        return [
            {"name": "figma_get_file", "desc": "Get Figma file metadata and nodes"},
            {"name": "figma_get_node", "desc": "Get details for a specific node"},
            {"name": "figma_resolve_link", "desc": "Resolve a Figma link to file/node IDs"},
        ]
