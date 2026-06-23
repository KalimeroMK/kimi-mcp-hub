"""Import MCP servers from Claude Desktop/Code."""

from .config import KimiConfig

import json
import platform
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm
from rich import box

from .preflight import maybe_install_npx_deps

console = Console()


def find_claude_config() -> Path | None:
    """Find Claude Desktop or Claude Code config file."""
    system = platform.system()

    # Claude Desktop paths
    if system == "Darwin":  # macOS
        desktop_path = Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    elif system == "Windows":
        desktop_path = Path.home() / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json"
    else:  # Linux
        desktop_path = Path.home() / ".config" / "Claude" / "claude_desktop_config.json"

    if desktop_path.exists():
        return desktop_path

    # Claude Code config
    code_path = Path.home() / ".claude" / "CLAUDE.md"
    if code_path.exists():
        # Claude Code stores MCP in settings.json or similar
        code_settings = Path.home() / ".claude" / "settings.json"
        if code_settings.exists():
            return code_settings

    return None


def parse_claude_config(config_path: Path) -> dict[str, Any]:
    """Parse Claude config and return mcpServers dict."""
    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("mcpServers", {})


def classify_server(name: str, config: dict) -> tuple[str, str, bool]:
    """Classify server as importable or needs re-auth.

    Returns: (status, icon, can_import)
    - "api-token" → 🔑 can import fully
    - "oauth" → 🔐 needs re-auth (config only)
    - "unknown" → ❓ unknown auth type
    """
    # Check for env with API keys/tokens
    env = config.get("env", {})
    if env:
        # Has API token in env → fully importable
        return ("api-token", "🔑", True)

    # Check for HTTP transport with OAuth
    transport = config.get("transport", "stdio")
    if transport == "http":
        auth = config.get("auth", "")
        if auth == "oauth":
            return ("oauth", "🔐", False)
        return ("http", "🌐", True)

    # Check for command-based with no env → likely needs auth
    if "command" in config and not env:
        return ("unknown", "❓", False)

    return ("unknown", "❓", False)


def import_claude_servers(config: KimiConfig) -> None:
    """Interactive import from Claude Desktop/Code."""
    console.print("\n[bold cyan]Import from Claude Desktop/Code[/bold cyan]\n")

    config_path = find_claude_config()
    if not config_path:
        console.print("[yellow]⚠️ No Claude Desktop or Claude Code config found.[/yellow]")
        console.print("[dim]Searched locations:[/dim]")
        console.print("  - ~/Library/Application Support/Claude/claude_desktop_config.json")
        console.print("  - ~/.config/Claude/claude_desktop_config.json")
        console.print("  - ~/.claude/settings.json")
        return

    console.print(f"[green]✅ Found config: {config_path}[/green]\n")

    try:
        servers = parse_claude_config(config_path)
    except json.JSONDecodeError:
        console.print("[red]❌ Invalid JSON in config file.[/red]")
        return

    if not servers:
        console.print("[yellow]No MCP servers found in Claude config.[/yellow]")
        return

    # Build table
    table = Table(title="Claude MCP Servers", box=box.ROUNDED)
    table.add_column("Server", style="cyan")
    table.add_column("Type", style="magenta")
    table.add_column("Auth", style="yellow")
    table.add_column("Import", style="green")

    classified = {}
    for name, cfg in servers.items():
        status, icon, can_import = classify_server(name, cfg)
        classified[name] = (cfg, status, icon, can_import)

        transport = cfg.get("transport", "stdio")
        if "command" in cfg:
            transport = f"stdio ({cfg['command']})"
        elif "url" in cfg:
            transport = f"http ({cfg['url'][:40]}...)"

        import_status = "✅ Full" if can_import else "⚠️ Config only"
        if status == "oauth":
            import_status = "🔐 Needs re-auth"

        table.add_row(
            f"{icon} {name}",
            transport,
            status,
            import_status,
        )

    console.print(table)
    console.print("\n[dim]🔑 = API token (fully importable) | 🔐 = OAuth (needs re-auth) | ❓ = Unknown[/dim]\n")

    # Ask which to import
    imported = 0
    for name, (cfg, status, icon, can_import) in classified.items():
        if not can_import:
            if status == "oauth":
                if Confirm.ask(f"Import {name} config (you'll need to re-auth)?", default=False):
                    # Import config only, strip env if any
                    clean_cfg = {k: v for k, v in cfg.items() if k != "env"}
                    maybe_install_npx_deps(clean_cfg, console)
                    config.add_server(name, clean_cfg)
                    console.print(f"[green]✅ Imported {name} config[/green] — run [bold]kimi mcp auth {name}[/bold]")
                    imported += 1
            continue

        # Fully importable
        if Confirm.ask(f"Import {icon} {name} with credentials?", default=True):
            maybe_install_npx_deps(cfg, console)
            config.add_server(name, cfg)
            console.print(f"[green]✅ Imported {name}[/green]")
            imported += 1

    console.print(f"\n[bold green]✅ Imported {imported} server(s)[/bold green]")
    if imported > 0:
        console.print("[dim]Run [bold]kimi-mcp-hub list[/bold] to verify.[/dim]")
