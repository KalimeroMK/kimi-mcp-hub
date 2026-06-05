"""OAuth provider configurations for MCP servers.

Each provider defines how to authenticate with a specific service.
Supports both Device Flow (for CLI) and Web Flow (with browser redirect).
"""

from __future__ import annotations

import secrets
import urllib.parse
from dataclasses import dataclass, field
from typing import Callable

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

from .oauth import DeviceFlowHandler, WebFlowHandler, TokenStore

console = Console()


@dataclass
class OAuthProvider:
    """Base configuration for an OAuth provider."""

    name: str
    display_name: str
    icon: str = ""

    # Device Flow endpoints (if supported)
    device_auth_url: str | None = None
    device_token_url: str | None = None

    # Web Flow endpoints
    auth_url: str | None = None
    token_url: str | None = None

    # Client credentials
    client_id: str | None = None
    client_secret: str | None = None

    # Scopes
    scopes: list[str] = field(default_factory=list)

    # Default flow preference
    default_flow: str = "web"  # "web" or "device"

    def is_configured(self) -> bool:
        """Check if provider has required credentials."""
        return self.client_id is not None

    def get_token_store(self) -> TokenStore:
        """Get token store for this provider."""
        from pathlib import Path
        import platformdirs
        config_dir = Path(platformdirs.user_config_dir("kimi-mcp-hub", "MoonshotAI"))
        config_dir.mkdir(parents=True, exist_ok=True)
        return TokenStore(config_dir)


# ---------------------------------------------------------------------------
# GitHub
# ---------------------------------------------------------------------------

GITHUB_PROVIDER = OAuthProvider(
    name="github",
    display_name="GitHub",
    icon="",
    # GitHub Device Flow
    device_auth_url="https://github.com/login/device/code",
    device_token_url="https://github.com/login/oauth/access_token",
    # GitHub Web Flow (fallback)
    auth_url="https://github.com/login/oauth/authorize",
    token_url="https://github.com/login/oauth/access_token",
    # GitHub OAuth App (public -- 'kimi-mcp-hub' CLI app)
    # Note: Users can override with their own OAuth app
    client_id="Ov23liVm8rM1y7Y0HUP5",  # kimi-mcp-hub public OAuth App
    scopes=["repo", "read:org", "read:user", "user:email", "workflow"],
    default_flow="device",
)


def authenticate_github(pat_fallback: bool = True) -> dict | None:
    """Authenticate with GitHub using Device Flow (preferred) or PAT fallback.

    Returns token dict with access_token, or None on failure.
    """
    provider = GITHUB_PROVIDER
    store = provider.get_token_store()

    # Check if already have token
    existing = store.load("github")
    if existing and existing.get("access_token"):
        if not Confirm.ask("GitHub already authorized. Re-authorize?", default=False):
            return existing

    console.print(Panel.fit(
        f"[bold]{provider.display_name} Authorization[/bold]\n"
        f"[dim]Device Flow -- secure, no copy-paste needed[/dim]",
        border_style="cyan",
    ))

    # Option 1: Device Flow (recommended)
    use_device = Confirm.ask("Use Device Flow (auto browser open)?", default=True)

    if use_device:
        return _github_device_flow()

    # Option 2: PAT
    if pat_fallback:
        console.print("\n[yellow]Falling back to Personal Access Token (PAT)[/yellow]")
        console.print("Create at: https://github.com/settings/tokens")
        token = Prompt.ask("GitHub PAT", password=True)
        if token:
            token_data = {"access_token": token, "token_type": "bearer", "scope": "repo"}
            store.save("github", token_data)
            console.print("[green]GitHub PAT saved![/green]")
            return token_data

    return None


def _github_device_flow() -> dict | None:
    """GitHub Device Flow with auto browser open."""
    provider = GITHUB_PROVIDER
    store = provider.get_token_store()

    handler = DeviceFlowHandler(
        device_endpoint=provider.device_auth_url,
        token_endpoint=provider.device_token_url,
        client_id=provider.client_id,
        scopes=provider.scopes,
    )

    # Step 1: Request device code
    try:
        import requests
        resp = requests.post(
            provider.device_auth_url,
            data={"client_id": provider.client_id, "scope": " ".join(provider.scopes)},
            headers={"Accept": "application/json"},
            timeout=30,
        )
        resp.raise_for_status()
        device_info = resp.json()
    except Exception as e:
        console.print(f"[red]Failed to start device flow: {e}[/red]")
        return None

    user_code = device_info.get("user_code", "")
    verification_uri = device_info.get("verification_uri", "https://github.com/login/device")
    device_code = device_info.get("device_code", "")
    interval = device_info.get("interval", 5)
    expires_in = device_info.get("expires_in", 600)

    # Step 2: Auto-open browser + show code
    console.print(f"\n[bold]Your verification code:[/bold] [yellow]{user_code}[/yellow]")
    console.print(f"[dim]Opening browser...[/dim]\n")

    import webbrowser
    webbrowser.open(verification_uri, new=2, autoraise=True)

    console.print(Panel.fit(
        f"[bold]If browser didn't open:[/bold]\n"
        f"1. Go to: [blue]{verification_uri}[/blue]\n"
        f"2. Enter code: [yellow]{user_code}[/yellow]\n"
        f"3. Click 'Authorize'",
        border_style="yellow",
    ))

    # Step 3: Poll for token
    token_data = handler.poll_for_token(device_code, interval=interval, expires_in=expires_in)

    if token_data and "access_token" in token_data:
        # GitHub returns x-www-form-urlencoded, handle both formats
        if isinstance(token_data, str):
            token_data = dict(urllib.parse.parse_qsl(token_data))

        store.save("github", token_data)
        console.print(f"\n[bold green]{provider.display_name} authorized successfully![/bold green]")
        return token_data

    return None


