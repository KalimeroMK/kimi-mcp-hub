"""Status/info/utility commands: status, notify, welcome, doctor, pack, shell-init."""

from __future__ import annotations

import json
import os
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
from ..i18n import _
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
    table.add_column(_("Property"), style="cyan")
    table.add_column(_("Value"), style="bold")

    table.add_row(_("Version"), f"[cyan]{__version__}[/cyan]")
    table.add_row(
        _("MCP Servers"),
        _("{configured} / {total} configured").format(
            configured=counts["servers_configured"], total=counts["total_servers"]
        ),
    )
    table.add_row(
        _("Skills"),
        _("{installed} / {total} installed").format(
            installed=counts["skills_installed"], total=counts["total_skills"]
        ),
    )

    project_root = find_project_root()
    if project_root:
        pc = ProjectConfig(project_root)
        project_status = (
            f"[green]{project_root.name}[/green]"
            if pc.exists()
            else _("[dim]{name} (no .kimi/mcp.json)[/dim]").format(name=project_root.name)
        )
        table.add_row(_("Project"), project_status)

    table.add_row(
        _("Memory"),
        (
            _("[green]enabled[/green]")
            if config.memory_db.exists()
            else _("[dim]disabled[/dim]")
        ),
    )

    # Check if Kimi CLI is installed
    try:
        result = subprocess.run(
            ["kimi", "--version"], capture_output=True, text=True, timeout=5
        )
        kimi_ver = result.stdout.strip() if result.returncode == 0 else "not found"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        kimi_ver = _("[red]not installed[/red]")
    table.add_row(_("Kimi CLI"), kimi_ver)

    console.print(
        Panel.fit(
            table,
            title=_("[bold]{title} Status[/bold]").format(title=__title__),
            border_style="green" if counts["servers_configured"] > 0 else "yellow",
        )
    )

    if counts["servers_configured"] == 0:
        console.print(
            _("\n[dim]Tip: Run [bold]kimi-mcp-hub init[/bold] to set up your first MCP server.[/dim]\n")
        )


@main.command()
def notify():
    """Print a short startup notification for shell wrappers."""
    console.print(
        _("[bold green]●[/bold green] [bold]{title} v{version}[/bold] [dim]plugin installed[/dim]").format(
            title=__title__, version=__version__
        )
    )


@main.command()
def welcome():
    """Display the welcome banner with version and installation info."""
    print_welcome()

    # Print installed servers detail
    config = KimiConfig()
    servers = config.list_servers()
    if servers:
        console.print(_("\n[bold]Configured MCP Servers:[/bold]"))
        for name, cfg in servers.items():
            console.print(f"  [green]{name}[/green] -- {cfg.get('transport', 'stdio')}")

    # Print installed skills
    skills = list_installed_skills(config)
    if skills:
        console.print(_("\n[bold]Installed Skills ({n}):[/bold]").format(n=len(skills)))
        for s in skills:
            desc = SKILLS.get(s, "")
            console.print(f"  [green]{s}[/green] {desc}")

    console.print(
        _("\n[bold green]Kimi MCP Hub v{version} is ready![/bold green]").format(
            version=__version__
        )
    )
    console.print(_("[dim]Start Kimi CLI with: [bold]kimi[/bold][/dim]\n"))


