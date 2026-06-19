"""Post-install welcome message for Kimi MCP Hub.

Shows a welcome message on first run after installation.
Also shows version-changed message when upgrading.
"""

from pathlib import Path

from . import __version__, __title__, TOTAL_SERVERS, TOTAL_SKILLS


def _get_state_file() -> Path:
    """Return path to the state file tracking first-run."""
    state_dir = Path.home() / ".kimi" / "mcp-hub"
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
            f"[bold green]{__title__} v{__version__} е успешно инсталиран![/bold green]\n\n"
            f"[cyan]{TOTAL_SERVERS}[/cyan] MCP сервери достапни (Jira, GitHub, Slack, Datadog, Perplexity, ...)\n"
            f"[cyan]{TOTAL_SKILLS}[/cyan] AI skills за подобро кодирање\n"
            f"[cyan]1[/cyan]  Persistent memory систем\n\n"
            f"[bold]За да започнеш:[/bold]\n"
            f"  [bold]kimi-mcp-hub init[/bold]    -- интерактивен wizard\n"
            f"  [bold]kimi-mcp-hub welcome[/bold] -- детален преглед\n"
            f"  [bold]kimi-mcp-hub status[/bold]  -- статус проверка\n"
            f"  [bold]kimi-mcp-hub doctor[/bold]  -- здравје на системот"
        )
        console.print("")
        console.print(Panel.fit(message, title="🎯 Kimi MCP Hub", border_style="green"))
        console.print("")
    except Exception:
        # Fallback if rich is not available
        print(f"\n{'='*50}")
        print(f"  {__title__} v{__version__} е успешно инсталиран!")
        print(f"{'='*50}")
        print(f"  {TOTAL_SERVERS} MCP сервери | {TOTAL_SKILLS} AI skills | Persistent memory")
        print(f"")
        print(f"  За да започнеш: kimi-mcp-hub init")
        print(f"{'='*50}\n")


def _print_upgrade_message(old_ver: str, new_ver: str):
    """Print upgrade message when version changes."""
    try:
        from rich.console import Console
        from rich.panel import Panel

        console = Console()
        message = (
            f"[bold green]{__title__} е ажуриран од v{old_ver} на v{new_ver}![/bold green]\n\n"
            f"[dim]Провери што е ново:[/dim] [bold]kimi-mcp-hub welcome[/bold]"
        )
        console.print("")
        console.print(Panel.fit(message, title="⬆️ Ажурирање", border_style="blue"))
        console.print("")
    except Exception:
        print(f"\n{__title__} ажуриран: v{old_ver} → v{new_ver}\n")
