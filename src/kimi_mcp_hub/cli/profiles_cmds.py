"""Profile commands: save/load/list/remove named MCP-server bundles."""

from __future__ import annotations

import sys

import click
from rich import box
from rich.prompt import Confirm
from rich.table import Table

from ..config import KimiConfig
from ..i18n import _
from ..profiles import ProfileStore
from .base import main, print_header
from .common import console


@main.group()
def profile():
    """Manage named MCP-server profiles (save/load whole server sets)."""


@profile.command()
@click.argument("name")
def save(name: str):
    """Save the current global MCP servers as a named profile."""
    print_header()
    config = KimiConfig()
    servers = config.list_servers()
    store = ProfileStore()
    try:
        path = store.save(name, {"mcpServers": servers})
    except ValueError as exc:
        console.print(_("[red]{exc}[/red]").format(exc=exc))
        sys.exit(1)
    console.print(
        _("[green]Saved profile [bold]{name}[/bold] ({n} servers)[/green]").format(
            name=name, n=len(servers)
        )
    )
    console.print(f"[dim]{path}[/dim]")


@profile.command()
@click.argument("name")
@click.option(
    "--yes", is_flag=True, help="Replace the global config without asking."
)
def load(name: str, yes: bool):
    """Replace the global MCP servers with a saved profile."""
    print_header()
    store = ProfileStore()
    try:
        data = store.load(name)
    except ValueError as exc:
        console.print(_("[red]{exc}[/red]").format(exc=exc))
        sys.exit(1)
    if data is None:
        console.print(_("[red]Profile not found: {name}[/red]").format(name=name))
        existing = store.list()
        if existing:
            console.print(
                _("[dim]Available profiles: {names}[/dim]").format(
                    names=", ".join(existing)
                )
            )
        sys.exit(1)

    servers = data.get("mcpServers", {})
    if not yes and not Confirm.ask(
        _("Replace global config with profile [bold]{name}[/bold] ({n} servers)?").format(
            name=name, n=len(servers)
        ),
        default=True,
    ):
        console.print(_("[dim]Cancelled.[/dim]"))
        return

    config = KimiConfig()
    config.save_mcp({"mcpServers": servers})
    console.print(
        _("[green]Loaded profile [bold]{name}[/bold] ({n} servers)[/green]").format(
            name=name, n=len(servers)
        )
    )
    for server_name in servers:
        console.print(f"  [cyan]{server_name}[/cyan]")


@profile.command(name="list")
def list_profiles():
    """List saved profiles."""
    print_header()
    store = ProfileStore()
    names = store.list()
    if not names:
        console.print(
            _("[yellow]No profiles saved.[/yellow] Use [bold]kimi-mcp-hub profile save <name>[/bold].")
        )
        return

    table = Table(title=_("Profiles"), box=box.ROUNDED)
    table.add_column(_("Profile"), style="cyan")
    table.add_column(_("Servers"), style="green")
    for name in names:
        data = store.load(name) or {}
        server_names = data.get("mcpServers", {})
        table.add_row(name, f"{len(server_names)} — {', '.join(server_names)}")
    console.print(table)


@profile.command()
@click.argument("name")
def remove(name: str):
    """Delete a saved profile."""
    print_header()
    store = ProfileStore()
    try:
        removed = store.remove(name)
    except ValueError as exc:
        console.print(_("[red]{exc}[/red]").format(exc=exc))
        sys.exit(1)
    if removed:
        console.print(_("[green]Removed profile {name}[/green]").format(name=name))
    else:
        console.print(_("[red]Profile not found: {name}[/red]").format(name=name))
        sys.exit(1)
