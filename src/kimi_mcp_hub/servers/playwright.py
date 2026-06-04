"""Playwright MCP server configuration."""

from typing import Any


class PlaywrightServer:
    """Playwright MCP server — browser automation, E2E testing from Microsoft."""

    name = "playwright"
    display_name = "Playwright"
    description = "Drive real browser: navigate, click, fill forms, screenshot, assert UI. E2E testing."
    icon = "🎭"

    @classmethod
    def get_stdio_config(cls) -> dict[str, Any]:
        """STDIO config — requires Node.js."""
        return {
            "command": "npx",
            "args": ["-y", "@executeautomation/playwright-mcp-server"],
            "env": {}
        }

    @classmethod
    def get_tools(cls) -> list[dict[str, str]]:
        return [
            {"name": "playwright_navigate", "desc": "Navigate to URL"},
            {"name": "playwright_click", "desc": "Click element"},
            {"name": "playwright_fill", "desc": "Fill form field"},
            {"name": "playwright_select", "desc": "Select dropdown option"},
            {"name": "playwright_screenshot", "desc": "Take screenshot (full page or element)"},
            {"name": "playwright_evaluate", "desc": "Execute JS in browser context"},
            {"name": "playwright_assert", "desc": "Assert element visible/text"},
            {"name": "playwright_e2e", "desc": "Run multi-step E2E scenario"},
        ]
