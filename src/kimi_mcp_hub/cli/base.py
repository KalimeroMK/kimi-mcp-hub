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
from ..i18n import _
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
        _("[green]{n} configured[/green]").format(n=counts["servers_configured"])
        if counts["servers_configured"] > 0
        else _("[dim]0 configured[/dim]")
    )
    skill_line = (
        _("[green]{n} installed[/green]").format(n=counts["skills_installed"])
        if counts["skills_installed"] > 0
        else _("[dim]0 installed[/dim]")
    )

    welcome_text = (
        f"[bold cyan]{__title__}[/bold cyan] [dim]v{__version__}[/dim]\n"
        + _("[dim]One-click MCP server & skills manager for Kimi CLI[/dim]\n")
        + "\n"
        + _("{servers} MCP Servers available  ({server_line})\n").format(
            servers=f"[cyan]{len(SERVERS)}[/cyan]", server_line=server_line
        )
        + _("{skills} Skills available       ({skill_line})\n").format(
            skills=f"[cyan]{len(SKILLS)}[/cyan]", skill_line=skill_line
        )
        + _("{memory}  Persistent memory").format(memory="[cyan]1[/cyan]")
    )

    console.print(
        Panel.fit(
            welcome_text,
            title=_("[bold]Kimi MCP Hub v{version}[/bold]").format(version=__version__),
            subtitle=_("[dim]Run: kimi-mcp-hub init[/dim]"),
            border_style="cyan",
        )
    )


def print_header(title: str | None = None):
    """Print compact header (used by subcommands)."""
    panel_title = f"[bold]{title}[/bold]" if title else None
    console.print(
        Panel.fit(
            f"[bold cyan]{__title__}[/bold cyan] [dim]v{__version__}[/dim]\n"
            + _("[dim]{servers} MCP Servers  |  {skills} Skills  |  Persistent Memory[/dim]").format(
                servers=len(SERVERS), skills=len(SKILLS)
            ),
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
            _("\n[dim]Tip: Run [bold]kimi-mcp-hub init[/bold] for interactive setup,[/dim]")
        )
        console.print(
            _("[dim]     or [bold]kimi-mcp-hub --help[/bold] to see all commands.[/dim]\n")
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
        console.print(_("[red]No project root found.[/red]"))
        console.print(
            _("[dim]Run inside a git repo or a directory with a .kimi/ folder.[/dim]")
        )
        sys.exit(1)
    return project_root


def _resolve_project_root(project: bool, global_: bool) -> Path | None:
    """Decide whether a command writes to the project or the global config.

    Explicit ``--project`` wins; ``--global`` forces the global config.
    Without flags, project mode is adopted automatically when the current
    project already has a ``.kimi/`` directory. Returns None for global.
    """
    if project and global_:
        console.print(_("[red]--project and --global are mutually exclusive.[/red]"))
        sys.exit(1)
    if global_:
        return None
    if project:
        return _require_project_root()
    root = find_project_root()
    if root and (root / ".kimi").is_dir():
        console.print(
            _(
                "[dim]Project config detected: saving to {path} "
                "(use --global for the global config)[/dim]"
            ).format(path=root / ".kimi")
        )
        return root
    return None
