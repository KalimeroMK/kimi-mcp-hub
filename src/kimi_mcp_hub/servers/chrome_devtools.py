"""Chrome DevTools MCP server configuration."""

from typing import Any


class ChromeDevToolsServer:
    """Chrome DevTools MCP server — performance, network, screenshots, console."""

    name = "chrome-devtools"
    display_name = "Chrome DevTools"
    description = "Performance insights, network analysis, screenshots, console logs, Puppeteer automation."
    icon = "🌐"

    @classmethod
    def get_stdio_config(cls, port: int = 9229) -> dict[str, Any]:
        """STDIO config — requires Node 22+ and Chrome."""
        return {
            "command": "npx",
            "args": ["-y", "chrome-devtools-mcp@latest", "--port", str(port)],
            "env": {}
        }

    @classmethod
    def get_tools(cls) -> list[dict[str, str]]:
        return [
            {"name": "devtools_performance", "desc": "Get performance trace / CrUX data"},
            {"name": "devtools_network", "desc": "Analyze network requests / intercept"},
            {"name": "devtools_screenshot", "desc": "Take full-page or element screenshot"},
            {"name": "devtools_console", "desc": "Get console logs with source maps"},
            {"name": "devtools_coverage", "desc": "CSS/JS coverage analysis"},
            {"name": "devtools_lighthouse", "desc": "Run Lighthouse audit"},
            {"name": "devtools_puppeteer_click", "desc": "Click element via Puppeteer"},
            {"name": "devtools_puppeteer_fill", "desc": "Fill form field via Puppeteer"},
            {"name": "devtools_puppeteer_navigate", "desc": "Navigate to URL via Puppeteer"},
            {"name": "devtools_puppeteer_evaluate", "desc": "Evaluate JS in page context"},
        ]
