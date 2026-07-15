"""OAuth and token management for MCP servers.

Supports:
- PKCE (Proof Key for Code Exchange) for secure OAuth
- Device Flow for CLI apps (GitHub, Google, etc.)
- Localhost callback with auto browser open
- Plain-JSON token storage (chmod 600 on Unix)
"""

import json
import webbrowser
import http.server
import socketserver
import threading
import urllib.parse
import urllib.request
import hashlib
import base64
import secrets
import time
from pathlib import Path

import requests
from rich.console import Console
from rich.progress import SpinnerColumn, Progress

console = Console()


def generate_pkce_pair() -> tuple[str, str]:
    """Generate PKCE code_verifier and code_challenge (S256).

    Returns:
        (code_verifier, code_challenge)
    """
    verifier = (
        base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii").rstrip("=")
    )
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
        .decode("ascii")
        .rstrip("=")
    )
    return verifier, challenge


class _CallbackServer(socketserver.TCPServer):
    """TCP server that stores the latest OAuth callback result."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.code: str | None = None
        self.state: str | None = None
        self.error: str | None = None
        self.error_description: str | None = None


class CallbackHandler(http.server.BaseHTTPRequestHandler):
    """HTTP handler that captures OAuth callback query params."""

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)

        server = self.server  # type: ignore[attr-defined]
        server.code = query.get("code", [None])[0]
        server.state = query.get("state", [None])[0]
        server.error = query.get("error", [None])[0]
        server.error_description = query.get("error_description", [None])[0]

        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()

        if server.code:
            html = """
            <!DOCTYPE html>
            <html>
            <head><title>Kimi MCP Hub - Authorized</title>
            <style>
                body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                       text-align: center; padding-top: 80px; background: #0d1117; color: #c9d1d9; }
                .box { max-width: 500px; margin: 0 auto; padding: 40px; border-radius: 12px;
                       background: #161b22; border: 1px solid #30363d; }
                h1 { color: #3fb950; font-size: 28px; margin-bottom: 10px; }
                p { color: #8b949e; font-size: 16px; line-height: 1.5; }
                .check { font-size: 64px; margin-bottom: 10px; }
                code { background: #21262d; padding: 2px 8px; border-radius: 4px; font-size: 14px; }
            </style></head>
            <body>
                <div class="box">
                    <div class="check">&#x2705;</div>
                    <h1>Authorization Successful!</h1>
                    <p>You can close this tab and return to the terminal.</p>
                    <p><code>Kimi MCP Hub</code> is now connected.</p>
                </div>
            </body></html>
            """
        else:
            html = f"""
            <!DOCTYPE html>
            <html>
            <head><title>Kimi MCP Hub - Error</title>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                       text-align: center; padding-top: 80px; background: #0d1117; color: #c9d1d9; }}
                .box {{ max-width: 500px; margin: 0 auto; padding: 40px; border-radius: 12px;
                       background: #161b22; border: 1px solid #30363d; }}
                h1 {{ color: #f85149; font-size: 28px; margin-bottom: 10px; }}
                p {{ color: #8b949e; font-size: 16px; }}
            </style></head>
            <body>
                <div class="box">
                    <div style="font-size: 64px; margin-bottom: 10px;">&#x274C;</div>
                    <h1>Authorization Failed</h1>
                    <p>{server.error or "Unknown error"}</p>
                    <p>{server.error_description or ""}</p>
                </div>
            </body></html>
            """

        self.wfile.write(html.encode("utf-8"))

    def log_message(self, format, *args):
        pass  # Suppress logs


class LocalCallbackServer:
    """Local HTTP server that captures OAuth callback."""

    def __init__(self):
        self.server: _CallbackServer | None = None
        self.thread: threading.Thread | None = None
        self.port: int = 0

    def start(self) -> int:
        """Start server on random port, return the port number."""
        self.server = _CallbackServer(("127.0.0.1", 0), CallbackHandler)
        self.port = self.server.socket.getsockname()[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return self.port

    def stop(self):
        """Shutdown the server."""
        if self.server:
            self.server.shutdown()
            self.server.server_close()

    def wait_for_code(self, timeout: int = 120) -> str | None:
        """Block until callback receives code or timeout."""
        if self.server is None:
            return None

        with Progress(
            SpinnerColumn(),
            *Progress.get_default_columns(),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task(
                "[cyan]Waiting for browser authorization...", total=timeout * 10
            )
            for _ in range(timeout * 10):
                if self.server.code:
                    progress.update(task, completed=timeout * 10)
                    return self.server.code
                if self.server.error:
                    console.print(f"[red]OAuth error: {self.server.error}[/red]")
                    if self.server.error_description:
                        console.print(f"[red]{self.server.error_description}[/red]")
                    return None
                time.sleep(0.1)
                progress.advance(task)

        console.print("[red]Timeout waiting for authorization.[/red]")
        return None


class DeviceFlowHandler:
    """Handles OAuth 2.0 Device Flow for CLI applications.

    Used by: GitHub, Google, and other providers that support device flow.
    """

    def __init__(
        self,
        device_endpoint: str,
        token_endpoint: str,
        client_id: str,
        scopes: list[str] | None = None,
    ):
        self.device_endpoint = device_endpoint
        self.token_endpoint = token_endpoint
        self.client_id = client_id
        self.scopes = scopes or []

    def start(self) -> dict:
        """Start device flow, return device code info.

        Returns dict with: device_code, user_code, verification_uri, expires_in, interval
        """
        data = {
            "client_id": self.client_id,
            "scope": " ".join(self.scopes),
        }
        resp = requests.post(
            self.device_endpoint,
            data=data,
            headers={"Accept": "application/json"},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def poll_for_token(
        self, device_code: str, interval: int = 5, expires_in: int = 600
    ) -> dict | None:
        """Poll token endpoint until user authorizes or timeout.

        Returns token dict with access_token, or None on failure.
        """
        data = {
            "client_id": self.client_id,
            "device_code": device_code,
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        }

        max_attempts = expires_in // interval

        with Progress(
            SpinnerColumn(),
            *Progress.get_default_columns(),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task(
                "[cyan]Waiting for you to authorize in browser...", total=max_attempts
            )

            for attempt in range(max_attempts):
                time.sleep(interval)
                progress.advance(task)

                resp = requests.post(self.token_endpoint, data=data, timeout=30)
                result = resp.json()

                if "access_token" in result:
                    progress.update(task, completed=max_attempts)
                    return result

                error = result.get("error", "")
                if error == "authorization_pending":
                    continue  # Still waiting
                elif error == "slow_down":
                    interval += 5  # Server asks us to slow down
                elif error == "expired_token":
                    console.print("[red]Device code expired. Please try again.[/red]")
                    return None
                elif error == "access_denied":
                    console.print("[red]Access denied by user.[/red]")
                    return None
                else:
                    console.print(f"[red]OAuth error: {error}[/red]")
                    if "error_description" in result:
                        console.print(f"[red]{result['error_description']}[/red]")
                    return None

        console.print("[red]Authorization timed out.[/red]")
        return None


class WebFlowHandler:
    """Handles OAuth 2.0 Web Flow with localhost callback + PKCE.

    Used by: Jira, Confluence, Slack, Figma, and other providers.
    """

    def __init__(
        self,
        auth_url: str,
        token_url: str,
        client_id: str,
        client_secret: str | None = None,
        scopes: list[str] | None = None,
    ):
        self.auth_url = auth_url
        self.token_url = token_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.scopes = scopes or []

    def authorize(self, timeout: int = 120) -> dict | None:
        """Full web flow: open browser, wait for callback, exchange code for token.

        Returns token dict or None.
        """
        # Generate PKCE
        code_verifier, code_challenge = generate_pkce_pair()

        # Start local callback server
        callback = LocalCallbackServer()
        port = callback.start()
        redirect_uri = f"http://127.0.0.1:{port}/callback"

        # Build auth URL with PKCE
        state = secrets.token_urlsafe(16)
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.scopes),
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        auth_url = f"{self.auth_url}?{urllib.parse.urlencode(params)}"

        # Open browser
        console.print("\n[bold cyan]Opening browser for authorization...[/bold cyan]")
        console.print("[dim]If browser doesn't open, use this URL:[/dim]")
        console.print(f"[blue underline]{auth_url}[/blue underline]\n")

        opened = webbrowser.open(auth_url, new=2, autoraise=True)
        if not opened:
            console.print("[yellow]Could not open browser automatically.[/yellow]")
            console.print("[yellow]Please open the URL above manually.[/yellow]\n")

        # Wait for callback
        code = callback.wait_for_code(timeout=timeout)
        callback.stop()

        if not code:
            return None

        # Validate state to protect against CSRF on the redirect
        if callback.server is None or callback.server.state != state:
            console.print("[red]OAuth state mismatch. Authorization aborted.[/red]")
            return None

        # Exchange code for token
        return self.exchange_code(code, redirect_uri, code_verifier)

    def exchange_code(
        self, code: str, redirect_uri: str, code_verifier: str
    ) -> dict | None:
        """Exchange authorization code for access token."""
        data = {
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "code": code,
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier,
        }
        if self.client_secret:
            data["client_secret"] = self.client_secret

        try:
            resp = requests.post(self.token_url, data=data, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            console.print(f"[red]Token exchange failed: {e}[/red]")
            return None


class TokenStore:
    """Plain-JSON token storage in the hub config directory.

    Files are chmod 600 on Unix (enforced by ``kimi-mcp-hub doctor``), but
    tokens are not encrypted at rest.
    """

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
