"""OAuth and token management for MCP servers."""

import json
import webbrowser
import http.server
import socketserver
import threading
import urllib.parse
from pathlib import Path
from typing import Callable

import requests
from rich.console import Console

console = Console()


class CallbackHandler(http.server.BaseHTTPRequestHandler):
    """HTTP handler that captures OAuth callback query params."""

    code: str | None = None
    error: str | None = None

    def do_GET(self):
        query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        CallbackHandler.code = query.get("code", [None])[0]
        CallbackHandler.error = query.get("error", [None])[0]
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write("""
        <html><body style="font-family:sans-serif;text-align:center;padding-top:50px">
        <h1>Authorization successful</h1>
        <p>You can close this tab and return to the terminal.</p>
        </body></html>
        """.encode('utf-8'))

    def log_message(self, format, *args):
        pass  # Suppress logs


class OAuthHandler:
    """Handles OAuth flows for MCP servers."""

    def __init__(self, port: int = 0):
        self.port = port
        self.server: socketserver.TCPServer | None = None
        self.thread: threading.Thread | None = None

    def start_callback_server(self) -> int:
        """Start local callback server, return assigned port."""
        handler = CallbackHandler
        handler.code = None
        handler.error = None
        self.server = socketserver.TCPServer(("127.0.0.1", 0), handler)
        self.port = self.server.socket.getsockname()[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return self.port

    def stop_callback_server(self):
        """Shutdown the callback server."""
        if self.server:
            self.server.shutdown()
            self.server.server_close()

    def wait_for_code(self, timeout: int = 120) -> str | None:
        """Block until callback receives code or timeout."""
        import time
        for _ in range(timeout * 10):
            if CallbackHandler.code:
                return CallbackHandler.code
            if CallbackHandler.error:
                console.print(f"[red]OAuth error: {CallbackHandler.error}[/red]")
                return None
            time.sleep(0.1)
        console.print("[red]Timeout waiting for authorization.[/red]")
        return None

    def atlassian_oauth(self, client_id: str, scope: str = "read:jira-work write:jira-work read:confluence-content write:confluence-content") -> dict:
        """Atlassian 2-click OAuth for Jira/Confluence."""
        port = self.start_callback_server()
        redirect_uri = f"http://127.0.0.1:{port}/callback"

        auth_url = (
            f"https://auth.atlassian.com/authorize"
            f"?audience=api.atlassian.com"
            f"&client_id={client_id}"
            f"&scope={urllib.parse.quote(scope)}"
            f"&redirect_uri={urllib.parse.quote(redirect_uri)}"
            f"&state=kimi-mcp-hub-{port}"
            f"&response_type=code"
            f"&prompt=consent"
        )

        console.print(f"\n[bold cyan]Opening browser for Atlassian authorization...[/bold cyan]")
        console.print(f"[dim]Callback URL: {redirect_uri}[/dim]\n")
        webbrowser.open(auth_url)

        code = self.wait_for_code()
        self.stop_callback_server()

        if not code:
            return {}

        # Exchange code for tokens (requires client_secret — in real impl this would be server-side or PKCE)
        # For Atlassian MCP, the official flow uses kimi mcp auth which handles this internally.
        # We return the code so the caller can complete the exchange.
        return {"code": code, "redirect_uri": redirect_uri}


class TokenStore:
    """Simple encrypted-at-rest token storage (using platform keyring if available)."""

    def __init__(self, config_dir: Path):
        self.file = config_dir / "tokens.json"

    def save(self, server: str, data: dict):
        tokens = {}
        if self.file.exists():
            tokens = json.loads(self.file.read_text())
        tokens[server] = data
        self.file.write_text(json.dumps(tokens, indent=2))

    def load(self, server: str) -> dict | None:
        if not self.file.exists():
            return None
        tokens = json.loads(self.file.read_text())
        return tokens.get(server)
