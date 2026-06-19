"""Perplexity MCP server configuration."""

from typing import Any


class PerplexityServer:
    """Perplexity AI MCP server — real-time web search with AI summaries."""

    name = "perplexity"
    display_name = "Perplexity"
    description = "Real-time web search with AI summaries and citations. Research, news, docs, comparisons."
    icon = "🔍"

    @classmethod
    def get_stdio_config(cls, api_key: str) -> dict[str, Any]:
        """STDIO config with Perplexity API key."""
        return {
            "command": "npx",
            "args": ["-y", "@perplexity-ai/mcp-server"],
            "env": {
                "PERPLEXITY_API_KEY": api_key,
            }
        }

    @classmethod
    def get_tools(cls) -> list[dict[str, str]]:
        return [
            {"name": "perplexity_search", "desc": "Web search with AI summary + citations"},
            {"name": "perplexity_ask", "desc": "Direct question with sourced answer"},
            {"name": "perplexity_related", "desc": "Related questions for deeper research"},
        ]