# ---------------------------------------------------------------------------
# Atlassian (Jira / Confluence)
# ---------------------------------------------------------------------------

ATLASSIAN_PROVIDER = OAuthProvider(
    name="atlassian",
    display_name="Atlassian",
    icon="",
    auth_url="https://auth.atlassian.com/authorize",
    token_url="https://auth.atlassian.com/oauth/token",
    # Public OAuth app for kimi-mcp-hub
    client_id="kimi-mcp-hub-atlassian",
    scopes=["read:jira-work", "write:jira-work", "read:confluence-content", "write:confluence-content"],
    default_flow="web",
)


def authenticate_atlassian(service: str = "jira") -> dict | None:
    """Authenticate with Atlassian for Jira or Confluence."""
    provider = ATLASSIAN_PROVIDER
    store = provider.get_token_store()

    console.print(Panel.fit(
        f"[bold]Atlassian {service.title()} Authorization[/bold]\n"
        f"[dim]PKCE Web Flow with auto browser open[/dim]",
        border_style="cyan",
    ))

    # Atlassian requires registering your own OAuth app
    # For now, guide the user through the official Kimi MCP flow
    console.print("\n[bold]Atlassian OAuth Setup[/bold]\n")
    console.print("Atlassian requires an OAuth app. You have two options:\n")
    console.print("[bold]1. Official MCP Server (Recommended):[/bold]")
    console.print("   [bold]kimi mcp add --transport http --auth oauth jira[/bold]")
    console.print("   [bold]https://mcp.atlassian.com/v1/mcp/authv2[/bold]")
    console.print("   Then: [bold]kimi mcp auth jira[/bold]\n")

    console.print("[bold]2. API Token (Simpler):[/bold]")
    console.print("   Get token at: https://id.atlassian.com/manage-profile/security/api-tokens")

    choice = Prompt.ask("Option", choices=["mcp", "api-token"], default="api-token")

    if choice == "api-token":
        from ..servers.jira import JiraServer
        from ..servers.confluence import ConfluenceServer
        from ..config import KimiConfig

        base_url = Prompt.ask("Base URL", default="https://yourcompany.atlassian.net")
        email = Prompt.ask("Email")
        token = Prompt.ask("API token", password=True)

        config = KimiConfig()
        if service == "jira":
            cfg = JiraServer.get_stdio_config(base_url, token, email)
            config.add_server("jira", cfg)
        else:
            cfg = ConfluenceServer.get_stdio_config(base_url, token, email)
            config.add_server("confluence", cfg)

        console.print(f"[green]{service.title()} configured with API token![/green]")
        return {"token": token, "email": email, "base_url": base_url}

    return {"flow": "mcp_official"}


# ---------------------------------------------------------------------------
# Google (Gmail)
# ---------------------------------------------------------------------------

def authenticate_google() -> dict | None:
    """Authenticate with Google for Gmail access.

    Google requires OAuth 2.0 with either:
    1. Desktop app credentials (client_id + client_secret)
    2. Service account
    """
    console.print(Panel.fit(
        "[bold]Google Gmail Authorization[/bold]\n"
        "[dim]OAuth 2.0 for Gmail access[/dim]",
        border_style="cyan",
    ))

    console.print("\n[bold]Google OAuth Setup[/bold]\n")
    console.print("Google requires a project in Google Cloud Console:\n")
    console.print("1. Go to: [blue]https://console.cloud.google.com/apis/credentials[/blue]")
    console.print("2. Create OAuth 2.0 credentials (Desktop app)")
    console.print("3. Enable Gmail API\n")

    client_id = Prompt.ask("OAuth Client ID (leave empty for npx mode)", default="")

    if not client_id:
        console.print("\n[yellow]Using npx mode (no OAuth needed)[/yellow]")
        from ..servers.gmail import GmailServer
        from ..config import KimiConfig
        config = KimiConfig()
        cfg = GmailServer.get_npx_config()
        config.add_server("gmail", cfg)
        console.print("[green]Gmail configured (npx mode)![/green]")
        return {"mode": "npx"}

    client_secret = Prompt.ask("OAuth Client Secret", password=True)

    # Use Web Flow with PKCE
    handler = WebFlowHandler(
        auth_url="https://accounts.google.com/o/oauth2/v2/auth",
        token_url="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=["https://www.googleapis.com/auth/gmail.modify"],
    )

    token_data = handler.authorize(timeout=120)

    if token_data and "access_token" in token_data:
        store = TokenStore(__get_config_dir())
        store.save("gmail", token_data)
        console.print("[bold green]Gmail authorized successfully![/bold green]")
        return token_data

    return None