@main.command()
def doctor():
    """Check system health -- node, npx, kimi CLI, docker."""
    print_header()
    table = Table(box=box.ROUNDED)
    table.add_column(_("Check"), style="cyan")
    table.add_column(_("Status"), style="bold")
    table.add_column(_("Note"), style="dim")

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
                table.add_row(name, f"[green]{ver}[/green]", _("Found"))
            else:
                table.add_row(name, _("[red]Error[/red]"), result.stderr[:50])
        except FileNotFoundError:
            table.add_row(name, _("[red]Missing[/red]"), _("Install {name}").format(name=name))
        except Exception as e:
            table.add_row(name, _("[red]Fail[/red]"), str(e)[:50])

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
            console.print(_("\n[yellow]Fixed permissions (chmod 600):[/yellow]"))
            for fp in fixed_files:
                console.print(f"  {fp}")

    servers = config.list_servers()
    if servers:
        console.print(
            _("\n[green]{n} MCP server(s) in ~/.kimi-code/mcp.json[/green]").format(
                n=len(servers)
            )
        )
    else:
        console.print(_("\n[yellow]No MCP servers configured yet[/yellow]"))

    # Duplicate check: servers provided by an installed Kimi plugin AND mcp.json
    plugin_servers: set[str] = set()
    for manifest in config.kimi_dir.glob("plugins/**/kimi.plugin.json"):
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            plugin_servers.update(data.get("mcpServers", {}))
        except (json.JSONDecodeError, OSError):
            continue
    duplicates = sorted(plugin_servers & set(servers))
    if duplicates:
        console.print(
            _("\n[yellow]Duplicate servers (provided by a Kimi plugin AND mcp.json):[/yellow]")
        )
        for name in duplicates:
            console.print(
                _("  [yellow]{name}[/yellow] — remove the mcp.json entry: [bold]kimi-mcp-hub remove {name}[/bold]").format(
                    name=name
                )
            )

    skills_installed = list_installed_skills(config)
    if skills_installed:
        console.print(
            _("[green]{n} skills in ~/.kimi-code/skills/[/green]").format(
                n=len(skills_installed)
            )
        )
    else:
        console.print(_("[yellow]No skills installed yet[/yellow]"))

    if config.memory_db.exists():
        console.print(
            _("[green]Memory database: {path}[/green]").format(path=config.memory_db)
        )
    else:
        console.print(_("[dim]Memory not enabled[/dim]"))

    console.print(
        _("\n[dim]Run [bold]kimi-mcp-hub init[/bold] to set up everything.[/dim]\n")
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
    console.print(_("[dim]Packing:[/dim] {root}").format(root=root))

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
        console.print(_("[red]Error: {exc}[/red]").format(exc=exc))
        sys.exit(1)

    if output and str(output) != "-":
        try:
            output.write_text(markdown, encoding="utf-8")
        except OSError as exc:
            console.print(
                _("[red]Error: could not write {output}: {exc}[/red]").format(
                    output=output, exc=exc
                )
            )
            sys.exit(1)
        size = output.stat().st_size
        console.print(
            _("[green]Wrote pack to[/green] {output} [dim]({size} bytes)[/dim]").format(
                output=output, size=size
            )
        )
    else:
        click.echo(markdown)


SHELL_INIT_MARKER_BEGIN = "# >>> kimi-mcp-hub shell-init >>>"
SHELL_INIT_MARKER_END = "# <<< kimi-mcp-hub shell-init <<<"

SHELL_SNIPPET = f"""{SHELL_INIT_MARKER_BEGIN}
# Auto-sync project MCP config (.kimi/mcp.json) on every Kimi start.
k() {{
  kimi-mcp-hub sync >/dev/null 2>&1
  kimi "$@"
}}
{SHELL_INIT_MARKER_END}"""


def _detect_rc_file() -> Path | None:
    """Return the rc file for the user's login shell, or None if unknown."""
    shell = os.environ.get("SHELL", "")
    if shell.endswith("zsh"):
        return Path.home() / ".zshrc"
    if shell.endswith("bash"):
        return Path.home() / ".bashrc"
    return None


@main.command(name="shell-init")
@click.option(
    "--install",
    is_flag=True,
    help="Append the snippet to your shell rc file instead of printing it.",
)
def shell_init(install: bool):
    """Shell wrapper that auto-syncs project MCP config when you start Kimi.

    Without --install, prints the snippet. With --install, appends it to
    ~/.zshrc or ~/.bashrc (idempotent). Afterwards use `k` instead of `kimi`;
    each Kimi start in a project with .kimi/mcp.json syncs that project's
    servers into the global config.
    """
    print_header()

    if not install:
        console.print(SHELL_SNIPPET)
        console.print(
            _(
                "\n[dim]Add this to your ~/.zshrc or ~/.bashrc (or run "
                "[bold]kimi-mcp-hub shell-init --install[/bold]), then use "
                "[bold]k[/bold] instead of [bold]kimi[/bold].[/dim]\n"
            )
        )
        return

    rc_file = _detect_rc_file()
    if rc_file is None:
        console.print(
            _("[red]Unsupported shell: {shell}[/red]").format(
                shell=os.environ.get("SHELL", "unknown")
            )
        )
        console.print(
            _("[dim]Only zsh and bash are supported. Add the snippet manually.[/dim]")
        )
        sys.exit(1)

    existing = rc_file.read_text(encoding="utf-8") if rc_file.exists() else ""
    if SHELL_INIT_MARKER_BEGIN in existing:
        console.print(
            _("[green]Already installed in {path}[/green]").format(path=rc_file)
        )
        return

    with open(rc_file, "a", encoding="utf-8") as f:
        f.write(f"\n{SHELL_SNIPPET}\n")
    console.print(_("[green]Installed in {path}[/green]").format(path=rc_file))
    console.print(
        _("[dim]Restart your shell (or run: source {path}), then use [bold]k[/bold] instead of [bold]kimi[/bold].[/dim]").format(
            path=rc_file
        )
    )
