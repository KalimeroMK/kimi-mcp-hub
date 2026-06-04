"""Context7 MCP server configuration."""

from typing import Any


class Context7Server:
    """Context7 MCP server — live, version-aware library documentation."""

    name = "context7"
    display_name = "Context7"
    description = "Live library docs lookup. Fetch correct docs for correct version on demand."
    icon = "📚"

    @classmethod
    def get_stdio_config(cls) -> dict[str, Any]:
        return {
            "command": "npx",
            "args": ["-y", "@upstash/context7-mcp"],
            "env": {}
        }

    @classmethod
    def get_tools(cls) -> list[dict[str, str]]:
        return [
            {"name": "context7_search", "desc": "Search library documentation"},
            {"name": "context7_get_doc", "desc": "Get specific doc page by URL"},
            {"name": "context7_resolve_api", "desc": "Resolve API signature for version"},
            {"name": "context7_list_libraries", "desc": "List supported libraries"},
        ]
