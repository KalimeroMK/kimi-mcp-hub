"""Obsidian vault commands."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import click
from rich import box
from rich.table import Table

from ..config import KimiConfig
from ..servers import ObsidianServer
from .base import main
from .common import console
from .helpers import enable_memory


@main.group()
def obsidian():
    """Manage Obsidian vaults for local memory."""


def _obsidian_slug_map(vaults: list[str]) -> dict[str, str]:
    """Return {slug: normalized_path} for the given vault paths."""
    return {
        ObsidianServer.slug_from_vault_path(p): str(Path(p).expanduser().resolve())
        for p in vaults
    }


def _obsidian_vault_rows(config: KimiConfig):
    """Return (slug, path, exists, valid) rows for configured vaults."""
    rows = []
    for path_str in config.get_obsidian_vaults():
        path = Path(path_str).expanduser().resolve()
        slug = ObsidianServer.slug_from_vault_path(path)
        exists = path.exists()
        valid = ObsidianServer.validate_vault(path) if exists else False
        rows.append((slug, path, exists, valid))
    return rows


def _get_git_root(cwd: Path | None = None) -> Path | None:
    """Return the git repository root for the given directory, or None."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        return Path(result.stdout.strip()).resolve()
    except (
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        FileNotFoundError,
    ):
        return None


def _ensure_gitignored(git_root: Path, vault_path: Path) -> bool:
    """Add a gitignore entry for vault_path if it lives under git_root.

    Returns True when a new entry was written, False otherwise.
    """
    try:
        git_root = git_root.resolve()
        vault_path = vault_path.resolve()
        vault_path.relative_to(git_root)
    except (OSError, ValueError):
        return False

    gitignore = git_root / ".gitignore"
    rel_vault = vault_path.relative_to(git_root).as_posix()
    # Always treat the vault as a directory entry.
    entry = f"/{rel_vault}/"

    existing_lines: list[str] = []
    if gitignore.exists():
        try:
            existing_lines = gitignore.read_text(encoding="utf-8").splitlines()
        except OSError:
            return False

    normalized = {line.strip().rstrip("/") for line in existing_lines}
    if rel_vault in normalized or entry.strip("/") in normalized:
        return False

    if existing_lines and existing_lines[-1] != "":
        existing_lines.append("")
    existing_lines.append(f"# Kimi memory vault for {git_root.name}")
    existing_lines.append(entry)

    try:
        gitignore.write_text("\n".join(existing_lines) + "\n", encoding="utf-8")
    except OSError:
        return False
    return True


@obsidian.command(name="auto")
@click.option(
    "--path",
    type=click.Path(path_type=Path, exists=False, file_okay=False, dir_okay=True),
    help="Custom vault path (default: <repo-root>/<RepoName>-Memory).",
)
def obsidian_auto(path: Path | None):
    """Create or switch to a project-specific Obsidian vault in the current git repo.

    This is useful as a shell wrapper before starting Kimi CLI:

        k() { kimi-mcp-hub obsidian auto && kimi "$@"; }

    The command exits silently when not inside a git repository.
    """
    git_root = _get_git_root()
    if not git_root:
        console.print(
            "[dim]Not inside a git repository; no project vault changed.[/dim]"
        )
        return

    slug = git_root.name
    vault_path = path.expanduser().resolve() if path else git_root / f"{slug}-Memory"
    vault_path_str = str(vault_path)

    config = KimiConfig()
    vaults = config.get_obsidian_vaults()
    existing_resolved = {Path(p).expanduser().resolve() for p in vaults}

    if vault_path.resolve() not in existing_resolved:
        slug_map = _obsidian_slug_map(vaults)
        if slug in slug_map and slug_map[slug] != vault_path_str:
            console.print(
                f"[red]Vault slug '{slug}' already used by {slug_map[slug]}.[/red]"
            )
            console.print(
                "[dim]Use --path to choose a different vault directory.[/dim]"
            )
            sys.exit(1)

        ObsidianServer.scaffold_vault(vault_path)
        vaults.append(vault_path_str)
        config.set_obsidian_vaults(vaults)
        console.print(f"[green]Created project vault:[/green] {vault_path}")
    else:
        console.print(f"[dim]Using existing project vault:[/dim] {vault_path}")

    if _ensure_gitignored(git_root, vault_path):
        console.print(f"[dim]Added {vault_path.name} to .gitignore.[/dim]")

    config.set_default_memory_vault(vault_path_str)
    console.print(f"[dim]Default memory vault set to {slug}.[/dim]")

    enable_memory(config)
    console.print(f"[dim]Memory hooks installed for vault {slug}.[/dim]")


@obsidian.command(name="status")
def obsidian_status():
    """Show configured Obsidian vaults and their status."""
    config = KimiConfig()
    rows = _obsidian_vault_rows(config)
    if not rows:
        console.print("[yellow]No Obsidian vaults configured.[/yellow]")
        console.print("Run [bold]kimi-mcp-hub obsidian add <path>[/bold] to add one.\n")
        return

    table = Table(title="Obsidian Vaults", box=box.ROUNDED)
    table.add_column("Slug", style="cyan")
    table.add_column("Path", style="white")
    table.add_column("Status", style="green")
    for slug, path, exists, valid in rows:
        if valid:
            status_text = "[green]valid[/green]"
        elif exists:
            status_text = "[yellow]invalid[/yellow]"
        else:
            status_text = "[red]missing[/red]"
        table.add_row(slug, str(path), status_text)
    console.print(table)

    default_vault = config.get_default_memory_vault()
    if default_vault:
        console.print(f"\n[dim]Default memory vault:[/dim] {default_vault}")