# ---------------------------------------------------------------------------
# Slack
# ---------------------------------------------------------------------------

def authenticate_slack() -> dict | None:
    """Authenticate with Slack."""
    console.print(Panel.fit(
        "[bold]Slack Authorization[/bold]\n"
        "[dim]OAuth 2.0 with auto browser[/dim]",
        border_style="cyan",
    ))

    console.print("\n[bold]Slack OAuth Setup[/bold]\n")
    console.print("Create a Slack app at: [blue]https://api.slack.com/apps[/blue]\n")

    choice = Prompt.ask("Method", choices=["oauth", "bot-token"], default="bot-token")

    if choice == "bot-token":
        console.print("\nGet Bot Token from: https://api.slack.com/apps -> Your App -> OAuth & Permissions")
        token = Prompt.ask("Bot User OAuth Token (xoxb-...)", password=True)
        if token:
            from ..servers.slack import SlackServer
            from ..config import KimiConfig
            config = KimiConfig()
            cfg = SlackServer.get_stdio_config(token)
            config.add_server("slack", cfg)
            console.print("[green]Slack configured![/green]")
            return {"token": token}
    else:
        # Web Flow
        client_id = Prompt.ask("Slack Client ID")
        client_secret = Prompt.ask("Slack Client Secret", password=True)

        handler = WebFlowHandler(
            auth_url="https://slack.com/oauth/v2/authorize",
            token_url="https://slack.com/api/oauth.v2.access",
            client_id=client_id,
            client_secret=client_secret,
            scopes=["chat:write", "channels:read", "groups:read", "im:read", "mpim:read", "search:read", "users:read"],
        )

        token_data = handler.authorize(timeout=120)
        if token_data:
            store = TokenStore(__get_config_dir())
            store.save("slack", token_data)
            console.print("[bold green]Slack authorized![/bold green]")
            return token_data

    return None


# ---------------------------------------------------------------------------
# Figma
# ---------------------------------------------------------------------------

def authenticate_figma() -> dict | None:
    """Authenticate with Figma."""
    console.print(Panel.fit(
        "[bold]Figma Authorization[/bold]\n"
        "[dim]OAuth 2.0 with auto browser[/dim]",
        border_style="cyan",
    ))

    console.print("\n[bold]Figma OAuth Setup[/bold]\n")
    console.print("Options:\n")
    console.print("[bold]1. Personal Access Token (PAT):[/bold] Easiest")
    console.print("   Get at: [blue]https://www.figma.com/developers/api#access-tokens[/blue]")
    console.print("[bold]2. OAuth 2.0:[/bold] Full access, requires app")
    console.print("   Create app at: [blue]https://www.figma.com/developers[/blue]\n")

    choice = Prompt.ask("Method", choices=["pat", "oauth"], default="pat")

    if choice == "pat":
        token = Prompt.ask("Figma PAT (figd_...)", password=True)
        if token:
            from ..servers.figma import FigmaServer
            from ..config import KimiConfig
            config = KimiConfig()
            cfg = FigmaServer.get_console_config(token)
            config.add_server("figma", cfg)
            console.print("[green]Figma configured (PAT)![/green]")
            return {"access_token": token}
    else:
        client_id = Prompt.ask("Figma Client ID")
        client_secret = Prompt.ask("Figma Client Secret", password=True)

        handler = WebFlowHandler(
            auth_url="https://www.figma.com/oauth",
            token_url="https://www.figma.com/api/oauth/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=["file_read", "file_write"],
        )

        token_data = handler.authorize(timeout=120)
        if token_data:
            store = TokenStore(__get_config_dir())
            store.save("figma", token_data)
            console.print("[bold green]Figma authorized![/bold green]")
            return token_data

    return None


# ---------------------------------------------------------------------------
# Registry of all auth handlers
# ---------------------------------------------------------------------------

AUTH_HANDLERS: dict[str, Callable[[], dict | None]] = {
    "github": authenticate_github,
    "jira": lambda: authenticate_atlassian("jira"),
    "confluence": lambda: authenticate_atlassian("confluence"),
    "gmail": authenticate_google,
    "slack": authenticate_slack,
    "figma": authenticate_figma,
}


def authenticate(server: str) -> dict | None:
    """Authenticate with any supported MCP server.

    Args:
        server: Server name (github, jira, gmail, etc.)

    Returns:
        Token dict or None on failure.
    """
    handler = AUTH_HANDLERS.get(server)
    if not handler:
        console.print(f"[red]No OAuth handler for: {server}[/red]")
        console.print(f"[dim]Supported: {', '.join(AUTH_HANDLERS.keys())}[/dim]")
        return None
    return handler()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def __get_config_dir() -> Path:
    """Get config directory."""
    from pathlib import Path
    import platformdirs
    config_dir = Path(platformdirs.user_config_dir("kimi-mcp-hub", "MoonshotAI"))
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir
