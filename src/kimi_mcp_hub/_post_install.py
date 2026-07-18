"""Post-install welcome message for Kimi MCP Hub.

Shows a welcome message on first run after installation.
Also shows version-changed message when upgrading.
"""

from pathlib import Path

import platformdirs

from . import __version__, __title__, TOTAL_SERVERS, TOTAL_SKILLS
from .i18n import _


def _get_state_file() -> Path:
    """Return path to the state file tracking first-run."""
    state_dir = Path(platformdirs.user_config_dir("kimi-mcp-hub", "MoonshotAI"))
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir / ".install-state.json"


def check_first_run():
    """Check if this is first run or version change, print welcome if so."""
    import json

    state_file = _get_state_file()
    current_version = __version__

    # Default state
    state = {"version": None, "first_run": True}

    if state_file.exists():
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    prev_version = state.get("version")

    # Show message on first install or version change
    if prev_version != current_version:
        if prev_version is None:
            # First install
            _print_first_install_message()
        else:
            # Upgrade
            _print_upgrade_message(prev_version, current_version)

        # Update state
        state["version"] = current_version
        state["first_run"] = False
        try:
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
        except OSError:
            pass


def _print_first_install_message():
    """Print welcome message after first installation."""
    try:
        from rich.console import Console
        from rich.panel import Panel

        console = Console()
        message = (
            _("[bold green]{title} v{version} installed successfully![/bold green]\n\n").format(
                title=__title__, version=__version__
            )
            + _("{n} MCP servers available (Jira, GitHub, Slack, Datadog, Perplexity, ...)\n").format(
                n=f"[cyan]{TOTAL_SERVERS}[/cyan]"
            )
            + _("{n} AI skills for better coding\n").format(n=f"[cyan]{TOTAL_SKILLS}[/cyan]")
            + _("{n}  Persistent memory system\n\n").format(n="[cyan]1[/cyan]")
            + _("[bold]Get started:[/bold]\n")
            + _("  [bold]kimi-mcp-hub init[/bold]    -- interactive wizard\n")
            + _("  [bold]kimi-mcp-hub welcome[/bold] -- detailed overview\n")
            + _("  [bold]kimi-mcp-hub status[/bold]  -- status check\n")
            + _("  [bold]kimi-mcp-hub doctor[/bold]  -- system health check")
        )
        console.print("")
        console.print(Panel.fit(message, title="🎯 Kimi MCP Hub", border_style="green"))
        console.print("")
    except Exception:
        # Fallback if rich is not available
        print(f"\n{'=' * 50}")
        print(f"  {__title__} v{__version__} installed successfully!")
        print(f"{'=' * 50}")
        print(
            f"  {TOTAL_SERVERS} MCP servers | {TOTAL_SKILLS} AI skills | Persistent memory"
        )
        print("")
        print("  Get started: kimi-mcp-hub init")
        print(f"{'=' * 50}\n")


def _print_upgrade_message(old_ver: str, new_ver: str):
    """Print upgrade message when version changes."""
    try:
        from rich.console import Console
        from rich.panel import Panel

        console = Console()
        message = (
            _("[bold green]{title} upgraded from v{old} to v{new}![/bold green]\n\n").format(
                title=__title__, old=old_ver, new=new_ver
            )
            + _("[dim]See what's new:[/dim] [bold]kimi-mcp-hub welcome[/bold]")
        )
        console.print("")
        console.print(Panel.fit(message, title="⬆️ Upgrade", border_style="blue"))
        console.print("")
    except Exception:
        print(f"\n{__title__} upgraded: v{old_ver} → v{new_ver}\n")