@obsidian.command(name="list")
def obsidian_list():
    """List configured Obsidian vaults."""
    config = KimiConfig()
    rows = _obsidian_vault_rows(config)
    if not rows:
        console.print("[yellow]No Obsidian vaults configured.[/yellow]")
        console.print("Run [bold]kimi-mcp-hub obsidian add <path>[/bold] to add one.\n")
        return

    for slug, path, exists, valid in rows:
        status_text = "valid" if valid else ("exists" if exists else "missing")
        console.print(f"  [cyan]{slug}[/cyan]  {path}  [dim]({status_text})[/dim]")

    default_vault = config.get_default_memory_vault()
    if default_vault:
        console.print(f"\n[dim]Default memory vault:[/dim] {default_vault}")


@obsidian.command(name="add")
@click.argument(
    "path",
    type=click.Path(path_type=Path, exists=False, file_okay=False, dir_okay=True),
)
def obsidian_add(path: Path):
    """Add an Obsidian vault path."""
    config = KimiConfig()
    vault_path = path.expanduser().resolve()

    vaults = config.get_obsidian_vaults()
    existing_resolved = {Path(p).expanduser().resolve() for p in vaults}
    if vault_path in existing_resolved:
        console.print(f"[yellow]Vault {vault_path} is already configured.[/yellow]")
        return

    slug_map = _obsidian_slug_map(vaults)
    new_slug = ObsidianServer.slug_from_vault_path(vault_path)
    if new_slug in slug_map and slug_map[new_slug] != str(vault_path):
        console.print(
            f"[red]Vault slug '{new_slug}' already used by {slug_map[new_slug]}.[/red]"
        )
        console.print("[dim]Choose a vault path with a different directory name.[/dim]")
        sys.exit(1)

    ObsidianServer.scaffold_vault(vault_path)

    path_str = str(vault_path)
    vaults.append(path_str)
    config.set_obsidian_vaults(vaults)
    console.print(
        f"[green]Added vault:[/green] {vault_path}  "
        f"[dim]({ObsidianServer.slug_from_vault_path(vault_path)})[/dim]"
    )

    if config.get_default_memory_vault() is None:
        config.set_default_memory_vault(path_str)
        console.print("[dim]Set as default memory vault.[/dim]")


@obsidian.command(name="remove")
@click.argument("slug")
def obsidian_remove(slug: str):
    """Remove an Obsidian vault from the config by slug (files are kept)."""
    config = KimiConfig()
    vaults = config.get_obsidian_vaults()
    slug_map = _obsidian_slug_map(vaults)

    if slug not in slug_map:
        console.print(f"[red]No vault with slug '{slug}' configured.[/red]")
        available = ", ".join(sorted(slug_map)) or "none"
        console.print(f"[dim]Configured slugs: {available}[/dim]")
        sys.exit(1)

    removed = slug_map[slug]
    vaults = [p for p in vaults if str(Path(p).expanduser().resolve()) != removed]
    config.set_obsidian_vaults(vaults)

    default_vault = config.get_default_memory_vault()
    if default_vault and str(Path(default_vault).expanduser().resolve()) == removed:
        if vaults:
            config.set_default_memory_vault(vaults[0])
            console.print(f"[dim]Default memory vault moved to {vaults[0]}.[/dim]")
        else:
            config.clear_default_memory_vault()

    console.print(f"[green]Removed vault '{slug}'.[/green]")
    console.print("[dim]Vault files were not deleted.[/dim]")


def _default_obsidian_templates_dir() -> Path:
    """Default package location for Obsidian templates."""
    return Path(__file__).parent.parent / "templates" / "obsidian"


@obsidian.command(name="sync-templates")
@click.argument("vault_slug")
@click.option(
    "--templates-dir",
    type=click.Path(path_type=Path),
    help="Directory of template markdown files.",
)
def obsidian_sync_templates(vault_slug: str, templates_dir: Path | None):
    """Copy template notes into the specified vault."""
    config = KimiConfig()
    vaults = config.get_obsidian_vaults()
    slug_map = _obsidian_slug_map(vaults)

    if vault_slug not in slug_map:
        console.print(f"[red]No vault with slug '{vault_slug}' configured.[/red]")
        sys.exit(1)

    vault_path = Path(slug_map[vault_slug])
    templates_dir = templates_dir or _default_obsidian_templates_dir()

    if not templates_dir.exists():
        console.print(
            f"[yellow]Templates directory not found: {templates_dir}[/yellow]"
        )
        return

    copied = ObsidianServer.sync_templates(templates_dir, vault_path)
    if copied:
        console.print(
            f"[green]Synced {len(copied)} template(s) to {vault_slug}.[/green]"
        )
        for note in copied:
            console.print(f"  [dim]{note}[/dim]")
    else:
        console.print(f"[dim]No new templates to sync to {vault_slug}.[/dim]")
