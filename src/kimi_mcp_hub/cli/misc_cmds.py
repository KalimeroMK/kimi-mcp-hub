"""Status/info/utility commands: status, notify, welcome, doctor, pack."""

from __future__ import annotations

import stat
import subprocess
import sys
from pathlib import Path

import click
from rich import box
from rich.panel import Panel
from rich.table import Table

from .. import __title__, __version__
from ..config import KimiConfig
from ..pack import RepoPacker
from ..project import ProjectConfig, find_project_root
from ..registry import SKILLS
from .base import _get_installed_count, main, print_header, print_welcome
from .common import console
from .helpers import list_installed_skills


@main.command()
def status():
    """Show Kimi MCP Hub status: version, servers, skills, memory."""
    config = KimiConfig()
    counts = _get_installed_count(config)

    table = Table(box=box.ROUNDED)
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="bold")

    table.add_row("Version", f"[cyan]{__version__}[/cyan]")
    table.add_row(
        "MCP Servers",
        f"{counts['servers_configured']} / {counts['total_servers']} configured",
    )
    table.add_row(
        "Skills", f"{counts['skills_installed']} / {counts['total_skills']} installed"
    )

    project_root = find_project_root()
    if project_root:
        pc = ProjectConfig(project_root)
        project_status = (
            f"[green]{project_root.name}[/green]"
            if pc.exists()
            else f"[dim]{project_root.name} (no .kimi/mcp.json)[/dim]"
        )
        table.add_row("Project", project_status)

    table.add_row(
        "Memory",
        (
            "[green]enabled[/green]"
            if config.memory_db.exists()
            else "[dim]disabled[/dim]"
        ),
    )

    # Check if Kimi CLI is installed
    try:
        result = subprocess.run(
            ["kimi", "--version"], capture_output=True, text=True, timeout=5
        )
        kimi_ver = result.stdout.strip() if result.returncode == 0 else "not found"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        kimi_ver = "[red]not installed[/red]"
    table.add_row("Kimi CLI", kimi_ver)

    console.print(
        Panel.fit(
            table,
            title=f"[bold]{__title__} Status[/bold]",
            border_style="green" if counts["servers_configured"] > 0 else "yellow",
        )
    )

    if counts["servers_configured"] == 0:
        console.print(
            "\n[dim]Tip: Run [bold]kimi-mcp-hub init[/bold] to set up your first MCP server.[/dim]\n"
        )


@main.command()
def notify():
    """Print a short startup notification for shell wrappers."""
    console.print(
        f"[bold green]●[/bold green] [bold]{__title__} v{__version__}[/bold] [dim]plugin installed[/dim]"
    )


@main.command()
def welcome():
    """Display the welcome banner with version and installation info."""
    print_welcome()

    # Print installed servers detail
    config = KimiConfig()
    servers = config.list_servers()
    if servers:
        console.print("\n[bold]Configured MCP Servers:[/bold]")
        for name, cfg in servers.items():
            console.print(f"  [green]{name}[/green] -- {cfg.get('transport', 'stdio')}")

    # Print installed skills
    skills = list_installed_skills(config)
    if skills:
        console.print(f"\n[bold]Installed Skills ({len(skills)}):[/bold]")
        for s in skills:
            desc = SKILLS.get(s, "")
            console.print(f"  [green]{s}[/green] {desc}")

    console.print(f"\n[bold green]Kimi MCP Hub v{__version__} is ready![/bold green]")
    console.print("[dim]Start Kimi CLI with: [bold]kimi[/bold][/dim]\n")


