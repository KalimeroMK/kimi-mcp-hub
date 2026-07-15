"""The click group, banner helpers, and shared prompts."""

from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.panel import Panel
from rich.prompt import Confirm

from .. import __title__, __version__
from .._post_install import check_first_run
from ..config import KimiConfig
from ..project import find_project_root
from ..registry import SERVERS, SKILLS
from .common import console
from .helpers import list_installed_skills


def _get_installed_count(config: KimiConfig) -> dict:
    """Get counts of installed servers, skills for display."""
    servers = config.list_servers()
    skills_installed = list_installed_skills(config)
    return {
        "servers_configured": len(servers),
        "skills_installed": len(skills_installed),
        "total_servers": len(SERVERS),
        "total_skills": len(SKILLS),
    }


def print_welcome():
    """Print the full welcome banner with version and status."""
    config = KimiConfig()
    counts = _get_installed_count(config)

    # Build status line
    server_line = (
        f"[green]{counts['servers_configured']} configured[/green]"
        if counts["servers_configured"] > 0
        else "[dim]0 configured[/dim]"
    )
    skill_line = (
        f"[green]{counts['skills_installed']} installed[/green]"
        if counts["skills_installed"] > 0
        else "[dim]0 installed[/dim]"
    )

    welcome_text = (
        f"[bold cyan]{__title__}[/bold cyan] [dim]v{__version__}[/dim]\n"
        f"[dim]One-click MCP server & skills manager for Kimi CLI[/dim]\n"
        f"\n"
        f"[cyan]{len(SERVERS)}[/cyan] MCP Servers available  ({server_line})\n"
        f"[cyan]{len(SKILLS)}[/cyan] Skills available       ({skill_line})\n"
        f"[cyan]1[/cyan]  Persistent memory"
    )

    console.print(
        Panel.fit(
            welcome_text,
            title=f"[bold]Kimi MCP Hub v{__version__}[/bold]",
            subtitle="[dim]Run: kimi-mcp-hub init[/dim]",
            border_style="cyan",
        )
    )


def print_header(title: str | None = None):
    """Print compact header (used by subcommands)."""
    panel_title = f"[bold]{title}[/bold]" if title else None
    console.print(
        Panel.fit(
            f"[bold cyan]{__title__}[/bold cyan] [dim]v{__version__}[/dim]\n"
            f"[dim]{len(SERVERS)} MCP Servers  |  {len(SKILLS)} Skills  |  Persistent Memory[/dim]",
            title=panel_title,
            border_style="cyan",
        )
    )


@click.group(invoke_without_command=True)
@click.version_option(version=__version__, prog_name="kimi-mcp-hub")
@click.pass_context
def main(ctx):
    """kimi-mcp-hub -- Manage MCP servers and skills for Kimi CLI.

    When called without a command, prints the welcome banner and status.
    """
    # Show first-install or upgrade message only when the CLI is invoked.
    try:
        check_first_run()
    except Exception:
        pass

    if ctx.invoked_subcommand is None:
        print_welcome()
        console.print(
            "\n[dim]Tip: Run [bold]kimi-mcp-hub init[/bold] for interactive setup,[/dim]"
        )
        console.print(
            "[dim]     or [bold]kimi-mcp-hub --help[/bold] to see all commands.[/dim]\n"
        )


def _confirm(text: str, default: bool = False, yes: bool = False) -> bool:
    """Return default value in non-interactive mode, otherwise prompt the user."""
    if yes:
        return default
    return Confirm.ask(text, default=default)


def _require_project_root() -> Path:
    """Resolve the current project root or exit with an error."""
    project_root = find_project_root()
    if not project_root:
        console.print("[red]No project root found.[/red]")
        console.print(
            "[dim]Run inside a git repo or a directory with a .kimi/ folder.[/dim]"
        )
        sys.exit(1)
    return project_root
