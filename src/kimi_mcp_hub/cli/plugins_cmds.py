"""Plugin commands: install-plugin, uninstall-plugin, update-plugin."""

from __future__ import annotations

import sys

import click
from rich.prompt import Confirm

from ..config import KimiConfig
from ..plugin_installer import (
    install_plugin,
    resolve_repo,
    uninstall_plugin,
    update_plugin,
)
from .base import main, print_header
from .common import console


@main.command(name="install-plugin")
@click.argument("repo")
@click.option(
    "--yes",
    is_flag=True,
    help="Skip confirmation prompts and overwrite existing plugin install.",
)
@click.option("--name", help="Override the auto-detected plugin name.")
def install_plugin_cmd(repo: str, yes: bool, name: str | None):
    """Install a Claude Code / Codex plugin (e.g. Ponytail) into Kimi CLI.

    REPO can be:
      owner/repo
      https://github.com/owner/repo
      /local/path/to/plugin
    """
    print_header()
    config = KimiConfig()

    _, plugin_name = resolve_repo(repo)
    plugin_name = (name or plugin_name).strip()
    plugin_dir = config.plugin_dir(plugin_name)

    if plugin_dir.exists() and any(plugin_dir.iterdir()) and not yes:
        if not Confirm.ask(
            f"Plugin '{plugin_name}' already installed. Reinstall/Update?",
            default=False,
        ):
            console.print("[dim]Cancelled.[/dim]")
            return

    install_plugin(repo, config, name=name)


@main.command(name="uninstall-plugin")
@click.argument("plugin_name")
def uninstall_plugin_cmd(plugin_name: str):
    """Remove an installed plugin from Kimi CLI."""
    print_header()
    config = KimiConfig()

    try:
        result = uninstall_plugin(plugin_name, config)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        sys.exit(1)
    except Exception as exc:
        console.print(f"[red]Uninstall failed: {exc}[/red]")
        sys.exit(1)

    console.print(f"[green]Plugin '{plugin_name}' uninstalled.[/green]")
    console.print(f"[dim]Removed plugin directory: {result['plugin_dir']}[/dim]")
    if result["hooks_removed"]:
        console.print(
            f"[dim]Removed {result['hooks_removed']} hook(s) from config.toml[/dim]"
        )
    if result["skills_removed"]:
        console.print(
            f"[dim]Removed skills: {', '.join(result['skills_removed'])}[/dim]"
        )
    if result["agents_md_removed"]:
        console.print("[dim]Removed AGENTS.md section.[/dim]")


@main.command(name="update-plugin")
@click.argument("plugin_name")
def update_plugin_cmd(plugin_name: str):
    """Update an installed plugin."""
    print_header()
    config = KimiConfig()

    try:
        result = update_plugin(plugin_name, config)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        sys.exit(1)
    except Exception as exc:
        console.print(f"[red]Update failed: {exc}[/red]")
        sys.exit(1)

    console.print(f"[green]Plugin '{plugin_name}' updated.[/green]")
    console.print(f"[dim]Hooks installed: {result['hooks_installed']}[/dim]")
    if result["skills_installed"]:
        console.print(
            f"[dim]Skills installed: {', '.join(result['skills_installed'])}[/dim]"
        )