@main.command()
def doctor():
    """Check system health -- node, npx, kimi CLI, docker."""
    print_header()
    table = Table(box=box.ROUNDED)
    table.add_column("Check", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Note", style="dim")

    checks = [
        ("node", ["node", "--version"]),
        ("npx", ["npx", "--version"]),
        ("kimi", ["kimi", "--version"]),
        ("npm", ["npm", "--version"]),
        ("docker", ["docker", "--version"]),
        ("uv", ["uv", "--version"]),
    ]

    for name, cmd in checks:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                ver = (
                    result.stdout.strip().split()[0] if result.stdout.strip() else "OK"
                )
                table.add_row(name, f"[green]{ver}[/green]", "Found")
            else:
                table.add_row(name, "[red]Error[/red]", result.stderr[:50])
        except FileNotFoundError:
            table.add_row(name, "[red]Missing[/red]", f"Install {name}")
        except Exception as e:
            table.add_row(name, "[red]Fail[/red]", str(e)[:50])

    console.print(table)

    config = KimiConfig()

    # Permission check / fix for sensitive files
    if sys.platform != "win32":
        fixed_files = []
        for sensitive_path in (config.mcp_json, config.tokens_file, config.memory_db):
            if sensitive_path.exists():
                try:
                    mode = sensitive_path.stat().st_mode
                    if mode & stat.S_IRWXG or mode & stat.S_IRWXO:
                        sensitive_path.chmod(0o600)
                        fixed_files.append(str(sensitive_path))
                except OSError:
                    pass
        if fixed_files:
            console.print("\n[yellow]Fixed permissions (chmod 600):[/yellow]")
            for fp in fixed_files:
                console.print(f"  {fp}")

    servers = config.list_servers()
    if servers:
        console.print(
            f"\n[green]{len(servers)} MCP server(s) in ~/.kimi-code/mcp.json[/green]"
        )
    else:
        console.print("\n[yellow]No MCP servers configured yet[/yellow]")

    skills_installed = list_installed_skills(config)
    if skills_installed:
        console.print(
            f"[green]{len(skills_installed)} skills in ~/.kimi-code/skills/[/green]"
        )
    else:
        console.print("[yellow]No skills installed yet[/yellow]")

    if config.memory_db.exists():
        console.print(f"[green]Memory database: {config.memory_db}[/green]")
    else:
        console.print("[dim]Memory not enabled[/dim]")

    console.print(
        "\n[dim]Run [bold]kimi-mcp-hub init[/bold] to set up everything.[/dim]\n"
    )


@main.command()
@click.argument(
    "root",
    required=False,
    default=".",
    type=click.Path(path_type=Path),
)
@click.option(
    "-i",
    "--include",
    multiple=True,
    default=["*"],
    help="Include glob patterns (default: '*').",
)
@click.option(
    "-e",
    "--exclude",
    multiple=True,
    help="Exclude glob patterns.",
)
@click.option(
    "--no-gitignore",
    is_flag=True,
    help="Disable .gitignore respect.",
)
@click.option(
    "--max-size",
    default=512000,
    show_default=True,
    help="Max output size in bytes.",
)
@click.option(
    "-o",
    "--output",
    type=click.Path(path_type=Path, allow_dash=True),
    help="Write output to file instead of stdout. Use '-' for stdout.",
)
def pack(
    root: Path,
    include: tuple[str, ...],
    exclude: tuple[str, ...],
    no_gitignore: bool,
    max_size: int,
    output: Path | None,
):
    """Pack a repository into a single AI-friendly markdown file."""
    print_header("Pack Repository")
    root = root.resolve()
    console.print(f"[dim]Packing:[/dim] {root}")

    try:
        include_patterns = [*include]
        exclude_patterns = [*exclude]
        markdown = RepoPacker(
            include=include_patterns,
            exclude=exclude_patterns,
            respect_gitignore=not no_gitignore,
            max_size=max_size,
        ).pack(root)
    except ValueError as exc:
        console.print(f"[red]Error: {exc}[/red]")
        sys.exit(1)

    if output and str(output) != "-":
        try:
            output.write_text(markdown, encoding="utf-8")
        except OSError as exc:
            console.print(f"[red]Error: could not write {output}: {exc}[/red]")
            sys.exit(1)
        size = output.stat().st_size
        console.print(f"[green]Wrote pack to[/green] {output} [dim]({size} bytes)[/dim]")
    else:
        click.echo(markdown)
