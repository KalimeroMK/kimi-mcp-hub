"""Skill commands: install-skill, list-skills, claude-compat."""

from __future__ import annotations

from pathlib import Path

import click
from rich import box
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table

from ..config import KimiConfig
from ..i18n import _
from ..project import ProjectConfig
from ..registry import CORE_SKILLS, SKILLS
from .base import _require_project_root, main, print_header
from .common import console
from .helpers import install_skill, list_installed_skills

CLAUDE_COMPAT_MARKER_START = "<!-- claude-compat -->"
CLAUDE_COMPAT_MARKER_END = "<!-- /claude-compat -->"
CLAUDE_COMPAT_PATCH = f"""\n{CLAUDE_COMPAT_MARKER_START}\n## Claude Code Compatibility — Auto-load CLAUDE.md

At the start of every session, before doing anything else, check for the
following files in the current working directory (project root):

| Priority | File | Purpose |
|----------|------|---------|
| 1 | `CLAUDE.local.md` | Local overrides — machine-specific, gitignored |
| 2 | `CLAUDE.md` | Project-wide instructions — committed to the repo |

**Discovery logic (in order):**
1. `<cwd>/CLAUDE.local.md` — read if exists
2. `<cwd>/CLAUDE.md` — read if exists
3. If neither exists, skip silently

**How to apply the content:**
- Treat both files as authoritative project instructions, equivalent to `AGENTS.md`.
- `CLAUDE.local.md` takes precedence over `CLAUDE.md` when they conflict.
- Never modify these files unless the user explicitly asks.
- If a file is found, print one line: `📋 Loaded <filename> (N lines)`
{CLAUDE_COMPAT_MARKER_END}\n"""


def apply_claude_compat_patch(yes: bool = False) -> bool:
    """Apply the CLAUDE.md / CLAUDE.local.md compatibility patch to AGENTS.md.

    Returns True if the patch was applied or already present, False if the
    user cancelled in interactive mode.
    """
    agents_md = Path.home() / ".kimi-code" / "AGENTS.md"

    existing = ""
    if agents_md.exists():
        existing = agents_md.read_text(encoding="utf-8")

    if CLAUDE_COMPAT_MARKER_START in existing:
        console.print(
            "[yellow]⚠️  claude-compat patch already present in ~/.kimi-code/AGENTS.md[/yellow]"
        )
        console.print(
            "[dim]Nothing to do. To re-apply, remove the <!-- claude-compat --> block first.[/dim]"
        )
        return True

    if yes:
        console.print(
            "[dim]Applying claude-compat patch in non-interactive mode...[/dim]"
        )
    else:
        console.print("\n[bold cyan]Claude Code Compatibility Patch[/bold cyan]\n")
        console.print(
            "This will append the following block to [bold]~/.kimi-code/AGENTS.md[/bold]:\n"
        )
        console.print(
            Panel(
                CLAUDE_COMPAT_PATCH.strip(),
                title="Patch preview",
                border_style="dim",
                padding=(1, 2),
            )
        )

        if not Confirm.ask("\nAdd this to ~/.kimi-code/AGENTS.md?", default=True):
            console.print("[dim]Cancelled.[/dim]")
            return False

    agents_md.parent.mkdir(parents=True, exist_ok=True)
    with open(agents_md, "a", encoding="utf-8") as f:
        f.write(CLAUDE_COMPAT_PATCH)

    console.print("\n[green]✅ Patch applied to ~/.kimi-code/AGENTS.md[/green]")
    console.print(
        "[dim]Kimi will now auto-read CLAUDE.local.md and CLAUDE.md at session start.[/dim]"
    )
    console.print("[dim]Restart Kimi CLI for the change to take effect.[/dim]\n")
    return True


@main.command()
@click.argument("skill_name")
@click.option(
    "--project",
    is_flag=True,
    help="Also record the skill in the project's .kimi/skills.json.",
)
def install_skill_cmd(skill_name: str, project: bool):
    """Install a skill into ~/.kimi-code/skills/."""
    print_header()
    config = KimiConfig()
    if skill_name not in SKILLS:
        console.print(f"[red]Unknown skill: {skill_name}[/red]")
        console.print(f"Available: {', '.join(SKILLS.keys())}")
        raise SystemExit(1)
    install_skill(skill_name, config)

    if project:
        project_root = _require_project_root()
        pc = ProjectConfig(project_root)
        pc.add_skill(skill_name)
        console.print(
            _("[dim]Recorded in {path} — 'kimi-mcp-hub sync' installs it for teammates.[/dim]").format(
                path=pc.skills_json
            )
        )


@main.command()
def list_skills():
    """List all available skills."""
    print_header()
    config = KimiConfig()
    installed = list_installed_skills(config)

    table = Table(title="Available Skills", box=box.ROUNDED)
    table.add_column("Skill", style="cyan")
    table.add_column("Description", style="white")
    table.add_column("Status", style="green")

    for key, desc in SKILLS.items():
        status = (
            "[green]installed[/green]"
            if key in installed
            else "[dim]not installed[/dim]"
        )
        marker = "[bold]*[/bold]" if key in CORE_SKILLS else " "
        table.add_row(f"{marker} {key}", desc, status)

    console.print(table)
    console.print(
        "\n[dim]* = core skill | Install with: [bold]kimi-mcp-hub install-skill <name>[/bold][/dim]\n"
    )


@main.command(name="claude-compat")
@click.option(
    "--yes", is_flag=True, help="Apply the patch without asking for confirmation."
)
def claude_compat_cmd(yes: bool):
    """Patch ~/.kimi-code/AGENTS.md to auto-load CLAUDE.md and CLAUDE.local.md."""
    print_header()
    apply_claude_compat_patch(yes=yes)
